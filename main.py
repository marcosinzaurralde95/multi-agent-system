"""
MAMS - Matrix Agentic Money System
Main System Orchestrator
"""

import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import loguru

from agents import (
    AnalystAgent,
    ComplianceAgent,
    CreatorAgent,
    FinanceAgent,
    MarketerAgent,
    QualityAgent,
    ResearcherAgent,
    SalesAgent,
)
from base_agent import AgentStatus, BaseAgent
from config import Config, get_env_config
from director import DirectorAgent
from memory import SharedMemory, get_memory
from message_bus import MessageBus, get_message_bus

logger = loguru.logger


class SystemOrchestrator:
    """Main orchestrator that manages startup, coordination and health."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = Config.load(config_path)
        self.env_config = get_env_config()

        self.memory: SharedMemory = get_memory()
        self.message_bus: MessageBus = get_message_bus()

        self.agents: Dict[str, BaseAgent] = {}
        self.director: Optional[DirectorAgent] = None

        self.running = False
        self.start_time: Optional[datetime] = None

        self.on_log: Optional[callable] = None
        self.on_alert: Optional[callable] = None
        self.on_dashboard_update: Optional[callable] = None

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("SystemOrchestrator initialized")

    def _signal_handler(self, signum, _frame):
        logger.info("Received signal {}, initiating shutdown...", signum)
        self.shutdown()
        sys.exit(0)

    def initialize(self):
        logger.info("=" * 60)
        logger.info("MAMS - Matrix Agentic Money System")
        logger.info("Initializing autonomous agent system...")
        logger.info("=" * 60)

        Path("data").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)

        self._initialize_director()
        self._initialize_specialized_agents()
        self._register_all_agents()
        self._log_system_status()
        logger.info("System initialization complete")

    def _initialize_director(self):
        self.director = DirectorAgent(
            config={
                "auto_approval_limit": self.config.system.auto_approval_limit,
                "human_approval_limit": self.config.system.require_human_approval_above,
            }
        )
        self.director.on_alert = self._handle_alert
        self.director.on_approval_required = self._handle_approval_required
        self.agents["director"] = self.director
        logger.info("Director Agent initialized")

    def _initialize_specialized_agents(self):
        agent_classes = {
            "researcher": ResearcherAgent,
            "creator": CreatorAgent,
            "marketer": MarketerAgent,
            "sales": SalesAgent,
            "analyst": AnalystAgent,
            "quality": QualityAgent,
            "compliance": ComplianceAgent,
            "finance": FinanceAgent,
        }

        for agent_id, agent_class in agent_classes.items():
            agent_config = getattr(self.config, agent_id, {})
            agent = agent_class(config=agent_config)
            agent.on_task_completed = self._on_agent_task_completed
            agent.on_error = lambda e, aid=agent_id: self._on_agent_error(aid, e)
            self.agents[agent_id] = agent

        logger.info("Initialized {} specialized agents", len(agent_classes))

    def _register_all_agents(self):
        for agent_id, agent in self.agents.items():
            self.message_bus.register_agent(
                agent_id=agent_id,
                agent_type=agent.agent_type,
                capabilities=agent.get_capabilities(),
            )
        logger.info("Registered {} agents with message bus", len(self.agents))

    def start(self):
        logger.info("Starting all agents...")
        self.running = True
        self.start_time = datetime.now()

        for agent in self.agents.values():
            agent.start()

        time.sleep(1)
        logger.info("SYSTEM STARTED - Running in autonomous mode")
        self._main_loop()

    def _main_loop(self):
        iteration = 0
        while self.running:
            try:
                iteration += 1

                if iteration % 5 == 0:
                    self._system_health_check()
                    self._update_dashboard()

                if iteration % 10 == 0:
                    self._log_heartbeat(iteration)

                time.sleep(3)
            except Exception as exc:
                logger.error("Main loop error: {}", exc)
                self._handle_alert(f"System error: {exc}", "critical")
                time.sleep(5)

    def _system_health_check(self):
        health = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
            if self.start_time
            else 0,
            "agents": {},
            "memory": self.memory.get_stats(),
            "message_bus": self.message_bus.get_stats(),
        }

        for agent_id, agent in self.agents.items():
            health["agents"][agent_id] = {
                "status": agent.status.value,
                "current_task": agent.current_task,
                "metrics": agent.metrics.__dict__,
            }

        timestamp = int(time.time())
        self.memory.store_shared("system_health", health)
        self.memory.store_shared(f"system_health:{timestamp}", health, importance=0.7)
        self.memory.store_shared("agent_status", health["agents"], importance=0.8)

        for agent_id, status in health["agents"].items():
            if status["status"] == "error":
                self._handle_alert(f"Agent {agent_id} in error state", "critical")

    def _update_dashboard(self):
        if not self.director:
            return

        dashboard_data = self.director.get_dashboard_data()
        self.memory.store_shared("dashboard_data", dashboard_data, importance=0.8)
        self.memory.store_shared("revenue_goals", dashboard_data.get("revenue", {}), importance=0.9)

        if self.on_dashboard_update:
            self.on_dashboard_update(dashboard_data)

    def _log_heartbeat(self, iteration: int):
        active_agents = sum(1 for a in self.agents.values() if a.status == AgentStatus.WORKING)
        total_tasks = sum(a.metrics.tasks_completed for a in self.agents.values())
        logger.debug(
            "Heartbeat #{} | Active: {}/{} agents | Tasks completed: {}",
            iteration,
            active_agents,
            len(self.agents),
            total_tasks,
        )

    def _log_system_status(self):
        logger.info("-" * 40)
        logger.info("Agent Registry:")
        for agent_id, agent in self.agents.items():
            logger.info("  - {}: {} ({})", agent_id, agent.name, agent.agent_type)
        logger.info("-" * 40)

    def _on_agent_task_completed(self, agent_id: str, payload: Dict[str, Any]):
        task_id = payload.get("task_id", "unknown")
        result = payload.get("result", {})
        logger.info("Task completed by {} (task_id={})", agent_id, task_id)

        self.memory.store_shared(
            f"task_result:{agent_id}:{task_id}",
            payload,
            importance=0.75,
        )

        if self.director:
            self.director.receive_report(agent_id, result if isinstance(result, dict) else {"value": result})

    def _on_agent_error(self, agent_id: str, error: Exception):
        logger.error("Error in {}: {}", agent_id, error)
        self._handle_alert(f"Agent {agent_id} error: {error}", "error")

    def _handle_alert(self, message: str, severity: str = "info"):
        alert = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "message": message,
        }

        self.memory.store_shared(f"alert:{int(time.time())}", alert, importance=0.9)
        alerts = self.memory.retrieve("alerts", [])
        if not isinstance(alerts, list):
            alerts = []
        alerts.append(alert)
        self.memory.store_shared("alerts", alerts[-100:], importance=0.9)

        log_func = getattr(logger, severity, logger.info)
        log_func("ALERT [{}]: {}", severity.upper(), message)

        if self.on_alert:
            self.on_alert(alert)

    def _handle_approval_required(self, decision: Dict):
        logger.info("Approval required: {}", decision.get("subject", "Unknown"))
        value = decision.get("estimated_impact", 0)
        if value < self.config.system.auto_approval_limit:
            logger.info("Auto-approving low-value decision: ${}", value)
            return "approved"
        return "pending"

    def shutdown(self):
        logger.info("Initiating system shutdown...")
        self.running = False

        for agent_id, agent in self.agents.items():
            try:
                agent.stop()
                logger.info("Stopped agent: {}", agent_id)
            except Exception as exc:
                logger.error("Error stopping {}: {}", agent_id, exc)

        self.memory.cleanup_expired()
        logger.info("System shutdown complete")

    def get_system_status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "agents": {
                agent_id: {
                    "status": agent.status.value,
                    "current_task": agent.current_task,
                }
                for agent_id, agent in self.agents.items()
            },
            "revenue_goals": self.director.revenue_goals if self.director else {},
        }

    def create_task(self, task_type: str, agent_id: str, description: str, input_data: Optional[Dict] = None) -> str:
        task = self.message_bus.create_task(
            task_type=task_type,
            description=description,
            assigned_to=agent_id,
            input_data=input_data or {},
        )
        return task.id

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        return self.agents.get(agent_id)

    def execute_strategy(self, strategy_name: str) -> Dict[str, Any]:
        strategies = {
            "content_scale": self._strategy_content_scale,
            "market_expansion": self._strategy_market_expansion,
            "conversion_boost": self._strategy_conversion_boost,
            "full_growth": self._strategy_full_growth,
        }
        strategy_func = strategies.get(strategy_name)
        if strategy_func:
            return strategy_func()
        return {"error": f"Unknown strategy: {strategy_name}"}

    def _strategy_content_scale(self) -> Dict[str, Any]:
        self.create_task(
            task_type="scan_trends",
            agent_id="researcher",
            description="Find trending topics for content",
            input_data={"depth": "comprehensive"},
        )
        self.create_task(
            task_type="create_blog_post",
            agent_id="creator",
            description="Create blog posts from research",
            input_data={"count": 10},
        )
        self.create_task(
            task_type="social_distribution",
            agent_id="marketer",
            description="Distribute content across channels",
        )
        return {"strategy": "content_scale", "tasks": 3}

    def _strategy_market_expansion(self) -> Dict[str, Any]:
        return {
            "strategy": "market_expansion",
            "tasks": [
                "Research new market opportunities",
                "Analyze competitor presence",
                "Create localized content",
                "Set up new traffic channels",
            ],
        }

    def _strategy_conversion_boost(self) -> Dict[str, Any]:
        return {
            "strategy": "conversion_boost",
            "tasks": [
                "Analyze conversion funnel",
                "A/B test landing pages",
                "Implement upsells",
                "Optimize checkout flow",
            ],
        }

    def _strategy_full_growth(self) -> Dict[str, Any]:
        if self.director:
            return self.director.execute_task(
                "strategic_planning",
                "Full growth planning",
                {"horizon": "90_days"},
            )
        return {"error": "Director not available"}


_orchestrator: Optional[SystemOrchestrator] = None


def get_orchestrator() -> SystemOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SystemOrchestrator()
    return _orchestrator


def main():
    orchestrator = get_orchestrator()
    try:
        orchestrator.initialize()
        orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as exc:
        logger.error("Fatal error: {}", exc)
    finally:
        orchestrator.shutdown()


if __name__ == "__main__":
    main()
