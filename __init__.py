"""
MAMS - Matrix Agentic Money System
"""

__version__ = "1.0.0"
__author__ = "Matrix Agent"

from .config import Config, get_config, get_env_config
from .memory import SharedMemory, get_memory, MemoryType
from .message_bus import MessageBus, get_message_bus, MessageType, MessagePriority
from .base_agent import BaseAgent, AgentStatus, AgentCapability
from .agents import (
    ResearcherAgent,
    CreatorAgent,
    MarketerAgent,
    SalesAgent,
    AnalystAgent,
    QualityAgent,
    ComplianceAgent,
    FinanceAgent,
)
from .director import DirectorAgent
from .main import SystemOrchestrator, get_orchestrator
from .revenue import RevenueEngine, get_revenue_engine, RevenueStream

__all__ = [
    # Version
    "__version__",
    
    # Config
    "Config",
    "get_config",
    "get_env_config",
    
    # Core
    "SharedMemory",
    "get_memory",
    "MemoryType",
    "MessageBus",
    "get_message_bus",
    "MessageType",
    "MessagePriority",
    
    # Base
    "BaseAgent",
    "AgentStatus",
    "AgentCapability",
    
    # Agents
    "ResearcherAgent",
    "CreatorAgent",
    "MarketerAgent",
    "SalesAgent",
    "AnalystAgent",
    "QualityAgent",
    "ComplianceAgent",
    "FinanceAgent",
    "DirectorAgent",
    
    # System
    "SystemOrchestrator",
    "get_orchestrator",
    
    # Revenue
    "RevenueEngine",
    "get_revenue_engine",
    "RevenueStream",
]
