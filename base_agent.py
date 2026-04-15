"""
MAMS - Matrix Agentic Money System
Base Agent Class
"""

import time
import uuid
import threading
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import loguru

from message_bus import MessageBus, MessageType, MessagePriority, get_message_bus, Message
from memory import SharedMemory, MemoryType, get_memory

logger = loguru.logger


class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    ERROR = "error"
    OFFLINE = "offline"


class AgentCapability(Enum):
    SEARCH = "search"
    CREATE_CONTENT = "create_content"
    ANALYZE_DATA = "analyze_data"
    MARKETING = "marketing"
    SALES = "sales"
    CODING = "coding"
    WRITING = "writing"
    DESIGN = "design"
    TRADING = "trading"
    COMMUNICATION = "communication"


@dataclass
class AgentMetrics:
    """Agent performance metrics"""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time: float = 0
    avg_task_time: float = 0
    last_active: datetime = field(default_factory=datetime.now)
    success_rate: float = 0
    revenue_generated: float = 0
    insights_produced: int = 0


class BaseAgent(ABC):
    """
    Base class for all agents in the system.
    Provides common functionality for messaging, memory, and task execution.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        name: str = None,
        description: str = None,
        capabilities: List[AgentCapability] = None,
        config: Dict[str, Any] = None,
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.name = name or agent_id
        self.description = description or ""
        self.capabilities = capabilities or []
        self.config = config or {}
        
        self.status = AgentStatus.IDLE
        self.metrics = AgentMetrics()
        self.current_task: Optional[str] = None
        self.task_history: List[Dict] = []
        
        # Dependencies
        self.message_bus = get_message_bus()
        self.memory = get_memory()
        
        # Threading
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Callbacks
        self.on_task_received: Optional[Callable] = None
        self.on_task_completed: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Tool registry
        self.tools: Dict[str, Callable] = {}
        self._register_default_tools()
        
        logger.info(f"Agent initialized: {self.agent_id} ({self.agent_type})")
    
    def _register_default_tools(self):
        """Register default tools available to all agents"""
        self.register_tool("log", self._tool_log)
        self.register_tool("store_memory", self._tool_store_memory)
        self.register_tool("retrieve_memory", self._tool_retrieve_memory)
        self.register_tool("query_knowledge", self._tool_query_knowledge)
        self.register_tool("send_message", self._tool_send_message)
        self.register_tool("calculate", self._tool_calculate)
    
    def register_tool(self, name: str, func: Callable):
        """Register a tool for this agent"""
        self.tools[name] = func
        logger.debug(f"Tool registered: {name} for {self.agent_id}")
    
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return [c.value for c in self.capabilities]
    
    # === Lifecycle Management ===
    
    def start(self):
        """Start the agent"""
        if self._running:
            return
        
        self._running = True
        
        # Register with message bus
        self.message_bus.register_agent(
            self.agent_id,
            self.agent_type,
            self.get_capabilities(),
        )
        
        # Start processing thread
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        logger.info(f"Agent started: {self.agent_id}")
    
    def stop(self):
        """Stop the agent"""
        self._running = False
        
        # Unregister from message bus
        self.message_bus.unregister_agent(self.agent_id)
        
        if self._thread:
            self._thread.join(timeout=5)
        
        logger.info(f"Agent stopped: {self.agent_id}")
    
    def _run_loop(self):
        """Main processing loop"""
        while self._running:
            try:
                # Heartbeat
                self.message_bus.heartbeat(self.agent_id)
                
                # Process messages
                self._process_messages()
                
                # Custom agent loop logic
                self._agent_loop()
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Agent loop error ({self.agent_id}): {e}")
                self.status = AgentStatus.ERROR
                if self.on_error:
                    self.on_error(e)
    
    def _process_messages(self):
        """Process incoming messages"""
        messages = self.message_bus.get_messages(self.agent_id)
        
        for message in messages:
            try:
                self._handle_message(message)
            except Exception as e:
                logger.error(f"Error handling message: {e}")
    
    def _handle_message(self, message: Message):
        """Handle an incoming message"""
        message_type = MessageType(message.type)
        
        if message_type == MessageType.TASK_ASSIGN:
            self._handle_task_assign(message)
        elif message_type == MessageType.BROADCAST:
            self._handle_broadcast(message)
        elif message_type == MessageType.DIRECT:
            self._handle_direct(message)
        elif message_type == MessageType.QUERY:
            self._handle_query(message)
        elif message_type == MessageType.APPROVAL_RESPONSE:
            self._handle_approval_response(message)
        else:
            logger.warning(f"Unhandled message type: {message.type}")
    
    def _handle_task_assign(self, message: Message):
        """Handle task assignment"""
        task_data = message.content
        if isinstance(task_data, str):
            import json
            task_data = json.loads(task_data)
        
        task_id = task_data.get("id")
        task_type = task_data.get("type")
        description = task_data.get("description")
        input_data = task_data.get("input_data", {})
        
        if isinstance(input_data, str):
            import json
            input_data = json.loads(input_data)
        
        self.current_task = task_id
        self.status = AgentStatus.WORKING
        
        start_time = time.time()
        
        try:
            # Execute task
            result = self.execute_task(task_type, description, input_data)
            
            # Update metrics
            execution_time = time.time() - start_time
            self._update_metrics(success=True, execution_time=execution_time)
            
            # Complete task
            self.message_bus.complete_task(task_id, result)
            
            # Store result
            self.memory.store_result(self.agent_id, task_type, result)
            
            # Callback
            if self.on_task_completed:
                self.on_task_completed(task_id, result)
            
            logger.info(f"Task completed: {task_id} in {execution_time:.2f}s")
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_metrics(success=False, execution_time=execution_time)
            self.message_bus.fail_task(task_id, str(e))
            logger.error(f"Task failed: {task_id} - {e}")
        
        finally:
            self.current_task = None
            self.status = AgentStatus.IDLE
    
    def _handle_broadcast(self, message: Message):
        """Handle broadcast message"""
        self.on_broadcast(message)
    
    def _handle_direct(self, message: Message):
        """Handle direct message"""
        self.on_direct_message(message)
    
    def _handle_query(self, message: Message):
        """Handle query message"""
        query = message.content
        response = self.handle_query(query)
        
        self.message_bus.reply_to(message, response, sender=self.agent_id)
    
    def _handle_approval_response(self, message: Message):
        """Handle approval response"""
        content = message.content
        self.on_approval_response(content)
    
    def _update_metrics(self, success: bool, execution_time: float):
        """Update agent metrics"""
        with self._lock:
            if success:
                self.metrics.tasks_completed += 1
            else:
                self.metrics.tasks_failed += 1
            
            self.metrics.total_execution_time += execution_time
            self.metrics.avg_task_time = (
                self.metrics.total_execution_time / 
                (self.metrics.tasks_completed + self.metrics.tasks_failed)
            )
            self.metrics.last_active = datetime.now()
            
            if self.metrics.tasks_completed + self.metrics.tasks_failed > 0:
                self.metrics.success_rate = (
                    self.metrics.tasks_completed / 
                    (self.metrics.tasks_completed + self.metrics.tasks_failed)
                )
    
    # === Abstract Methods ===
    
    @abstractmethod
    def execute_task(self, task_type: str, description: str, input_data: Dict) -> Dict[str, Any]:
        """
        Execute a task. Must be implemented by subclasses.
        
        Args:
            task_type: Type of task to execute
            description: Human-readable description
            input_data: Input data for the task
            
        Returns:
            Dict containing task results
        """
        pass
    
    def _agent_loop(self):
        """Custom agent loop logic. Override in subclasses."""
        pass
    
    def on_broadcast(self, message: Message):
        """Handle broadcast message. Override in subclasses."""
        pass
    
    def on_direct_message(self, message: Message):
        """Handle direct message. Override in subclasses."""
        pass
    
    def on_approval_response(self, content: Dict):
        """Handle approval response. Override in subclasses."""
        pass
    
    def handle_query(self, query: str) -> Any:
        """Handle a query. Override in subclasses."""
        return {"error": "Query not supported"}
    
    # === Default Tools ===
    
    def _tool_log(self, message: str, level: str = "info"):
        """Log a message"""
        log_func = getattr(logger, level, logger.info)
        log_func(f"[{self.agent_id}] {message}")
    
    def _tool_store_memory(self, key: str, value: Any, memory_type: str = "shared"):
        """Store value in memory"""
        mem_type = MemoryType(memory_type) if memory_type in [m.value for m in MemoryType] else MemoryType.SHARED
        self.memory.store(
            key=f"{self.agent_id}:{key}",
            value=value,
            memory_type=mem_type,
            agent_id=self.agent_id,
        )
    
    def _tool_retrieve_memory(self, key: str) -> Any:
        """Retrieve value from memory"""
        return self.memory.retrieve(f"{self.agent_id}:{key}")
    
    def _tool_query_knowledge(self, topic: str) -> Any:
        """Query knowledge base"""
        return self.memory.get_knowledge(topic)
    
    def _tool_send_message(self, recipient: str, subject: str, content: Any, msg_type: str = "direct"):
        """Send message to another agent"""
        message_type = MessageType(msg_type) if msg_type in [m.value for m in MessageType] else MessageType.DIRECT
        self.message_bus.send_message(
            sender=self.agent_id,
            recipient=recipient,
            message_type=message_type,
            subject=subject,
            content=content,
        )
    
    def _tool_calculate(self, expression: str) -> float:
        """Simple calculator"""
        try:
            # Safe evaluation (only allow basic math)
            import re
            if not re.match(r'^[\d\s+\-*/().]+$', expression):
                return 0
            return eval(expression)
        except:
            return 0
    
    # === Utility Methods ===
    
    def request_approval(self, subject: str, details: Dict, value: float = 0) -> str:
        """Request human approval"""
        return self.message_bus.request_approval(
            requester=self.agent_id,
            subject=subject,
            details=details,
            value=value,
        )
    
    def get_status(self) -> Dict:
        """Get agent status"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "name": self.name,
            "status": self.status.value,
            "current_task": self.current_task,
            "metrics": asdict(self.metrics) if hasattr(self.metrics, '__dataclass_fields__') else str(self.metrics),
            "capabilities": self.get_capabilities(),
        }
    
    def broadcast_status(self):
        """Broadcast agent status"""
        self.message_bus.send_broadcast(
            sender=self.agent_id,
            subject="Status Update",
            content=self.get_status(),
        )
    
    def escalate(self, subject: str, details: Dict, urgency: MessagePriority = MessagePriority.HIGH):
        """Escalate issue to human"""
        self.message_bus.escalate(
            from_agent=self.agent_id,
            subject=subject,
            details=details,
            urgency=urgency,
        )


# Helper for dataclass to dict
def asdict(obj):
    """Convert dataclass to dict recursively"""
    if hasattr(obj, '__dataclass_fields__'):
        return {k: asdict(v) for k, v in obj.__dict__.items()}
    elif isinstance(obj, list):
        return [asdict(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: asdict(v) for k, v in obj.items()}
    else:
        return obj
