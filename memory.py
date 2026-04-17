"""
MAMS - Matrix Agentic Money System
Hybrid Memory System: SQLite (Structured) + ChromaDB (Vector/Semantic)
"""

import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import loguru
import chromadb
from chromadb.config import Settings

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
    id: Optional[Union[int, str]] = None
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
        raw_value = data.get("value", "")
        parsed_value = raw_value
        if isinstance(raw_value, str):
            stripped = raw_value.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    parsed_value = json.loads(raw_value)
                except json.JSONDecodeError:
                    parsed_value = raw_value

        return cls(
            id=data.get("id"),
            key=data.get("key", ""),
            value=parsed_value,
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
    Hybrid Memory System:
    - SQLite for exact key-value lookups and structured storage.
    - ChromaDB for vector-based semantic search.
    """
    
    def __init__(self, db_path: str = "data/mams_memory.db", vector_path: str = "data/chroma_db"):
        self.db_path = db_path
        self.vector_path = vector_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.lock = threading.RLock()
        self._init_sqlite()
        self._init_vector_db()
        
        self.subscribers: Dict[str, List[Callable]] = {}
        logger.info(f"Hybrid Memory initialized. SQLite: {db_path}, VectorDB: {vector_path}")
    
    def _init_sqlite(self):
        """Initialize SQLite database for structured storage"""
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
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(memory_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_key ON memory(key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_tags ON memory(tags)")
            conn.commit()
            conn.close()

    def _init_vector_db(self):
        """Initialize ChromaDB for semantic search"""
        try:
            self.chroma_client = chromadb.PersistentClient(path=self.vector_path)
            self.collection = self.chroma_client.get_or_create_collection(
                name="mams_semantic_memory",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB collection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.collection = None

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
        """Store a value in both structured (SQLite) and semantic (Vector) memory"""
        with self.lock:
            try:
                # 1. Store in SQLite for fast lookup
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
                
                # 2. Store in VectorDB if it's semantic or long-term knowledge
                if self.collection and memory_type in [MemoryType.SEMANTIC, MemoryType.LONG_TERM]:
                    self._store_vector(key, value, agent_id, tags, metadata)
                
                self._notify_subscribers(key, value)
                logger.debug(f"Stored in memory: {key} ({memory_type.value})")
                return True
                
            except Exception as e:
                logger.error(f"Error storing memory: {e}")
                return False

    def _store_vector(self, key: str, value: Any, agent_id: str, tags: List[str], metadata: Dict):
        """Internal method to handle ChromaDB updates"""
        try:
            # Convert value to string for embedding
            text_content = value if isinstance(value, str) else json.dumps(value)
            
            # Combine key and tags into a metadata object for Chroma
            vec_metadata = {
                "key": key,
                "agent_id": agent_id,
                "tags": ",".join(tags) if tags else "",
                "timestamp": datetime.now().isoformat()
            }
            if metadata:
                vec_metadata.update(metadata)

            self.collection.upsert(
                ids=[key],
                documents=[text_content],
                metadatas=[vec_metadata]
            )
        except Exception as e:
            logger.warning(f"Vector store update failed for {key}: {e}")

    def retrieve(self, key: str, default: Any = None) -> Any:
        """Retrieve a value by key from SQLite"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT value, expires_at FROM memory WHERE key = ?", (key,))
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

    def semantic_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Perform a semantic search using VectorDB"""
        if not self.collection:
            logger.error("VectorDB not available for semantic search")
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            formatted_results = []
            for i in range(len(results['documents'][0])):
                doc = results['documents'][0][i]
                meta = results['metadatas'][0][i]
                dist = results['distances'][0][i] if 'distances' in results else None
                
                formatted_results.append({
                    "content": doc,
                    "metadata": meta,
                    "distance": dist,
                    "key": meta.get("key")
                })
                
            return formatted_results
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def delete(self, key: str) -> bool:
        """Delete from both SQLite and VectorDB"""
        with self.lock:
            try:
                # SQLite delete
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM memory WHERE key = ?", (key,))
                conn.commit()
                conn.close()
                
                # Vector delete
                if self.collection:
                    self.collection.delete(ids=[key])
                
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
        """Query structured memory entries"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                query_str = "SELECT * FROM memory WHERE 1=1"
                params = []
                if memory_type:
                    query_str += " AND memory_type = ?"
                    params.append(memory_type.value)
                if search_key:
                    query_str += " AND key LIKE ?"
                    params.append(f"%{search_key}%")
                if tags:
                    for tag in tags:
                        query_str += " AND tags LIKE ?"
                        params.append(f"%{tag}%")
                query_str += " AND (expires_at IS NULL OR expires_at > ?)"
                params.append(datetime.now().isoformat())
                query_str += f" ORDER BY importance DESC, created_at DESC LIMIT {limit}"
                cursor.execute(query_str, params)
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                conn.close()
                return [MemoryEntry.from_dict(dict(zip(columns, row))) for row in results]
            except Exception as e:
                logger.error(f"Error querying memory: {e}")
                return []

    def get_recent(self, limit: int = 50, memory_type: Optional[MemoryType] = None) -> List[MemoryEntry]:
        return self.query(memory_type=memory_type, limit=limit)

    def subscribe(self, key_pattern: str, callback: Callable):
        if key_pattern not in self.subscribers:
            self.subscribers[key_pattern] = []
        self.subscribers[key_pattern].append(callback)
    
    def _notify_subscribers(self, key: str, value: Any):
        for pattern, callbacks in self.subscribers.items():
            if pattern in key or pattern == "*":
                for callback in callbacks:
                    try:
                        callback(key, value)
                    except Exception as e:
                        logger.error(f"Error in subscriber callback: {e}")

    def cleanup_expired(self):
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM memory WHERE expires_at IS NOT NULL AND expires_at < ?", (datetime.now().isoformat(),))
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
                if self.collection:
                    self.collection.delete(ids=self.collection.get().ids)
                logger.info(f"Cleared memory: {memory_type or 'all'}")
            except Exception as e:
                logger.error(f"Error clearing memory: {e}")

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                stats = {}
                cursor.execute("SELECT COUNT(*) FROM memory")
                stats["total_entries"] = cursor.fetchone()[0]
                cursor.execute("SELECT memory_type, COUNT(*) FROM memory GROUP BY memory_type")
                stats["by_type"] = dict(cursor.fetchall())
                conn.close()
                if self.collection:
                    stats["vector_entries"] = len(self.collection.get().ids)
                return stats
            except Exception as e:
                logger.error(f"Error getting stats: {e}")
                return {}

    # === Convenience Methods for Agents ===
    def store_task(self, task_id: str, task_data: Dict):
        self.store(key=f"task:{task_id}", value=task_data, memory_type=MemoryType.WORKING, expires_in_seconds=86400)
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        return self.retrieve(f"task:{task_id}")
    
    def store_result(self, agent_id: str, operation: str, result: Any):
        self.store(key=f"result:{agent_id}:{operation}:{int(time.time())}", value=result, memory_type=MemoryType.EPISODIC, agent_id=agent_id, expires_in_seconds=604800)
    
    def store_knowledge(self, topic: str, knowledge: Dict):
        self.store(key=f"knowledge:{topic}", value=knowledge, memory_type=MemoryType.SEMANTIC, importance=0.8)
    
    def get_knowledge(self, topic: str) -> Optional[Dict]:
        return self.retrieve(f"knowledge:{topic}")
    
    def store_shared(self, key: str, value: Any, importance: float = 1.0):
        self.store(key=key, value=value, memory_type=MemoryType.SHARED, importance=importance)
    
    def get_shared(self, key: str, default: Any = None) -> Any:
        return self.retrieve(key, default)


_memory: Optional[SharedMemory] = None

def get_memory() -> SharedMemory:
    global _memory
    if _memory is None:
        _memory = SharedMemory()
    return _memory
