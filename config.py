"""
MAMS - Matrix Agentic Money System
Configuration Module
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ConfigValidationError(ValueError):
    """Configuration schema or runtime validation error."""


@dataclass
class SystemConfig:
    name: str = "MAMS"
    version: str = "1.0.0"
    mode: str = "autonomous"
    log_level: str = "INFO"
    timezone: str = "America/New_York"
    auto_approval_limit: float = 100
    require_human_approval_above: float = 1000
    max_daily_budget: float = 500
    max_concurrent_agents: int = 10
    task_timeout_seconds: int = 300
    retry_attempts: int = 3


@dataclass
class RevenueTargets:
    daily: float = 333
    weekly: float = 2333
    monthly: float = 10000
    yearly: float = 120000


@dataclass
class Config:
    system: SystemConfig
    revenue_targets: RevenueTargets
    director: Dict[str, Any]
    researcher: Dict[str, Any]
    creator: Dict[str, Any]
    marketer: Dict[str, Any]
    sales: Dict[str, Any]
    analyst: Dict[str, Any]
    quality: Dict[str, Any]
    compliance: Dict[str, Any]
    finance: Dict[str, Any]
    dashboard: Dict[str, Any]
    database: Dict[str, Any]
    scheduler: Dict[str, Any]
    security: Dict[str, Any]

    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "Config":
        """Load configuration from YAML file and validate required sections."""
        path = Path(config_path)
        if not path.exists():
            raise ConfigValidationError(f"Configuration file not found: {config_path}")

        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if not isinstance(data, dict):
            raise ConfigValidationError("Configuration root must be a YAML mapping.")

        system_data = data.get("system", {}) or {}
        if not isinstance(system_data, dict):
            raise ConfigValidationError("'system' section must be a mapping.")

        autonomy = system_data.get("autonomy", {}) or {}
        if not isinstance(autonomy, dict):
            raise ConfigValidationError("'system.autonomy' section must be a mapping.")

        # Support both top-level revenue_targets and legacy system.revenue_targets.
        targets = data.get("revenue_targets") or system_data.get("revenue_targets") or {}
        if not isinstance(targets, dict):
            raise ConfigValidationError("'revenue_targets' section must be a mapping.")

        compliance = data.get("compliance", {}) or {}
        compliance_checks = compliance.get("checks", {}) or {}
        affiliate_checks = compliance_checks.get("affiliate", {}) or {}
        if "check_ FTC" in affiliate_checks and "check_ftc" not in affiliate_checks:
            affiliate_checks["check_ftc"] = affiliate_checks["check_ FTC"]
        if affiliate_checks:
            compliance_checks["affiliate"] = affiliate_checks
            compliance["checks"] = compliance_checks

        system = SystemConfig(
            name=system_data.get("name", "MAMS"),
            version=system_data.get("version", "1.0.0"),
            mode=system_data.get("mode", "autonomous"),
            log_level=system_data.get("log_level", "INFO"),
            timezone=system_data.get("timezone", "America/New_York"),
            auto_approval_limit=float(autonomy.get("auto_approval_limit", 100)),
            require_human_approval_above=float(autonomy.get("require_human_approval_above", 1000)),
            max_daily_budget=float(autonomy.get("max_daily_budget", 500)),
            max_concurrent_agents=int(autonomy.get("max_concurrent_agents", 10)),
            task_timeout_seconds=int(autonomy.get("task_timeout_seconds", 300)),
            retry_attempts=int(autonomy.get("retry_attempts", 3)),
        )

        revenue_targets = RevenueTargets(
            daily=float(targets.get("daily", 333)),
            weekly=float(targets.get("weekly", 2333)),
            monthly=float(targets.get("monthly", 10000)),
            yearly=float(targets.get("yearly", 120000)),
        )

        required_sections = (
            "director",
            "researcher",
            "creator",
            "marketer",
            "sales",
            "analyst",
            "quality",
            "compliance",
            "finance",
            "dashboard",
            "database",
            "scheduler",
            "security",
        )
        missing = [section for section in required_sections if section not in data]
        if missing:
            raise ConfigValidationError(
                "Missing required configuration sections: " + ", ".join(missing)
            )

        database = data.get("database", {}) or {}
        if not database.get("path"):
            database["path"] = "data/mams_memory.db"

        return cls(
            system=system,
            revenue_targets=revenue_targets,
            director=data.get("director", {}),
            researcher=data.get("researcher", {}),
            creator=data.get("creator", {}),
            marketer=data.get("marketer", {}),
            sales=data.get("sales", {}),
            analyst=data.get("analyst", {}),
            quality=data.get("quality", {}),
            compliance=compliance,
            finance=data.get("finance", {}),
            dashboard=data.get("dashboard", {}),
            database=database,
            scheduler=data.get("scheduler", {}),
            security=data.get("security", {}),
        )


@dataclass
class EnvConfig:
    """Environment variable configuration."""

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    LOG_LEVEL: str = "INFO"
    AUTO_APPROVAL_LIMIT: float = 100
    MAX_DAILY_SPEND: float = 500
    REVENUE_TARGET: float = 10000

    @classmethod
    def load(cls) -> "EnvConfig":
        config = cls(
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
            OPENAI_BASE_URL=os.getenv("OPENAI_BASE_URL"),
            OPENROUTER_MODEL=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
            AUTO_APPROVAL_LIMIT=float(os.getenv("AUTO_APPROVAL_LIMIT", "100")),
            MAX_DAILY_SPEND=float(os.getenv("MAX_DAILY_SPEND", "500")),
            REVENUE_TARGET=float(os.getenv("REVENUE_TARGET", "10000")),
        )
        return config

    def get(self, key: str, default: Any = None) -> Any:
        return os.getenv(key, default)

    def __getitem__(self, key: str) -> Any:
        return os.getenv(key)

    def __contains__(self, key: str) -> bool:
        return key in os.environ

    def validate_openrouter(self, strict: bool = True) -> None:
        missing = []
        if not self.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not self.OPENAI_BASE_URL:
            missing.append("OPENAI_BASE_URL")

        if strict and missing:
            raise ConfigValidationError(
                "Missing required OpenRouter environment variables: "
                + ", ".join(missing)
                + ". Configure them in .env before starting worker/run."
            )


_config: Optional[Config] = None
_env_config: Optional[EnvConfig] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def get_env_config() -> EnvConfig:
    global _env_config
    if _env_config is None:
        _env_config = EnvConfig.load()
    return _env_config


def validate_runtime(require_openrouter: bool = True) -> Dict[str, Any]:
    """Validate config + env and return loaded values for startup paths."""
    cfg = get_config()
    env = get_env_config()
    env.validate_openrouter(strict=require_openrouter)
    return {"config": cfg, "env": env}


def get_api_key(provider: str) -> Optional[str]:
    return get_env_config().get(f"{provider.upper()}_API_KEY")


def get_revenue_target(period: str = "monthly") -> float:
    targets = get_config().revenue_targets
    return float(getattr(targets, period, 10000))
