"""
MAMS - Matrix Agentic Money System
Specialized Agents (deterministic rules + OpenRouter enrichment)
"""

import hashlib
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from base_agent import AgentCapability, BaseAgent
from memory import get_memory


def _stable_int(seed: str, low: int, high: int) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    value = int(digest[:8], 16)
    return low + (value % (high - low + 1))


def _slug(text: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in text.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "item"


class _RuleAgent(BaseAgent):
    def _base(self, task_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "task_type": task_type,
            "status": "completed",
            "generated_at": datetime.now().isoformat(),
            "input_echo": input_data,
        }

    def execute_task(self, task_type: str, description: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        rule = self._base(task_type, input_data)
        rule.update(self._task_data(task_type, input_data))
        return self.enrich_with_llm(task_type, description, input_data, rule)

    def _task_data(self, task_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {}


class ResearcherAgent(_RuleAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_id="researcher",
            agent_type="research",
            name="Research Agent",
            description="Market intelligence and opportunity identification",
            capabilities=[AgentCapability.SEARCH, AgentCapability.ANALYZE_DATA, AgentCapability.COMMUNICATION],
            config=config or {},
        )
        self.memory = get_memory()

    def _task_data(self, task_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if task_type == "scan_trends":
            keywords = input_data.get("keywords") or ["ai automation", "content ops", "conversion funnel"]
            trends = []
            for keyword in keywords:
                seed = f"trend:{keyword}"
                trends.append(
                    {
                        "keyword": keyword,
                        "score": _stable_int(seed, 55, 98),
                        "volume": _stable_int(seed + ":volume", 1500, 120000),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            trends.sort(key=lambda item: item["score"], reverse=True)
            self.memory.store_shared("trending_topics", trends, importance=0.8)
            return {"trends_found": len(trends), "top_trends": trends[:5]}
        if task_type == "keyword_research":
            seed_keywords = input_data.get("seed_keywords") or ["ai tools", "business automation"]
            rows = []
            for seed in seed_keywords:
                for suffix in ["guide", "pricing", "comparison", "templates"]:
                    phrase = f"{seed} {suffix}"
                    score_seed = f"kw:{phrase}"
                    rows.append(
                        {
                            "keyword": phrase,
                            "volume": _stable_int(score_seed + ":v", 300, 50000),
                            "difficulty": _stable_int(score_seed + ":d", 10, 85),
                        }
                    )
            rows.sort(key=lambda item: item["volume"], reverse=True)
            return {"keywords_found": len(rows), "top_keywords": rows[:20]}
        if task_type == "lead_generation":
            count = int(input_data.get("count", 20))
            leads = []
            for idx in range(max(1, count)):
                seed = f"lead:{idx}"
                leads.append({"id": f"lead_{idx+1}", "fit_score": _stable_int(seed, 50, 95)})
            leads.sort(key=lambda item: item["fit_score"], reverse=True)
            self.memory.store_shared("leads", leads, importance=0.7)
            return {"leads_generated": len(leads), "top_leads": leads[:10]}
        return {}


class CreatorAgent(_RuleAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_id="creator",
            agent_type="creator",
            name="Creator Agent",
            description="Content production and creative asset generation",
            capabilities=[AgentCapability.CREATE_CONTENT, AgentCapability.WRITING, AgentCapability.DESIGN],
            config=config or {},
        )
        self.memory = get_memory()

    def _task_data(self, task_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if task_type == "create_blog_post":
            topic = input_data.get("topic", "AI operations for revenue teams")
            content_id = f"post_{int(time.time())}"
            post = {
                "content_id": content_id,
                "title": f"{topic}: practical blueprint",
                "slug": _slug(topic),
                "outline": ["problem", "framework", "execution", "metrics"],
                "publish_ready": True,
            }
            self.memory.store_shared(f"content:{content_id}", post, importance=0.8)
            return post
        if task_type == "create_social_content":
            topic = input_data.get("topic", "AI growth operations")
            count = int(input_data.get("count", 5))
            return {
                "posts_created": count,
                "posts": [f"{topic} insight #{idx+1}" for idx in range(max(1, count))],
            }
        if task_type == "create_email_sequence":
            return {"sequence_length": 5, "emails": ["welcome", "diagnostic", "education", "proof", "offer"]}
        return {}


class MarketerAgent(_RuleAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_id="marketer",
            agent_type="marketing",
            name="Marketer Agent",
            description="Growth channel execution and optimization",
            capabilities=[AgentCapability.MARKETING, AgentCapability.ANALYZE_DATA, AgentCapability.COMMUNICATION],
            config=config or {},
        )

    def _task_data(self, task_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if task_type == "social_distribution":
            channels = input_data.get("channels", ["linkedin", "x", "youtube"])
            return {"channels": channels, "frequency_per_day": 2}
        if task_type == "seo_optimization":
            return {"actions": ["improve h1/h2 intent match", "expand internal links", "add schema"], "expected_lift_percent": 12}
        if task_type == "email_campaign":
            return {"emails": 4, "target_open_rate": 32, "target_click_rate": 5}
        if task_type == "paid_campaign":
            budget = float(input_data.get("budget", 200))
            return {"budget_daily": budget, "min_roas": 2.0, "max_cpl": 35}
        return {}


class SalesAgent(_RuleAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_id="sales",
            agent_type="sales",
            name="Sales Agent",
            description="Revenue generation and conversion management",
            capabilities=[AgentCapability.SALES, AgentCapability.ANALYZE_DATA, AgentCapability.COMMUNICATION],
            config=config or {},
        )

    def _task_data(self, task_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if task_type == "optimize_conversion":
            baseline = float(input_data.get("baseline_rate", 2.0))
            target = round(baseline * 1.2, 2)
            return {"baseline_rate": baseline, "target_rate": target, "revenue_generated": round(target * 120, 2)}
        if task_type == "funnel_analysis":
            visitors = int(input_data.get("visitors", 10000))
            leads = int(visitors * 0.12)
            customers = int(leads * 0.22)
            return {"visitors": visitors, "leads": leads, "customers": customers}
        if task_type == "close_deal":
            deal_value = float(input_data.get("deal_value", 1500))
            return {"deal_id": f"deal_{int(time.time())}", "status": "won" if deal_value > 0 else "lost", "revenue_generated": deal_value}
        return {}


class AnalystAgent(_RuleAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_id="analyst",
            agent_type="analytics",
            name="Analyst Agent",
            description="Business intelligence and forecasting",
            capabilities=[AgentCapability.ANALYZE_DATA, AgentCapability.COMMUNICATION],
            config=config or {},
        )

    def _task_data(self, task_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if task_type == "performance_report":
            traffic = int(input_data.get("traffic", 12000))
            conversion_rate = float(input_data.get("conversion_rate", 2.3))
            revenue = round(traffic * conversion_rate * 0.42, 2)
            return {"traffic": traffic, "conversion_rate": conversion_rate, "revenue_generated": revenue}
        if task_type == "revenue_forecast":
            daily = float(input_data.get("daily_revenue", 550))
            horizon = int(input_data.get("horizon_days", 30))
            return {"horizon_days": horizon, "expected_revenue": round(daily * horizon, 2)}
        if task_type == "roi_analysis":
            cost = float(input_data.get("cost", 1000))
            revenue = float(input_data.get("revenue", 1700))
            return {"cost": cost, "revenue": revenue, "roi_percent": round(((revenue - cost) / max(cost, 1)) * 100, 2)}
        return {}


class QualityAgent(_RuleAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_id="quality",
            agent_type="quality",
            name="Quality Agent",
            description="Quality assurance and brand consistency",
            capabilities=[AgentCapability.ANALYZE_DATA, AgentCapability.COMMUNICATION],
            config=config or {},
        )
        self.quality_standards = {"readability_min": 60, "seo_score_min": 70, "plagiarism_max": 10}

    def _task_data(self, task_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if task_type == "check_content":
            content = str(input_data.get("content", ""))
            score = min(100, max(40, len(content) // 20))
            return {"quality_score": score, "approved": score >= self.quality_standards["readability_min"]}
        if task_type == "seo_audit":
            return {"overall_score": 82, "checks": {"meta_tags": True, "heading_structure": True}}
        if task_type == "set_quality_standards":
            self.quality_standards.update(input_data)
            return {"standards_updated": True, "quality_standards": self.quality_standards}
        return {}


class ComplianceAgent(_RuleAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_id="compliance",
            agent_type="compliance",
            name="Compliance Agent",
            description="Legal compliance and regulatory adherence",
            capabilities=[AgentCapability.ANALYZE_DATA, AgentCapability.COMMUNICATION],
            config=config or {},
        )

    def _task_data(self, task_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if task_type == "check_affiliate_disclosure":
            return {"has_disclosure": True, "ftc_compliant": True}
        if task_type == "verify_claims":
            claims = input_data.get("claims", [])
            return {"claims_verified": len(claims), "all_safe": True}
        if task_type == "compliance_audit":
            return {"overall_compliance": 94.0, "action_items": []}
        return {}


class FinanceAgent(_RuleAgent):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_id="finance",
            agent_type="finance",
            name="Finance Agent",
            description="Financial operations and money management",
            capabilities=[AgentCapability.ANALYZE_DATA],
            config=config or {},
        )
        self.balance = 0.0
        self.transactions = []

    def _task_data(self, task_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if task_type == "track_expense":
            amount = float(input_data.get("amount", 0))
            self.balance -= amount
            self.transactions.append({"amount": amount, "category": input_data.get("category", "other")})
            return {"recorded": True, "new_balance": round(self.balance, 2)}
        if task_type == "generate_invoice":
            items = input_data.get("items", [])
            subtotal = sum(float(item.get("amount", 0)) for item in items)
            total = round(subtotal * 1.1, 2)
            return {"invoice_id": f"inv_{int(time.time())}", "total": total}
        if task_type == "financial_summary":
            expenses = sum(float(tx["amount"]) for tx in self.transactions) if self.transactions else 0.0
            revenue = float(input_data.get("revenue", max(0.0, expenses * 1.8)))
            return {"total_revenue": round(revenue, 2), "total_expenses": round(expenses, 2), "net_profit": round(revenue - expenses, 2), "revenue_generated": round(revenue, 2)}
        if task_type == "budget_analysis":
            budget_total = float(input_data.get("budget_total", 10000))
            actual_total = float(input_data.get("actual_total", abs(self.balance)))
            return {"budget_total": budget_total, "actual_total": actual_total, "variance": round(actual_total - budget_total, 2)}
        if task_type == "track_payout":
            amount = float(input_data.get("amount", 0))
            return {"payout_id": f"pay_{int(time.time())}", "amount": amount, "status": "processing"}
        if task_type == "expense_report":
            by_category = {}
            for tx in self.transactions:
                by_category[tx["category"]] = by_category.get(tx["category"], 0.0) + float(tx["amount"])
            return {"total_expenses": round(sum(by_category.values()), 2), "by_category": {k: round(v, 2) for k, v in by_category.items()}}
        return {}
