"""
MAMS - Matrix Agentic Money System
Message Bus for Inter-Agent Communication
"""

import json
import asyncio
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import loguru

logger = loguru.logger


class MessagePriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3
    CRITICAL = 4


class MessageType(Enum):
    # Task Distribution
    TASK_ASSIGN = "task_assign"
    TASK_RESULT = "task_result"
    TASK_STATUS = "task_status"
    
    # Information Sharing
    BROADCAST = "broadcast"
    DIRECT = "direct"
    REPLY = "reply"
    
    # Coordination
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    ESCALATION = "escalation"
    
    # Monitoring
    HEARTBEAT = "heartbeat"
    STATUS_UPDATE = "status_update"
    ALERT = "alert"
    
    # Collaboration
    QUERY = "query"
    RESPONSE = "response"
    PROPOSE = "propose"
    ACCEPT = "accept"
    REJECT = "reject"


@dataclass
class Message:
    """Inter-agent message"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = MessageType.DIRECT.value
    sender: str = ""
    recipient: str = ""  # "" means broadcast
    subject: str = ""
    content: Any = None
    priority: int = MessagePriority.NORMAL.value
    correlation_id: str = ""  # For reply tracking
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "sender": self.sender,
            "recipient": self.recipient,
            "subject": self.subject,
            "content": json.dumps(self.content) if not isinstance(self.content, str) else self.content,
            "priority": self.priority,
            "correlation_id": self.correlation_id,
            "metadata": json.dumps(self.metadata),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "retry_count": self.retry_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=data.get("type", MessageType.DIRECT.value),
            sender=data.get("sender", ""),
            recipient=data.get("recipient", ""),
            subject=data.get("subject", ""),
            content=json.loads(data["content"]) if isinstance(data.get("content"), str) and (data["content"].startswith("[") or data["content"].startswith("{")) else data.get("content"),
            priority=data.get("priority", MessagePriority.NORMAL.value),
            correlation_id=data.get("correlation_id", ""),
            metadata=json.loads(data["metadata"]) if isinstance(data.get("metadata"), str) else data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.now()),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            retry_count=data.get("retry_count", 0),
        )


@dataclass 
class Task:
    """Task for agent execution"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    description: str = ""
    assigned_to: str = ""
    status: str = "pending"  # pending, in_progress, completed, failed
    priority: int = MessagePriority.NORMAL.value
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "status": self.status,
            "priority": self.priority,
            "input_data": json.dumps(self.input_data),
            "output_data": json.dumps(self.output_data) if self.output_data else None,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "retry_count": self.retry_count,
            "metadata": json.dumps(self.metadata),
        }


