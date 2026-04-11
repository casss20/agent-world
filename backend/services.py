from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models import (
    Room, RoomAgent, Agent, Task, Message, Activity, Project, Tenant
)
import json

class RoomService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_room(self, project_id: UUID, name: str, description: str = None,
                   room_type: str = "general", guidelines: dict = None) -> Room:
        """Create a new room in a project"""
        room = Room(
            project_id=project_id,
            name=name,
            description=description,
            room_type=room_type,
            guidelines=guidelines or {}
        )
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        
        # Log activity
        self._log_activity(room.id, None, "room_created", f"Room '{name}' created")
        
        return room
    
    def get_room(self, room_id: UUID) -> Optional[Room]:
        """Get room by ID with all relationships"""
        return self.db.query(Room).filter(Room.id == room_id).first()
    
    def get_project_rooms(self, project_id: UUID) -> List[Room]:
        """Get all rooms in a project"""
        return self.db.query(Room).filter(
            Room.project_id == project_id,
            Room.status == 'active'
        ).all()
    
    def get_shared_context(self, room_id: UUID) -> dict:
        """Get current shared context for a room"""
        room = self.get_room(room_id)
        return room.shared_context if room else {}
    
    def update_context(self, room_id: UUID, agent_id: UUID, updates: dict) -> dict:
        """Update shared context (merge strategy)"""
        room = self.get_room(room_id)
        if not room:
            return None
        
        # Merge updates into existing context
        current = room.shared_context or {}
        current.update(updates)
        room.shared_context = current
        
        self.db.commit()
        
        # Log the update
        self._log_activity(
            room_id, agent_id, "context_updated",
            f"Updated context: {list(updates.keys())}"
        )
        
        return current
    
    def add_artifact(self, room_id: UUID, agent_id: UUID, url: str, metadata: dict = None):
        """Add an artifact URL to room"""
        room = self.get_room(room_id)
        if not room:
            return None
        
        room.artifact_urls = room.artifact_urls or []
        room.artifact_urls.append(url)
        
        self.db.commit()
        
        self._log_activity(
            room_id, agent_id, "artifact_added",
            f"Added artifact: {url[:50]}..."
        )
        
        return room.artifact_urls
    
    def agent_enter_room(self, room_id: UUID, agent_id: UUID,
                        position: tuple = (0, 0, 0)) -> RoomAgent:
        """Agent enters a room"""
        # Check if already in room
        existing = self.db.query(RoomAgent).filter(
            RoomAgent.room_id == room_id,
            RoomAgent.agent_id == agent_id
        ).first()
        
        if existing:
            existing.status = 'idle'
            existing.left_at = None
            existing.last_heartbeat = datetime.utcnow()
            self.db.commit()
            return existing
        
        room_agent = RoomAgent(
            room_id=room_id,
            agent_id=agent_id,
            status='idle',
            position_x=position[0],
            position_y=position[1],
            position_z=position[2]
        )
        self.db.add(room_agent)
        self.db.commit()
        self.db.refresh(room_agent)
        
        self._log_activity(
            room_id, agent_id, "agent_joined",
            f"Agent entered room"
        )
        
        return room_agent
    
    def agent_leave_room(self, room_id: UUID, agent_id: UUID):
        """Agent leaves room"""
        room_agent = self.db.query(RoomAgent).filter(
            RoomAgent.room_id == room_id,
            RoomAgent.agent_id == agent_id
        ).first()
        
        if room_agent:
            room_agent.status = 'offline'
            room_agent.left_at = datetime.utcnow()
            self.db.commit()
            
            self._log_activity(
                room_id, agent_id, "agent_left",
                f"Agent left room"
            )
    
    def update_agent_status(self, room_id: UUID, agent_id: UUID,
                           status: str, current_task_id: UUID = None):
        """Update agent's status in room"""
        room_agent = self.db.query(RoomAgent).filter(
            RoomAgent.room_id == room_id,
            RoomAgent.agent_id == agent_id
        ).first()
        
        if room_agent:
            room_agent.status = status
            room_agent.current_task_id = current_task_id
            room_agent.last_heartbeat = datetime.utcnow()
            self.db.commit()
    
    def get_active_agents(self, room_id: UUID) -> List[dict]:
        """Get all active agents in room with their status"""
        room_agents = self.db.query(RoomAgent).filter(
            RoomAgent.room_id == room_id,
            RoomAgent.status != 'offline'
        ).all()
        
        result = []
        for ra in room_agents:
            agent = self.db.query(Agent).filter(Agent.id == ra.agent_id).first()
            if agent:
                result.append({
                    'agent_id': str(agent.id),
                    'name': agent.name,
                    'role': agent.role,
                    'color': agent.color,
                    'status': ra.status,
                    'current_task_id': str(ra.current_task_id) if ra.current_task_id else None,
                    'position': {
                        'x': ra.position_x,
                        'y': ra.position_y,
                        'z': ra.position_z
                    },
                    'last_heartbeat': ra.last_heartbeat.isoformat() if ra.last_heartbeat else None
                })
        
        return result
    
    def get_room_state(self, room_id: UUID) -> dict:
        """Get complete room state for WebSocket broadcast"""
        room = self.get_room(room_id)
        if not room:
            return None
        
        # Get recent messages
        messages = self.db.query(Message).filter(
            Message.room_id == room_id
        ).order_by(desc(Message.created_at)).limit(50).all()
        
        # Get active tasks
        tasks = self.db.query(Task).filter(
            Task.room_id == room_id,
            Task.status.in_(['pending', 'queued', 'active', 'review'])
        ).all()
        
        return {
            'room': {
                'id': str(room.id),
                'name': room.name,
                'description': room.description,
                'room_type': room.room_type
            },
            'shared_context': room.shared_context,
            'artifact_urls': room.artifact_urls or [],
            'active_agents': self.get_active_agents(room_id),
            'active_tasks': [
                {
                    'id': str(t.id),
                    'title': t.title,
                    'status': t.status,
                    'owner_agent_id': str(t.owner_agent_id),
                    'progress': self._calculate_task_progress(t)
                }
                for t in tasks
            ],
            'recent_messages': [
                {
                    'id': str(m.id),
                    'from_agent_id': str(m.from_agent_id),
                    'to_agent_id': str(m.to_agent_id) if m.to_agent_id else None,
                    'content': m.content,
                    'message_type': m.message_type,
                    'created_at': m.created_at.isoformat()
                }
                for m in reversed(messages)
            ]
        }
    
    def _log_activity(self, room_id: UUID, agent_id: Optional[UUID],
                     activity_type: str, description: str):
        """Internal: log activity"""
        activity = Activity(
            room_id=room_id,
            agent_id=agent_id,
            activity_type=activity_type,
            description=description
        )
        self.db.add(activity)
        self.db.commit()
    
    def _calculate_task_progress(self, task: Task) -> int:
        """Estimate task progress based on status"""
        status_progress = {
            'pending': 0,
            'queued': 5,
            'active': 50,
            'review': 90,
            'completed': 100,
            'failed': 0
        }
        return status_progress.get(task.status, 0)


