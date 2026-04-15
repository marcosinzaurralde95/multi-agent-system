"""
MAMS - Matrix Agentic Money System
Shared Memory System for Agent Communication
"""

import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import loguru

logger = loguru.logger


class MemoryType(Enum):
    """Types of memory storage"""
    SHORT_TERM = "short_term"      # Current session, task-related
    LONG_TERM = "long_term"        # Persistent across sessions
    EPISODIC = "episodic"          # Event snapshots
    SEMANTIC = "semantic"          # Knowledge base
    WORKING = "working"            # Active task context
    SHARED = "shared"              # Inter-agent communication


@dataclass
class MemoryEntry:
    """Single memory entry"""
    id: Optional[int] = None
    key: str = ""
    value: Any = None
    memory_type: str = MemoryType.SHORT_TERM.value
    agent_id: str = ""
    tags: List[str] = field(default_factory=list)
    importance: float = 1.0       # 0.0 - 1.0
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "key": self.key,
            "value": json.dumps(self.value) if not isinstance(self.value, str) else self.value,
            "memory_type": self.memory_type,
            "agent_id": self.agent_id,
            "tags": json.dumps(self.tags),
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": json.dumps(self.metadata),
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryEntry":
        return cls(
            id=data.get("id"),
            key=data.get("key", ""),
            value=json.loads(data["value"]) if isinstance(data.get("value"), str) and data["value"].startswith("[") or (isinstance(data.get("value"), str) and "{" in data["value"]) else data.get("value", ""),
            memory_type=data.get("memory_type", MemoryType.SHORT_TERM.value),
            agent_id=data.get("agent_id", ""),
            tags=json.loads(data["tags"]) if isinstance(data.get("tags"), str) else data.get("tags", []),
            importance=data.get("importance", 1.0),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.now()),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            metadata=json.loads(data["metadata"]) if isinstance(data.get("metadata"), str) else data.get("metadata", {}),
        )


