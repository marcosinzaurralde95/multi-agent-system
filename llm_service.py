"""
MAMS - Matrix Agentic Money System
Shared LLM Service (OpenRouter via OpenAI SDK)
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import loguru

from config import get_env_config

logger = loguru.logger

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - handled at runtime
    OpenAI = None


class LLMService:
    """Common LLM service for all agents using OpenRouter-compatible API."""

    def __init__(self):
        self.env = get_env_config()
        self.enabled = bool(self.env.OPENAI_API_KEY and self.env.OPENAI_BASE_URL and OpenAI)
        self.model = self.env.OPENROUTER_MODEL
        self.client = None

        if self.enabled:
            self.client = OpenAI(
                api_key=self.env.OPENAI_API_KEY,
                base_url=self.env.OPENAI_BASE_URL,
            )
            logger.info("LLMService enabled with model: {}", self.model)
        else:
            logger.warning("LLMService running in rules-only mode (OpenRouter not configured)")

    def _extract_json(self, content: str) -> Optional[Dict[str, Any]]:
        if not content:
            return None

        stripped = content.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                data = json.loads(stripped)
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(stripped[start : end + 1])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None
        return None

    def _fallback_payload(
        self,
        agent_id: str,
        task_type: str,
        description: str,
        input_data: Dict[str, Any],
        required_fields: List[str],
    ) -> Dict[str, Any]:
        safe_required = required_fields or []
        payload: Dict[str, Any] = {
            "agent": agent_id,
            "task_type": task_type,
            "summary": f"Rules-based execution for '{task_type}'",
            "next_actions": [
                "Validate input data",
                "Execute deterministic workflow",
                "Persist result in shared memory",
            ],
            "source": "rules",
            "generated_at": datetime.now().isoformat(),
        }
        for field in safe_required:
            payload.setdefault(field, input_data.get(field))

        if description:
            payload.setdefault("description", description)
        return payload

    def generate_task_payload(
        self,
        agent_id: str,
        task_type: str,
        description: str,
        input_data: Dict[str, Any],
        rule_context: Optional[Dict[str, Any]] = None,
        required_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        required = required_fields or []
        fallback = self._fallback_payload(agent_id, task_type, description, input_data, required)

        if not self.enabled or not self.client:
            return fallback

        system_prompt = (
            "You are an operations AI for a multi-agent business system. "
            "Return strict JSON object only. Do not use markdown. "
            "Keep output practical and deterministic."
        )
        user_prompt = {
            "agent_id": agent_id,
            "task_type": task_type,
            "description": description,
            "input_data": input_data,
            "rule_context": rule_context or {},
            "required_fields": required,
            "instructions": [
                "Return valid JSON object.",
                "Include concise operational recommendations.",
                "Never invent API credentials or external results.",
            ],
        }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
                ],
            )
            content = response.choices[0].message.content if response.choices else ""
            parsed = self._extract_json(content or "")
            if not parsed:
                return fallback

            merged = dict(fallback)
            merged.update(parsed)
            merged["source"] = "openrouter"
            merged.setdefault("generated_at", datetime.now().isoformat())
            return merged

        except Exception as exc:  # pragma: no cover - depends on external service
            logger.warning("LLMService request failed for {}:{} - {}", agent_id, task_type, exc)
            return fallback


_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
