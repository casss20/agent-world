"""Week 5: Concrete repositories."""
from typing import Dict, Any, Optional, List

from infrastructure.interfaces.base_repository import BaseRepository
from database import get_session_factory
from models import Agent, TaskQueue, AuditLog


class AgentRepository(BaseRepository):
    """Repository for Agent entities."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or get_session_factory
        self._data: Dict[str, Dict[str, Any]] = {}

    async def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        session = self._session_factory()
        try:
            agent = session.query(Agent).filter(Agent.id == id).first()
            if agent:
                return {"id": str(agent.id), "name": agent.name, "status": str(agent.status)}
            return None
        finally:
            session.close()

    async def find_many(self, filters: Dict = None, order_by: str = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        session = self._session_factory()
        try:
            query = session.query(Agent)
            if filters:
                for k, v in filters.items():
                    query = query.filter(getattr(Agent, k) == v)
            agents = query.limit(limit).offset(offset).all()
            return [{"id": str(a.id), "name": a.name, "status": str(a.status)} for a in agents]
        finally:
            session.close()

    async def save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        session = self._session_factory()
        try:
            agent = Agent(**data)
            session.add(agent)
            session.commit()
            session.refresh(agent)
            return {"id": str(agent.id), **data}
        finally:
            session.close()

    async def update(self, id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        session = self._session_factory()
        try:
            agent = session.query(Agent).filter(Agent.id == id).first()
            if agent:
                for k, v in data.items():
                    setattr(agent, k, v)
                session.commit()
                return {"id": str(agent.id), **data}
            return None
        finally:
            session.close()

    async def delete(self, id: str) -> bool:
        session = self._session_factory()
        try:
            agent = session.query(Agent).filter(Agent.id == id).first()
            if agent:
                session.delete(agent)
                session.commit()
                return True
            return False
        finally:
            session.close()

    async def count(self, filters: Dict = None) -> int:
        session = self._session_factory()
        try:
            query = session.query(Agent)
            if filters:
                for k, v in filters.items():
                    query = query.filter(getattr(Agent, k) == v)
            return query.count()
        finally:
            session.close()


class TaskRepository(BaseRepository):
    """Repository for TaskQueue entities."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or get_session_factory
        self._data: Dict[str, Dict[str, Any]] = {}

    async def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        session = self._session_factory()
        try:
            task = session.query(TaskQueue).filter(TaskQueue.id == id).first()
            if task:
                return {"id": str(task.id), "task_type": task.task_type, "status": task.status}
            return None
        finally:
            session.close()

    async def find_many(self, filters: Dict = None, order_by: str = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        session = self._session_factory()
        try:
            query = session.query(TaskQueue)
            if filters:
                for k, v in filters.items():
                    query = query.filter(getattr(TaskQueue, k) == v)
            tasks = query.limit(limit).offset(offset).all()
            return [{"id": str(t.id), "task_type": t.task_type, "status": t.status} for t in tasks]
        finally:
            session.close()

    async def save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        session = self._session_factory()
        try:
            task = TaskQueue(**data)
            session.add(task)
            session.commit()
            session.refresh(task)
            return {"id": str(task.id), **data}
        finally:
            session.close()

    async def update(self, id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        session = self._session_factory()
        try:
            task = session.query(TaskQueue).filter(TaskQueue.id == id).first()
            if task:
                for k, v in data.items():
                    setattr(task, k, v)
                session.commit()
                return {"id": str(task.id), **data}
            return None
        finally:
            session.close()

    async def delete(self, id: str) -> bool:
        session = self._session_factory()
        try:
            task = session.query(TaskQueue).filter(TaskQueue.id == id).first()
            if task:
                session.delete(task)
                session.commit()
                return True
            return False
        finally:
            session.close()

    async def count(self, filters: Dict = None) -> int:
        session = self._session_factory()
        try:
            query = session.query(TaskQueue)
            if filters:
                for k, v in filters.items():
                    query = query.filter(getattr(TaskQueue, k) == v)
            return query.count()
        finally:
            session.close()


class LedgerRepository(BaseRepository):
    """Repository for AuditLog entities."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or get_session_factory

    async def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        session = self._session_factory()
        try:
            log = session.query(AuditLog).filter(AuditLog.id == id).first()
            if log:
                return {"id": str(log.id), "action": log.action, "decision": log.decision}
            return None
        finally:
            session.close()

    async def find_many(self, filters: Dict = None, order_by: str = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        session = self._session_factory()
        try:
            query = session.query(AuditLog)
            if filters:
                for k, v in filters.items():
                    query = query.filter(getattr(AuditLog, k) == v)
            logs = query.limit(limit).offset(offset).all()
            return [{"id": str(l.id), "action": l.action, "decision": l.decision} for l in logs]
        finally:
            session.close()

    async def save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        session = self._session_factory()
        try:
            log = AuditLog(**data)
            session.add(log)
            session.commit()
            session.refresh(log)
            return {"id": str(log.id), **data}
        finally:
            session.close()

    async def update(self, id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        session = self._session_factory()
        try:
            log = session.query(AuditLog).filter(AuditLog.id == id).first()
            if log:
                for k, v in data.items():
                    setattr(log, k, v)
                session.commit()
                return {"id": str(log.id), **data}
            return None
        finally:
            session.close()

    async def delete(self, id: str) -> bool:
        session = self._session_factory()
        try:
            log = session.query(AuditLog).filter(AuditLog.id == id).first()
            if log:
                session.delete(log)
                session.commit()
                return True
            return False
        finally:
            session.close()

    async def count(self, filters: Dict = None) -> int:
        session = self._session_factory()
        try:
            query = session.query(AuditLog)
            if filters:
                for k, v in filters.items():
                    query = query.filter(getattr(AuditLog, k) == v)
            return query.count()
        finally:
            session.close()
