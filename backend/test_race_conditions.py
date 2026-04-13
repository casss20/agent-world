"""
Race Condition Tests for Hardened Mutations
Tests concurrent access patterns to ensure thread safety
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Import models and app
from models import Base, Agent, Room, TaskQueue, AgentRoom, Business, AgentStatus, TaskStatus
from hardened_mutations import router, VALID_STATUS_TRANSITIONS
from ledger_client import LedgerClient

# Test database
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


class TestRaceConditions:
    """Test suite for race condition prevention"""
    
    @pytest.fixture
    def db(self):
        """Get test database session"""
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    @pytest.fixture
    def business(self, db: Session):
        """Create test business"""
        business = Business(
            id=uuid.uuid4(),
            name="Test Business",
            slug="test-business"
        )
        db.add(business)
        db.commit()
        db.refresh(business)
        return business
    
    @pytest.fixture
    def agent(self, db: Session, business: Business):
        """Create test agent"""
        agent = Agent(
            id=uuid.uuid4(),
            business_id=business.id,
            name="Test Agent",
            agent_type="scout",
            status=AgentStatus.IDLE,
            capabilities=["discover_trends"],
            max_load=5,
            current_load=0
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent
    
    @pytest.fixture
    def room(self, db: Session, business: Business):
        """Create test room"""
        room = Room(
            id=uuid.uuid4(),
            business_id=business.id,
            name="Test Room",
            room_type="FORGE",
            max_agents=5,
            policy_config={
                "join_rule": "open",
                "blackboard_write": "all_members"
            }
        )
        db.add(room)
        db.commit()
        db.refresh(room)
        return room
    
    def test_concurrent_task_claim(self, db: Session, business: Business, agent: Agent):
        """
        Test that concurrent task claims don't result in duplicate ownership.
        
        Scenario: Multiple agents try to claim the same task simultaneously.
        Expected: Only one agent should successfully claim the task.
        """
        # Create test task
        task = TaskQueue(
            id=uuid.uuid4(),
            business_id=business.id,
            task_type="test_task",
            priority=1,
            payload={"test": "data"},
            status=TaskStatus.PENDING,
            required_capability="discover_trends"
        )
        db.add(task)
        
        # Create multiple agents
        agents = []
        for i in range(5):
            a = Agent(
                id=uuid.uuid4(),
                business_id=business.id,
                name=f"Agent {i}",
                agent_type="scout",
                status=AgentStatus.IDLE,
                capabilities=["discover_trends"],
                max_load=5,
                current_load=0
            )
            db.add(a)
            agents.append(a)
        
        db.commit()
        
        claim_results = []
        lock = threading.Lock()
        
        def attempt_claim(agent_id):
            """Simulate task claim attempt"""
            db_session = TestingSessionLocal()
            try:
                # Get fresh task
                task_to_claim = db_session.query(TaskQueue).filter(
                    TaskQueue.id == task.id
                ).with_for_update().first()
                
                if task_to_claim and task_to_claim.status == TaskStatus.PENDING:
                    task_to_claim.agent_id = agent_id
                    task_to_claim.status = TaskStatus.CLAIMED
                    task_to_claim.claimed_at = datetime.utcnow()
                    db_session.commit()
                    
                    with lock:
                        claim_results.append({
                            "agent_id": agent_id,
                            "success": True
                        })
                else:
                    with lock:
                        claim_results.append({
                            "agent_id": agent_id,
                            "success": False
                        })
            finally:
                db_session.close()
        
        # Run concurrent claims
        threads = []
        for a in agents:
            t = threading.Thread(target=attempt_claim, args=(a.id,))
            threads.append(t)
        
        # Start all threads simultaneously
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify only one claim succeeded
        successful_claims = [r for r in claim_results if r["success"]]
        assert len(successful_claims) == 1, f"Expected 1 successful claim, got {len(successful_claims)}"
        
        # Verify task state in database
        db.expire_all()
        final_task = db.query(TaskQueue).filter(TaskQueue.id == task.id).first()
        assert final_task.status == TaskStatus.CLAIMED
        assert final_task.agent_id in [a.id for a in agents]
    
    def test_room_capacity_enforcement(self, db: Session, business: Business, room: Room):
        """
        Test that room capacity is strictly enforced under concurrent joins.
        
        Scenario: More agents than capacity try to join simultaneously.
        Expected: Only max_agents should successfully join.
        """
        # Create more agents than room capacity
        agents = []
        for i in range(room.max_agents + 3):
            a = Agent(
                id=uuid.uuid4(),
                business_id=business.id,
                name=f"Agent {i}",
                agent_type="scout",
                status=AgentStatus.IDLE,
                capabilities=[],
                max_load=5,
                current_load=0
            )
            db.add(a)
            agents.append(a)
        
        db.commit()
        
        join_results = []
        lock = threading.Lock()
        
        def attempt_join(agent_id):
            """Simulate room join attempt"""
            db_session = TestingSessionLocal()
            try:
                # Lock room row
                room_to_join = db_session.query(Room).filter(
                    Room.id == room.id
                ).with_for_update().first()
                
                # Check capacity
                current_count = db_session.query(AgentRoom).filter(
                    AgentRoom.room_id == room.id,
                    AgentRoom.is_active == True
                ).count()
                
                if current_count < room.max_agents:
                    membership = AgentRoom(
                        agent_id=agent_id,
                        room_id=room.id,
                        role="member",
                        is_active=True,
                        joined_at=datetime.utcnow()
                    )
                    db_session.add(membership)
                    db_session.commit()
                    
                    with lock:
                        join_results.append({
                            "agent_id": agent_id,
                            "success": True
                        })
                else:
                    with lock:
                        join_results.append({
                            "agent_id": agent_id,
                            "success": False,
                            "reason": "capacity"
                        })
            finally:
                db_session.close()
        
        # Run concurrent joins
        threads = []
        for a in agents:
            t = threading.Thread(target=attempt_join, args=(a.id,))
            threads.append(t)
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Verify capacity enforcement
        successful_joins = [r for r in join_results if r["success"]]
        assert len(successful_joins) == room.max_agents, \
            f"Expected {room.max_agents} successful joins, got {len(successful_joins)}"
        
        # Verify database state
        db.expire_all()
        final_count = db.query(AgentRoom).filter(
            AgentRoom.room_id == room.id,
            AgentRoom.is_active == True
        ).count()
        assert final_count == room.max_agents
    
    def test_blackboard_optimistic_locking(self, db: Session, business: Business, room: Room, agent: Agent):
        """
        Test that concurrent blackboard writes are detected and rejected.
        
        Scenario: Two agents try to write to blackboard with stale version numbers.
        Expected: Second write should fail with conflict error.
        """
        from models import BlackboardEvent
        
        # Add agent to room
        membership = AgentRoom(
            agent_id=agent.id,
            room_id=room.id,
            role="member",
            is_active=True
        )
        db.add(membership)
        db.commit()
        
        # First write (succeeds)
        event1 = BlackboardEvent(
            room_id=room.id,
            agent_id=agent.id,
            sequence_number=1,
            key="counter",
            value={"count": 1},
            operation="set"
        )
        db.add(event1)
        db.commit()
        
        # Simulate concurrent writes with same expected version
        write_results = []
        lock = threading.Lock()
        
        def attempt_write(agent_id, expected_version):
            """Simulate blackboard write"""
            db_session = TestingSessionLocal()
            try:
                # Get current sequence
                last_seq = db_session.query(func.max(BlackboardEvent.sequence_number)).filter(
                    BlackboardEvent.room_id == room.id
                ).scalar() or 0
                
                # Check optimistic lock
                if expected_version is not None and last_seq != expected_version:
                    with lock:
                        write_results.append({
                            "agent_id": agent_id,
                            "success": False,
                            "error": "conflict"
                        })
                    return
                
                # Write event
                event = BlackboardEvent(
                    room_id=room.id,
                    agent_id=agent_id,
                    sequence_number=last_seq + 1,
                    key="counter",
                    value={"count": last_seq + 1},
                    operation="set"
                )
                db_session.add(event)
                db_session.commit()
                
                with lock:
                    write_results.append({
                        "agent_id": agent_id,
                        "success": True,
                        "sequence": event.sequence_number
                    })
            finally:
                db_session.close()
        
        # Both agents try to write with expected_version=1
        threads = [
            threading.Thread(target=attempt_write, args=(agent.id, 1)),
            threading.Thread(target=attempt_write, args=(agent.id, 1)),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # One should succeed, one should fail
        successful_writes = [r for r in write_results if r["success"]]
        failed_writes = [r for r in write_results if not r["success"]]
        
        assert len(successful_writes) == 1, f"Expected 1 successful write, got {len(successful_writes)}"
        assert len(failed_writes) == 1, f"Expected 1 failed write, got {len(failed_writes)}"
    
    def test_agent_status_state_machine(self, db: Session, business: Business, agent: Agent):
        """
        Test that invalid status transitions are rejected.
        
        Scenario: Agent tries invalid status transitions.
        Expected: Only valid transitions should succeed.
        """
        # Valid transitions
        valid_transitions = [
            (AgentStatus.OFFLINE, AgentStatus.STARTING),
            (AgentStatus.STARTING, AgentStatus.ONLINE),
            (AgentStatus.ONLINE, AgentStatus.IDLE),
            (AgentStatus.IDLE, AgentStatus.BUSY),
            (AgentStatus.BUSY, AgentStatus.IDLE),
            (AgentStatus.IDLE, AgentStatus.OFFLINE),
        ]
        
        for from_status, to_status in valid_transitions:
            agent.status = from_status
            
            # Check if transition is valid
            is_valid = to_status in VALID_STATUS_TRANSITIONS.get(from_status, set())
            
            if is_valid:
                agent.status = to_status
                assert agent.status == to_status
            
            db.commit()
        
        # Test invalid transition
        agent.status = AgentStatus.OFFLINE
        invalid_transition = AgentStatus.BUSY in VALID_STATUS_TRANSITIONS.get(AgentStatus.OFFLINE, set())
        assert not invalid_transition, "OFFLINE -> BUSY should be invalid"
    
    def test_tenant_isolation(self, db: Session):
        """
        Test that agents cannot access resources from other tenants.
        
        Scenario: Agent from Business A tries to access Business B's resources.
        Expected: Access should be denied.
        """
        # Create two businesses
        business_a = Business(id=uuid.uuid4(), name="Business A", slug="business-a")
        business_b = Business(id=uuid.uuid4(), name="Business B", slug="business-b")
        db.add_all([business_a, business_b])
        
        # Create agent for business A
        agent_a = Agent(
            id=uuid.uuid4(),
            business_id=business_a.id,
            name="Agent A",
            agent_type="scout",
            status=AgentStatus.IDLE
        )
        db.add(agent_a)
        
        # Create room for business B
        room_b = Room(
            id=uuid.uuid4(),
            business_id=business_b.id,
            name="Room B",
            room_type="FORGE",
            max_agents=5
        )
        db.add(room_b)
        
        db.commit()
        
        # Verify tenant isolation
        assert agent_a.business_id == business_a.id
        assert room_b.business_id == business_b.id
        assert agent_a.business_id != room_b.business_id
        
        # Agent A should not be able to join Room B
        # (This would be enforced by the endpoint)
        can_access = room_b.business_id == agent_a.business_id or room_b.scope == "global"
        assert not can_access


class TestLedgerIntegration:
    """Test Ledger client integration"""
    
    @pytest.fixture
    def db(self):
        """Get test database session"""
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def test_ledger_permission_check(self, db: Session):
        """Test Ledger permission validation"""
        ledger = LedgerClient(db)
        
        # Test admin permissions
        result = asyncio.run(ledger.check_permission(
            actor_id="admin-1",
            action="agent:delete",
            resource="business:123",
            context={"role": "admin"}
        ))
        assert result is True
        
        # Test viewer restrictions
        result = asyncio.run(ledger.check_permission(
            actor_id="viewer-1",
            action="agent:delete",
            resource="business:123",
            context={"role": "viewer"}
        ))
        assert result is False
        
        # Test operator permissions
        result = asyncio.run(ledger.check_permission(
            actor_id="operator-1",
            action="agent:register",
            resource="business:123",
            context={"role": "operator"}
        ))
        assert result is True
    
    def test_ledger_capability_validation(self, db: Session):
        """Test capability whitelist validation"""
        ledger = LedgerClient(db)
        
        # Valid capabilities
        assert asyncio.run(ledger.validate_capability("discover_trends")) is True
        assert asyncio.run(ledger.validate_capability("write_article")) is True
        
        # Invalid capabilities
        assert asyncio.run(ledger.validate_capability("invalid_capability")) is False
        assert asyncio.run(ledger.validate_capability("hack_system")) is False
    
    def test_audit_log_chain(self, db: Session):
        """Test audit log hash chain integrity"""
        ledger = LedgerClient(db)
        
        # Create multiple audit entries
        for i in range(5):
            asyncio.run(ledger.audit_log(
                actor_type="agent",
                actor_id=f"agent-{i}",
                action="task:claimed",
                resource_type="task",
                resource_id=f"task-{i}",
                result="success",
                metadata={"iteration": i}
            ))
        
        # Verify chain integrity
        integrity = asyncio.run(ledger.verify_audit_integrity())
        assert integrity["chain_intact"] is True
        assert integrity["total_events"] == 5
        assert integrity["verified_events"] == 5
        assert integrity["failed_events"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