class MessageService:
    def __init__(self, db: Session):
        self.db = db
    
    def send_message(self, room_id: UUID, from_agent_id: UUID,
                    content: str, to_agent_id: UUID = None,
                    message_type: str = "chat", metadata: dict = None) -> Message:
        """Send a message (broadcast if to_agent_id is None)"""
        message = Message(
            room_id=room_id,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            content=content,
            message_type=message_type,
            metadata=metadata or {}
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        return message
    
    def get_room_messages(self, room_id: UUID, limit: int = 50) -> List[Message]:
        """Get recent messages in room"""
        return self.db.query(Message).filter(
            Message.room_id == room_id
        ).order_by(desc(Message.created_at)).limit(limit).all()
    
    def get_agent_dm_history(self, room_id: UUID, agent1_id: UUID,
                            agent2_id: UUID, limit: int = 50) -> List[Message]:
        """Get DM history between two agents in a room"""
        return self.db.query(Message).filter(
            Message.room_id == room_id,
            ((Message.from_agent_id == agent1_id) & (Message.to_agent_id == agent2_id)) |
            ((Message.from_agent_id == agent2_id) & (Message.to_agent_id == agent1_id))
        ).order_by(desc(Message.created_at)).limit(limit).all()


class TaskService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_task(self, room_id: UUID, owner_agent_id: UUID,
                   task_type: str, title: str, description: str = None,
                   priority: int = 3, input_payload: dict = None,
                   contributor_ids: List[UUID] = None) -> Task:
        """Create a new task"""
        task = Task(
            room_id=room_id,
            owner_agent_id=owner_agent_id,
            type=task_type,
            title=title,
            description=description,
            priority=priority,
            input_payload=input_payload or {},
            contributor_agent_ids=contributor_ids or [],
            status='pending'
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        # Log activity
        activity = Activity(
            room_id=room_id,
            agent_id=owner_agent_id,
            task_id=task.id,
            activity_type='task_created',
            description=f"Created task: {title}"
        )
        self.db.add(activity)
        self.db.commit()
        
        return task
    
    def assign_contributors(self, task_id: UUID, contributor_ids: List[UUID]):
        """Add contributors to a task"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if task:
            current = task.contributor_agent_ids or []
            current.extend(contributor_ids)
            task.contributor_agent_ids = list(set(current))
            self.db.commit()
    
    def start_task(self, task_id: UUID, agent_id: UUID) -> bool:
        """Agent starts working on task"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task or task.owner_agent_id != agent_id:
            return False
        
        task.status = 'active'
        task.started_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    def complete_task(self, task_id: UUID, agent_id: UUID,
                     output_payload: dict) -> bool:
        """Mark task as completed"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task or task.owner_agent_id != agent_id:
            return False
        
        task.status = 'completed'
        task.output_payload = output_payload
        task.completed_at = datetime.utcnow()
        
        # Update agent stats
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if agent:
            agent.total_tasks_completed += 1
        
        self.db.commit()
        
        return True
    
    def handoff_task(self, task_id: UUID, from_agent_id: UUID,
                    to_agent_id: UUID, handoff_notes: str = None) -> bool:
        """Transfer task ownership with context"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task or task.owner_agent_id != from_agent_id:
            return False
        
        # Add previous owner as contributor
        contributors = task.contributor_agent_ids or []
        contributors.append(from_agent_id)
        task.contributor_agent_ids = list(set(contributors))
        
        # Transfer ownership
        task.owner_agent_id = to_agent_id
        
        # Add handoff notes to input payload
        input_data = task.input_payload or {}
        input_data['handoff_from'] = str(from_agent_id)
        input_data['handoff_notes'] = handoff_notes
        task.input_payload = input_data
        
        self.db.commit()
        
        return True