class SharedMemory:
    """
    Centralized memory system for all agents.
    Provides thread-safe access to shared state and inter-agent communication.
    """
    
    def __init__(self, db_path: str = "data/mams_memory.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._init_database()
        self.subscribers: Dict[str, List[Callable]] = {}
        logger.info(f"SharedMemory initialized at {db_path}")
    
    def _init_database(self):
        """Initialize SQLite database"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT,
                    memory_type TEXT DEFAULT 'short_term',
                    agent_id TEXT,
                    tags TEXT,
                    importance REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(memory_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_key ON memory(key)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_tags ON memory(tags)
            """)
            
            conn.commit()
            conn.close()
    
    def store(
        self,
        key: str,
        value: Any,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        agent_id: str = "",
        tags: List[str] = None,
        importance: float = 1.0,
        expires_in_seconds: Optional[int] = None,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """Store a value in memory"""
        with self.lock:
            try:
                entry = MemoryEntry(
                    key=key,
                    value=value,
                    memory_type=memory_type.value,
                    agent_id=agent_id,
                    tags=tags or [],
                    importance=importance,
                    expires_at=datetime.now() + timedelta(seconds=expires_in_seconds) if expires_in_seconds else None,
                    metadata=metadata or {},
                )
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Use REPLACE to update existing keys
                cursor.execute("""
                    INSERT OR REPLACE INTO memory 
                    (key, value, memory_type, agent_id, tags, importance, created_at, expires_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.key,
                    json.dumps(entry.value),
                    entry.memory_type,
                    entry.agent_id,
                    json.dumps(entry.tags),
                    entry.importance,
                    entry.created_at.isoformat(),
                    entry.expires_at.isoformat() if entry.expires_at else None,
                    json.dumps(entry.metadata),
                ))
                
                conn.commit()
                conn.close()
                
                # Notify subscribers
                self._notify_subscribers(key, value)
                
                logger.debug(f"Stored in memory: {key} ({memory_type.value})")
                return True
                
            except Exception as e:
                logger.error(f"Error storing memory: {e}")
                return False
    
    def retrieve(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from memory"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT value, expires_at FROM memory WHERE key = ?
                """, (key,))
                
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    value, expires_at = result
                    if expires_at:
                        exp_time = datetime.fromisoformat(expires_at)
                        if datetime.now() > exp_time:
                            self.delete(key)
                            return default
                    
                    return json.loads(value) if isinstance(value, str) and (value.startswith("[") or value.startswith("{")) else value
                
                return default
                
            except Exception as e:
                logger.error(f"Error retrieving memory: {e}")
                return default
    
    def delete(self, key: str) -> bool:
        """Delete a memory entry"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM memory WHERE key = ?", (key,))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                logger.error(f"Error deleting memory: {e}")
                return False
    
    def query(
        self,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        search_key: Optional[str] = None,
        limit: int = 100,
    ) -> List[MemoryEntry]:
        """Query memory entries"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                query = "SELECT * FROM memory WHERE 1=1"
                params = []
                
                if memory_type:
                    query += " AND memory_type = ?"
                    params.append(memory_type.value)
                
                if search_key:
                    query += " AND key LIKE ?"
                    params.append(f"%{search_key}%")
                
                if tags:
                    for tag in tags:
                        query += " AND tags LIKE ?"
                        params.append(f"%{tag}%")
                
                # Filter expired
                query += " AND (expires_at IS NULL OR expires_at > ?)"
                params.append(datetime.now().isoformat())
                
                query += f" ORDER BY importance DESC, created_at DESC LIMIT {limit}"
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                conn.close()
                
                columns = [desc[0] for desc in cursor.description]
                entries = []
                for row in results:
                    entries.append(MemoryEntry.from_dict(dict(zip(columns, row))))
                
                return entries
                
            except Exception as e:
                logger.error(f"Error querying memory: {e}")
                return []
    
    def get_recent(self, limit: int = 50, memory_type: Optional[MemoryType] = None) -> List[MemoryEntry]:
        """Get recent memory entries"""
        return self.query(memory_type=memory_type, limit=limit)
    
    def get_by_tags(self, tags: List[str], limit: int = 100) -> List[MemoryEntry]:
        """Get entries by tags"""
        return self.query(tags=tags, limit=limit)
    
    def subscribe(self, key_pattern: str, callback: Callable):
        """Subscribe to memory changes"""
        if key_pattern not in self.subscribers:
            self.subscribers[key_pattern] = []
        self.subscribers[key_pattern].append(callback)
    
    def _notify_subscribers(self, key: str, value: Any):
        """Notify subscribers of memory changes"""
        for pattern, callbacks in self.subscribers.items():
            if pattern in key or pattern == "*":
                for callback in callbacks:
                    try:
                        callback(key, value)
                    except Exception as e:
                        logger.error(f"Error in subscriber callback: {e}")
    
    def cleanup_expired(self):
        """Remove expired memory entries"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM memory 
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                """, (datetime.now().isoformat(),))
                deleted = cursor.rowcount
                conn.commit()
                conn.close()
                
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} expired memory entries")
                
                return deleted
                
            except Exception as e:
                logger.error(f"Error cleaning up memory: {e}")
                return 0
    
    def clear(self, memory_type: Optional[MemoryType] = None):
        """Clear memory"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                if memory_type:
                    cursor.execute("DELETE FROM memory WHERE memory_type = ?", (memory_type.value,))
                else:
                    cursor.execute("DELETE FROM memory")
                
                conn.commit()
                conn.close()
                logger.info(f"Cleared memory: {memory_type or 'all'}")
                
            except Exception as e:
                logger.error(f"Error clearing memory: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                stats = {}
                
                # Total entries
                cursor.execute("SELECT COUNT(*) FROM memory")
                stats["total_entries"] = cursor.fetchone()[0]
                
                # By type
                cursor.execute("""
                    SELECT memory_type, COUNT(*) 
                    FROM memory 
                    GROUP BY memory_type
                """)
                stats["by_type"] = dict(cursor.fetchall())
                
                # Recent activity
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM memory 
                    WHERE created_at > datetime('now', '-24 hours')
                """)
                stats["last_24h"] = cursor.fetchone()[0]
                
                conn.close()
                return stats
                
            except Exception as e:
                logger.error(f"Error getting stats: {e}")
                return {}
    
    # === Convenience Methods for Agents ===
    
    def store_task(self, task_id: str, task_data: Dict):
        """Store task data"""
        self.store(
            key=f"task:{task_id}",
            value=task_data,
            memory_type=MemoryType.WORKING,
            expires_in_seconds=3600 * 24,
        )
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get task data"""
        return self.retrieve(f"task:{task_id}")
    
    def store_result(self, agent_id: str, operation: str, result: Any):
        """Store agent operation result"""
        self.store(
            key=f"result:{agent_id}:{operation}:{int(time.time())}",
            value=result,
            memory_type=MemoryType.EPISODIC,
            agent_id=agent_id,
            expires_in_seconds=3600 * 24 * 7,  # 7 days
        )
    
    def store_knowledge(self, topic: str, knowledge: Dict):
        """Store semantic knowledge"""
        self.store(
            key=f"knowledge:{topic}",
            value=knowledge,
            memory_type=MemoryType.SEMANTIC,
            importance=0.8,
        )
    
    def get_knowledge(self, topic: str) -> Optional[Dict]:
        """Get semantic knowledge"""
        return self.retrieve(f"knowledge:{topic}")
    
    def store_shared(self, key: str, value: Any, importance: float = 1.0):
        """Store shared inter-agent data"""
        self.store(
            key=key,
            value=value,
            memory_type=MemoryType.SHARED,
            importance=importance,
        )
    
    def get_shared(self, key: str, default: Any = None) -> Any:
        """Get shared data"""
        return self.retrieve(key, default)


# Global memory instance
_memory: Optional[SharedMemory] = None


def get_memory() -> SharedMemory:
    """Get global memory instance"""
    global _memory
    if _memory is None:
        _memory = SharedMemory()
    return _memory
