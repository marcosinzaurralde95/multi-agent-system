"""
MAMS - Matrix Agentic Money System
Main System Orchestrator
"""

import time
import signal
import sys
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import loguru
import yaml

from config import Config, get_config, get_env_config
from memory import SharedMemory, get_memory
from message_bus import MessageBus, MessageType, MessagePriority, get_message_bus
from base_agent import BaseAgent, AgentStatus
from agents import (
    ResearcherAgent,
    CreatorAgent,
    MarketerAgent,
    SalesAgent,
    AnalystAgent,
    QualityAgent,
    ComplianceAgent,
    FinanceAgent,
)
from director import DirectorAgent

logger = loguru.logger


class SystemOrchestrator:
    """
    Main orchestrator that manages the entire agent system.
    Handles startup, shutdown, and coordination of all agents.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = Config.load(config_path)
        self.env_config = get_env_config()
        
        # Core components
        self.memory: SharedMemory = get_memory()
        self.message_bus: MessageBus = get_message_bus()
        
        # Agents registry
        self.agents: Dict[str, BaseAgent] = {}
        self.director: Optional[DirectorAgent] = None
        
        # System state
        self.running = False
        self.start_time: Optional[datetime] = None
        
        # Callbacks
        self.on_log: Optional[callable] = None
        self.on_alert: Optional[callable] = None
        self.on_dashboard_update: Optional[callable] = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("SystemOrchestrator initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown()
        sys.exit(0)
    
    def initialize(self):
        """Initialize the system and all agents"""
        logger.info("=" * 60)
        logger.info("MAMS - Matrix Agentic Money System")
        logger.info("Initializing autonomous agent system...")
        logger.info("=" * 60)
        
        # Create data directory
        Path("data").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
        
        # Initialize agents
        self._initialize_director()
        self._initialize_specialized_agents()
        
        # Register all agents with message bus
        self._register_all_agents()
        
        logger.info("System initialization complete")
        self._log_system_status()
    
    def _initialize_director(self):
        """Initialize the Director (CEO) agent"""
        director_config = self.config.director
        
        self.director = DirectorAgent(
            config={
                "auto_approval_limit": self.config.system.auto_approval_limit,
                "human_approval_limit": self.config.system.require_human_approval_above,
            }
        )
        
        # Set up director callbacks
        self.director.on_alert = self._handle_alert
        self.director.on_approval_required = self._handle_approval_required
        
        self.agents["director"] = self.director
        
        logger.info("Director Agent (CEO) initialized")
    
    def _initialize_specialized_agents(self):
        """Initialize all specialized agents"""
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
            
            # Set up callbacks
            agent.on_task_completed = lambda aid, result: self._on_agent_task_completed(aid, result)
            agent.on_error = lambda e, aid=agent_id: self._on_agent_error(aid, e)
            
            self.agents[agent_id] = agent
        
        logger.info(f"Initialized {len(agent_classes)} specialized agents")
    
    def _register_all_agents(self):
        """Register all agents with the message bus"""
        for agent_id, agent in self.agents.items():
            self.message_bus.register_agent(
                agent_id=agent_id,
                agent_type=agent.agent_type,
                capabilities=agent.get_capabilities(),
            )
        
        logger.info(f"Registered {len(self.agents)} agents with message bus")
    
    def start(self):
        """Start all agents"""
        logger.info("Starting all agents...")
        
        self.running = True
        self.start_time = datetime.now()
        
        # Start director first
        if self.director:
            self.director.start()
        
        # Start all specialized agents
        for agent_id, agent in self.agents.items():
            if agent_id != "director":
                agent.start()
        
        # Give agents time to initialize
        time.sleep(2)
        
        logger.info("=" * 60)
        logger.info("SYSTEM STARTED - Running in autonomous mode")
        logger.info("=" * 60)
        
        # Start main loop
        self._main_loop()
    
    def _main_loop(self):
        """Main system loop"""
        iteration = 0
        
        while self.running:
            try:
                iteration += 1
                
                # System health check every 10 iterations
                if iteration % 10 == 0:
                    self._system_health_check()
                
                # Update dashboard every 5 iterations
                if iteration % 5 == 0:
                    self._update_dashboard()
                
                # Log heartbeat
                if iteration % 20 == 0:
                    self._log_heartbeat(iteration)
                
                time.sleep(3)  # Main loop interval
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                self._handle_alert(f"System error: {e}", "critical")
                time.sleep(5)
    
    def _system_health_check(self):
        """Perform system health check"""
        health = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "agents": {},
            "memory": self.memory.get_stats(),
            "message_bus": self.message_bus.get_stats(),
        }
        
        for agent_id, agent in self.agents.items():
            health["agents"][agent_id] = {
                "status": agent.status.value,
                "current_task": agent.current_task,
                "metrics": agent.metrics.__dict__ if hasattr(agent.metrics, '__dict__') else {},
            }
        
        # Store health snapshot
        self.memory.store_shared("system_health", health)
        
        # Check for issues
        for agent_id, status in health["agents"].items():
            if status["status"] == "error":
                self._handle_alert(f"Agent {agent_id} in error state", "critical")
    
    def _update_dashboard(self):
        """Update dashboard data"""
        if self.director and self.on_dashboard_update:
            dashboard_data = self.director.get_dashboard_data()
            self.on_dashboard_update(dashboard_data)
    
    def _log_heartbeat(self, iteration: int):
        """Log system heartbeat"""
        active_agents = sum(1 for a in self.agents.values() if a.status == AgentStatus.WORKING)
        total_tasks = sum(a.metrics.tasks_completed for a in self.agents.values())
        
        logger.debug(
            f"Heartbeat #{iteration} | "
            f"Active: {active_agents}/{len(self.agents)} agents | "
            f"Tasks completed: {total_tasks}"
        )
    
    def _log_system_status(self):
        """Log initial system status"""
        logger.info("-" * 40)
        logger.info("Agent Registry:")
        for agent_id, agent in self.agents.items():
            logger.info(f"  - {agent_id}: {agent.name} ({agent.agent_type})")
        logger.info("-" * 40)
    
    def _on_agent_task_completed(self, agent_id: str, result: Dict):
        """Handle agent task completion"""
        logger.info(f"Task completed by {agent_id}")
        
        # Notify director
        if self.director:
            self.director.receive_report(agent_id, result)
    
    def _on_agent_error(self, agent_id: str, error: Exception):
        """Handle agent error"""
        logger.error(f"Error in {agent_id}: {error}")
        self._handle_alert(f"Agent {agent_id} error: {error}", "error")
    
    def _handle_alert(self, message: str, severity: str = "info"):
        """Handle system alert"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "message": message,
        }
        
        # Store in memory
        self.memory.store_shared(f"alert:{int(time.time())}", alert, importance=0.9)
        
        # Log
        log_func = getattr(logger, severity, logger.info)
        log_func(f"ALERT [{severity.upper()}]: {message}")
        
        # Callback
        if self.on_alert:
            self.on_alert(alert)
    
    def _handle_approval_required(self, decision: Dict):
        """Handle approval request"""
        logger.info(f"Approval required: {decision.get('subject', 'Unknown')}")
        
        # In full implementation, this would send to human dashboard
        # For now, auto-approve small decisions
        value = decision.get("estimated_impact", 0)
        if value < self.config.system.auto_approval_limit:
            logger.info(f"Auto-approving low-value decision: ${value}")
            return "approved"
        
        return "pending"
    
    def shutdown(self):
        """Gracefully shutdown all agents"""
        logger.info("Initiating system shutdown...")
        
        self.running = False
        
        # Stop all agents
        for agent_id, agent in self.agents.items():
            try:
                agent.stop()
                logger.info(f"Stopped agent: {agent_id}")
            except Exception as e:
                logger.error(f"Error stopping {agent_id}: {e}")
        
        # Cleanup memory
        self.memory.cleanup_expired()
        
        logger.info("System shutdown complete")
    
    # === Public API ===
    
    def get_system_status(self) -> Dict:
        """Get overall system status"""
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
    
    def create_task(self, task_type: str, agent_id: str, description: str, input_data: Dict = None) -> str:
        """Create a task for an agent"""
        task = self.message_bus.create_task(
            task_type=task_type,
            description=description,
            assigned_to=agent_id,
            input_data=input_data or {},
        )
        return task.id
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID"""
        return self.agents.get(agent_id)
    
    def execute_strategy(self, strategy_name: str) -> Dict:
        """Execute a predefined strategy"""
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
    
    def _strategy_content_scale(self) -> Dict:
        """Scale content production strategy"""
        results = {}
        
        # Research topics
        self.create_task(
            task_type="scan_trends",
            agent_id="researcher",
            description="Find trending topics for content",
            input_data={"depth": "comprehensive"},
        )
        results["research"] = "Task assigned"
        
        # Create content pipeline
        self.create_task(
            task_type="create_blog_post",
            agent_id="creator",
            description="Create blog posts from research",
            input_data={"count": 10},
        )
        results["creation"] = "Task assigned"
        
        # Distribute
        self.create_task(
            task_type="social_distribution",
            agent_id="marketer",
            description="Distribute content across channels",
        )
        results["distribution"] = "Task assigned"
        
        return {"strategy": "content_scale", "tasks": results}
    
    def _strategy_market_expansion(self) -> Dict:
        """Expand into new markets"""
        return {
            "strategy": "market_expansion",
            "tasks": [
                "Research new market opportunities",
                "Analyze competitor presence",
                "Create localized content",
                "Set up new traffic channels",
            ],
        }
    
    def _strategy_conversion_boost(self) -> Dict:
        """Boost conversion rates"""
        return {
            "strategy": "conversion_boost",
            "tasks": [
                "Analyze conversion funnel",
                "A/B test landing pages",
                "Implement upsells",
                "Optimize checkout flow",
            ],
        }
    
    def _strategy_full_growth(self) -> Dict:
        """Comprehensive growth strategy"""
        if self.director:
            return self.director.execute_task(
                "strategic_planning",
                "Full growth planning",
                {"horizon": "90_days"},
            )
        return {"error": "Director not available"}


# Global orchestrator instance
_orchestrator: Optional[SystemOrchestrator] = None


def get_orchestrator() -> SystemOrchestrator:
    """Get global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SystemOrchestrator()
    return _orchestrator


def main():
    """Main entry point"""
    orchestrator = get_orchestrator()
    
    try:
        orchestrator.initialize()
        orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        orchestrator.shutdown()


if __name__ == "__main__":
    main()