class MessageBus:
    """
    Central message bus for agent communication.
    Handles message routing, task distribution, and event coordination.
    """
    
    def __init__(self):
        self.lock = threading.RLock()
        self.mailboxes: Dict[str, List[Message]] = defaultdict(list)
        self.subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        self.pending_tasks: Dict[str, Task] = {}
        self.task_queues: Dict[str, List[Task]] = defaultdict(list)
        self.agents: Dict[str, Dict] = {}  # agent_id -> agent_info
        self.message_history: List[Message] = []
        self.max_history = 1000
        
        # Event loops for async handlers
        self._async_handlers = []
        
        logger.info("MessageBus initialized")
    
    # === Agent Registration ===
    
    def register_agent(self, agent_id: str, agent_type: str, capabilities: List[str] = None):
        """Register an agent"""
        with self.lock:
            self.agents[agent_id] = {
                "id": agent_id,
                "type": agent_type,
                "capabilities": capabilities or [],
                "status": "online",
                "registered_at": datetime.now(),
                "last_heartbeat": datetime.now(),
            }
            logger.info(f"Agent registered: {agent_id} ({agent_type})")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id]["status"] = "offline"
                del self.agents[agent_id]
                logger.info(f"Agent unregistered: {agent_id}")
    
    def get_online_agents(self) -> List[Dict]:
        """Get all online agents"""
        with self.lock:
            return [a for a in self.agents.values() if a.get("status") == "online"]
    
    def heartbeat(self, agent_id: str):
        """Update agent heartbeat"""
        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id]["last_heartbeat"] = datetime.now()
    
    # === Message Sending ===

    def _normalize_priority(self, priority: Any) -> MessagePriority:
        """Normalize priority from enum/int/string values."""
        if isinstance(priority, MessagePriority):
            return priority

        if isinstance(priority, int):
            for enum_value in MessagePriority:
                if enum_value.value == priority:
                    return enum_value
            return MessagePriority.NORMAL

        if isinstance(priority, str):
            try:
                return MessagePriority[priority.upper()]
            except KeyError:
                return MessagePriority.NORMAL

        return MessagePriority.NORMAL
    
    def send_message(
        self,
        sender: str,
        recipient: str,
        message_type: MessageType,
        subject: str = "",
        content: Any = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: str = "",
        expires_in_seconds: int = 3600,
    ) -> Message:
        """Send a message to an agent or broadcast"""
        normalized_priority = self._normalize_priority(priority)
        expires_at = (
            datetime.now() + timedelta(seconds=expires_in_seconds)
            if expires_in_seconds
            else None
        )

        msg = Message(
            type=message_type.value,
            sender=sender,
            recipient=recipient,
            subject=subject,
            content=content,
            priority=normalized_priority.value,
            correlation_id=correlation_id,
            expires_at=expires_at,
        )
        
        with self.lock:
            if recipient:  # Direct message
                self.mailboxes[recipient].append(msg)
            else:  # Broadcast
                for agent_id in self.agents:
                    self.mailboxes[agent_id].append(msg)
            
            # Add to history
            self.message_history.append(msg)
            if len(self.message_history) > self.max_history:
                self.message_history = self.message_history[-self.max_history:]
        
        # Notify subscribers
        self._notify_subscribers(msg)
        
        logger.debug(f"Message sent: {sender} -> {recipient or 'broadcast'} [{message_type.value}]")
        return msg
    
    def send_broadcast(self, sender: str, subject: str, content: Any, priority: MessagePriority = MessagePriority.NORMAL):
        """Broadcast to all agents"""
        return self.send_message(sender, "", MessageType.BROADCAST, subject, content, priority)
    
    def reply_to(self, original_message: Message, content: Any, sender: str = "") -> Message:
        """Reply to a message"""
        return self.send_message(
            sender=sender or original_message.recipient,
            recipient=original_message.sender,
            message_type=MessageType.REPLY,
            subject=f"Re: {original_message.subject}",
            content=content,
            correlation_id=original_message.id,
        )
    
    # === Message Receiving ===
    
    def get_messages(self, agent_id: str, mark_read: bool = True) -> List[Message]:
        """Get messages for an agent"""
        with self.lock:
            messages = self.mailboxes.get(agent_id, [])
            if mark_read:
                self.mailboxes[agent_id] = []
            return messages
    
    def peek_messages(self, agent_id: str) -> List[Message]:
        """Peek at messages without removing"""
        with self.lock:
            return self.mailboxes.get(agent_id, []).copy()
    
    def wait_for_message(self, agent_id: str, timeout_seconds: int = 30) -> Optional[Message]:
        """Wait for a message with timeout"""
        start = time.time()
        while time.time() - start < timeout_seconds:
            messages = self.get_messages(agent_id)
            if messages:
                return messages[0]
            time.sleep(0.5)
        return None
    
    # === Subscriptions ===
    
    def subscribe(self, pattern: str, callback: Callable):
        """Subscribe to messages matching pattern"""
        with self.lock:
            self.subscriptions[pattern].append(callback)
    
    def unsubscribe(self, pattern: str, callback: Callable):
        """Unsubscribe from pattern"""
        with self.lock:
            if pattern in self.subscriptions:
                self.subscriptions[pattern].remove(callback)
    
    def _notify_subscribers(self, message: Message):
        """Notify subscribers of new message"""
        with self.lock:
            for pattern, callbacks in self.subscriptions.items():
                if self._matches_pattern(message, pattern):
                    for callback in callbacks:
                        try:
                            callback(message)
                        except Exception as e:
                            logger.error(f"Error in subscription callback: {e}")
    
    def _matches_pattern(self, message: Message, pattern: str) -> bool:
        """Check if message matches pattern"""
        if pattern == "*":
            return True
        if pattern == message.sender:
            return True
        if pattern == message.recipient:
            return True
        if pattern in message.subject.lower():
            return True
        if message.type == pattern:
            return True
        return False
    
    # === Task Management ===
    
    def create_task(
        self,
        task_type: str,
        description: str,
        assigned_to: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        deadline_seconds: int = None,
        input_data: Dict = None,
        metadata: Dict = None,
    ) -> Task:
        """Create a new task"""
        normalized_priority = self._normalize_priority(priority)
        deadline = (
            datetime.now() + timedelta(seconds=deadline_seconds)
            if deadline_seconds
            else None
        )

        task = Task(
            type=task_type,
            description=description,
            assigned_to=assigned_to,
            priority=normalized_priority.value,
            input_data=input_data or {},
            deadline=deadline,
            metadata=metadata or {},
        )
        
        with self.lock:
            self.pending_tasks[task.id] = task
            self.task_queues[assigned_to].append(task)
        
        # Send task assignment message
        self.send_message(
            sender="system",
            recipient=assigned_to,
            message_type=MessageType.TASK_ASSIGN,
            subject=f"New task: {task_type}",
            content=task.to_dict(),
            priority=normalized_priority,
        )
        
        logger.info(f"Task created: {task.id} -> {assigned_to}")
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        with self.lock:
            return self.pending_tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: str, output_data: Dict = None, error: str = None) -> bool:
        """Update task status"""
        with self.lock:
            if task_id not in self.pending_tasks:
                return False
            
            task = self.pending_tasks[task_id]
            task.status = status
            
            if status == "in_progress" and not task.started_at:
                task.started_at = datetime.now()
            elif status in ["completed", "failed"]:
                task.completed_at = datetime.now()
            
            if output_data:
                task.output_data = output_data
            if error:
                task.error = error
            
            # Notify task creator
            if task.metadata.get("creator"):
                self.send_message(
                    sender="system",
                    recipient=task.metadata["creator"],
                    message_type=MessageType.TASK_RESULT,
                    subject=f"Task {status}: {task.type}",
                    content=task.to_dict(),
                )
            
            return True
    
    def get_tasks_for_agent(self, agent_id: str, status: str = None) -> List[Task]:
        """Get tasks assigned to an agent"""
        with self.lock:
            tasks = self.task_queues.get(agent_id, [])
            if status:
                tasks = [t for t in tasks if t.status == status]
            return tasks
    
    def complete_task(self, task_id: str, result: Dict) -> bool:
        """Mark task as completed"""
        return self.update_task_status(task_id, "completed", output_data=result)
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """Mark task as failed"""
        return self.update_task_status(task_id, "failed", error=error)
    
    def retry_task(self, task_id: str) -> bool:
        """Retry a failed task"""
        with self.lock:
            if task_id not in self.pending_tasks:
                return False
            
            task = self.pending_tasks[task_id]
            if task.status != "failed":
                return False
            
            task.status = "pending"
            task.retry_count += 1
            task.error = None
            
            self.send_message(
                sender="system",
                recipient=task.assigned_to,
                message_type=MessageType.TASK_ASSIGN,
                subject=f"Retry task: {task.type}",
                content=task.to_dict(),
            )
            
            return True
    
    # === Approval Workflow ===
    
    def request_approval(self, requester: str, subject: str, details: Dict, value: float = 0) -> str:
        """Request human approval"""
        approval_id = str(uuid.uuid4())
        
        self.send_message(
            sender=requester,
            recipient="human",
            message_type=MessageType.APPROVAL_REQUEST,
            subject=subject,
            content={
                "approval_id": approval_id,
                "requester": requester,
                "details": details,
                "value": value,
                "status": "pending",
            },
            priority=MessagePriority.HIGH if value > 100 else MessagePriority.NORMAL,
        )
        
        # Store approval request
        self.store_pending_approval(approval_id, requester, subject, details, value)
        
        return approval_id
    
    def store_pending_approval(self, approval_id: str, requester: str, subject: str, details: Dict, value: float):
        """Store pending approval request"""
        with self.lock:
            self.mailboxes["pending_approvals"].append(Message(
                type=MessageType.APPROVAL_REQUEST.value,
                sender=requester,
                subject=subject,
                content={
                    "approval_id": approval_id,
                    "requester": requester,
                    "details": details,
                    "value": value,
                    "status": "pending",
                },
            ))
    
    def approve(self, approval_id: str, approver: str = "human") -> bool:
        """Approve a request"""
        with self.lock:
            for messages in self.mailboxes.values():
                for msg in messages:
                    if msg.content and msg.content.get("approval_id") == approval_id:
                        msg.content["status"] = "approved"
                        msg.content["approver"] = approver
                        msg.content["approved_at"] = datetime.now().isoformat()
                        
                        # Notify requester
                        self.send_message(
                            sender="system",
                            recipient=msg.sender,
                            message_type=MessageType.APPROVAL_RESPONSE,
                            subject="Request Approved",
                            content=msg.content,
                        )
                        return True
        return False
    
    def reject(self, approval_id: str, reason: str = "", approver: str = "human") -> bool:
        """Reject a request"""
        with self.lock:
            for messages in self.mailboxes.values():
                for msg in messages:
                    if msg.content and msg.content.get("approval_id") == approval_id:
                        msg.content["status"] = "rejected"
                        msg.content["reason"] = reason
                        msg.content["approver"] = approver
                        msg.content["rejected_at"] = datetime.now().isoformat()
                        
                        # Notify requester
                        self.send_message(
                            sender="system",
                            recipient=msg.sender,
                            message_type=MessageType.APPROVAL_RESPONSE,
                            subject="Request Rejected",
                            content=msg.content,
                        )
                        return True
        return False
    
    # === Escalation ===
    
    def escalate(self, from_agent: str, subject: str, details: Dict, urgency: MessagePriority = MessagePriority.HIGH):
        """Escalate issue to human"""
        self.send_message(
            sender=from_agent,
            recipient="human",
            message_type=MessageType.ESCALATION,
            subject=f"ESCALATION: {subject}",
            content=details,
            priority=urgency,
        )
    
    # === Statistics ===
    
    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics"""
        with self.lock:
            total_messages = sum(len(m) for m in self.mailboxes.values())
            
            return {
                "total_agents": len(self.agents),
                "online_agents": len([a for a in self.agents.values() if a.get("status") == "online"]),
                "pending_tasks": len(self.pending_tasks),
                "total_messages": total_messages,
                "message_history_size": len(self.message_history),
                "subscriptions": len(self.subscriptions),
            }
    
    def get_agent_status(self) -> Dict[str, Dict]:
        """Get status of all agents"""
        with self.lock:
            return self.agents.copy()


# Global message bus instance
_message_bus: Optional[MessageBus] = None


def get_message_bus() -> MessageBus:
    """Get global message bus"""
    global _message_bus
    if _message_bus is None:
        _message_bus = MessageBus()
    return _message_bus
