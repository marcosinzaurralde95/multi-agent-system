"""
MAMS - Matrix Agentic Money System
Configuration Module
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class SystemConfig:
    name: str = "MAMS"
    version: str = "1.0.0"
    mode: str = "autonomous"
    log_level: str = "INFO"
    timezone: str = "America/New_York"
    
    # Autonomy settings
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
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        system_data = data.get('system', {})
        system = SystemConfig(
            name=system_data.get('name', 'MAMS'),
            version=system_data.get('version', '1.0.0'),
            mode=system_data.get('mode', 'autonomous'),
            log_level=system_data.get('log_level', 'INFO'),
            timezone=system_data.get('timezone', 'America/New_York'),
            auto_approval_limit=system_data.get('autonomy', {}).get('auto_approval_limit', 100),
            require_human_approval_above=system_data.get('autonomy', {}).get('require_human_approval_above', 1000),
            max_daily_budget=system_data.get('autonomy', {}).get('max_daily_budget', 500),
            max_concurrent_agents=system_data.get('autonomy', {}).get('max_concurrent_agents', 10),
            task_timeout_seconds=system_data.get('autonomy', {}).get('task_timeout_seconds', 300),
            retry_attempts=system_data.get('autonomy', {}).get('retry_attempts', 3),
        )
        
        targets = data.get('revenue_targets', {})
        revenue_targets = RevenueTargets(
            daily=targets.get('daily', 333),
            weekly=targets.get('weekly', 2333),
            monthly=targets.get('monthly', 10000),
            yearly=targets.get('yearly', 120000),
        )
        
        return cls(
            system=system,
            revenue_targets=revenue_targets,
            director=data.get('director', {}),
            researcher=data.get('researcher', {}),
            creator=data.get('creator', {}),
            marketer=data.get('marketer', {}),
            sales=data.get('sales', {}),
            analyst=data.get('analyst', {}),
            quality=data.get('quality', {}),
            compliance=data.get('compliance', {}),
            finance=data.get('finance', {}),
            dashboard=data.get('dashboard', {}),
            database=data.get('database', {}),
            scheduler=data.get('scheduler', {}),
            security=data.get('security', {}),
        )


class EnvConfig:
    """Environment variable configuration"""
    
    # AI APIs
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None  # Added for Groq/OpenRouter support
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Search & News
    NEWS_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None
    
    # Affiliate
    AMAZON_ASSOCIATE_TAG: Optional[str] = None
    CJ_AFFILIATE_ID: Optional[str] = None
    SHAREASALE_ID: Optional[str] = None
    
    # Ads
    GOOGLE_ADS_API_KEY: Optional[str] = None
    FACEBOOK_ADS_API_KEY: Optional[str] = None
    TIKTOK_ADS_API_KEY: Optional[str] = None
    
    # Analytics
    GA4_PROPERTY_ID: Optional[str] = None
    POSTHOG_API_KEY: Optional[str] = None
    
    # Trading
    ALPACA_API_KEY: Optional[str] = None
    ALPACA_SECRET_KEY: Optional[str] = None
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_SECRET_KEY: Optional[str] = None
    
    # Email
    SENDGRID_API_KEY: Optional[str] = None
    MAILCHIMP_API_KEY: Optional[str] = None
    
    # SMS
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE: Optional[str] = None
    
    # Payments
    STRIPE_API_KEY: Optional[str] = None
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_SECRET: Optional[str] = None
    
    # Social
    TWITTER_API_KEY: Optional[str] = None
    TWITTER_API_SECRET: Optional[str] = None
    LINKEDIN_API_KEY: Optional[str] = None
    
    # Infrastructure
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SENTRY_DSN: Optional[str] = None
    SLACK_WEBHOOK_URL: Optional[str] = None
    
    # System
    LOG_LEVEL: str = "INFO"
    AUTO_APPROVAL_LIMIT: float = 100
    MAX_DAILY_SPEND: float = 500
    REVENUE_TARGET: float = 10000
    
    @classmethod
    def load(cls) -> "EnvConfig":
        """Load all environment variables"""
        config = cls()
        for key in dir(config):
            if key.isupper() and not key.startswith('_'):
                value = os.getenv(key)
                if value is not None:
                    setattr(config, key, value)
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get environment variable with default"""
        return os.getenv(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Dict-style access"""
        return os.getenv(key)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists"""
        return key in os.environ


# Global config instance
_config: Optional[Config] = None
_env_config: Optional[EnvConfig] = None


def get_config() -> Config:
    """Get global configuration"""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def get_env_config() -> EnvConfig:
    """Get environment configuration"""
    global _env_config
    if _env_config is None:
        _env_config = EnvConfig.load()
    return _env_config


# Convenience functions
def get_api_key(provider: str) -> Optional[str]:
    """Get API key for a provider"""
    return get_env_config().get(f"{provider.upper()}_API_KEY")


def get_revenue_target(period: str = "monthly") -> float:
    """Get revenue target for a period"""
    targets = get_config().revenue_targets
    return getattr(targets, period, 10000)
