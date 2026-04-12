"""
Unit tests for webhook receiver
Ticket 1: Phase 2 Production Readiness
"""

import pytest
import hmac
import hashlib
import asyncio
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Import the module under test
import sys
sys.path.insert(0, '/root/.openclaw/workspace/agent-world/backend')

from webhook_receiver import (
    WorkflowEvent, EventProcessor, router, WEBHOOK_SECRET
)


class TestSignatureVerification:
    """Test HMAC signature verification"""
    
    def test_valid_signature_accepted(self):
        """Valid HMAC signature should pass verification"""
        processor = EventProcessor()
        
        event = WorkflowEvent(
            event_type="workflow.started",
            run_id="run_001",
            room_id="room_001",
            timestamp="2026-04-12T08:00:00Z",
            payload={},
            signature="",  # Will be computed
            event_id="evt_001"
        )
        
        # Generate valid signature
        message = f"{event.event_id}:{event.timestamp}:{event.run_id}"
        valid_sig = hmac.new(
            WEBHOOK_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        event.signature = valid_sig
        
        # Should pass
        assert asyncio.run(processor.verify_signature(event)) is True
    
    def test_invalid_signature_rejected(self):
        """Invalid signature should be rejected"""
        processor = EventProcessor()
        
        event = WorkflowEvent(
            event_type="workflow.started",
            run_id="run_001",
            room_id="room_001",
            timestamp="2026-04-12T08:00:00Z",
            payload={},
            signature="invalid_signature",
            event_id="evt_001"
        )
        
        # Should fail
        assert asyncio.run(processor.verify_signature(event)) is False
    
    def test_tampered_message_rejected(self):
        """Signature for different message should fail"""
        processor = EventProcessor()
        
        # Generate signature for one message
        message = f"evt_001:2026-04-12T08:00:00Z:run_001"
        valid_sig = hmac.new(
            WEBHOOK_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Use for different event
        event = WorkflowEvent(
            event_type="workflow.started",
            run_id="run_002",  # Different!
            room_id="room_001",
            timestamp="2026-04-12T08:00:00Z",
            payload={},
            signature=valid_sig,
            event_id="evt_001"
        )
        
        # Should fail
        assert asyncio.run(processor.verify_signature(event)) is False


class TestDuplicateDetection:
    """Test idempotency / duplicate detection"""
    
    def test_first_event_not_duplicate(self):
        """First occurrence should not be duplicate"""
        processor = EventProcessor()
        assert processor.is_duplicate("evt_001") is False
    
    def test_second_event_is_duplicate(self):
        """Same event_id should be detected as duplicate"""
        processor = EventProcessor()
        processor.is_duplicate("evt_001")  # First
        assert processor.is_duplicate("evt_001") is True  # Second
    
    def test_different_events_not_duplicate(self):
        """Different event_ids should not be duplicates"""
        processor = EventProcessor()
        processor.is_duplicate("evt_001")
        assert processor.is_duplicate("evt_002") is False


class TestEventProcessing:
    """Test full event processing pipeline"""
    
    @pytest.mark.asyncio
    async def test_workflow_started_event(self):
        """Workflow started event processed correctly"""
        processor = EventProcessor()
        
        message = f"evt_start:2026-04-12T08:00:00Z:run_start"
        valid_sig = hmac.new(
            WEBHOOK_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        event = WorkflowEvent(
            event_type="workflow.started",
            run_id="run_start",
            room_id="room_001",
            timestamp="2026-04-12T08:00:00Z",
            payload={"initiated_by": "user_001"},
            signature=valid_sig,
            event_id="evt_start"
        )
        
        response = await processor.process_event(event)
        
        assert response.status == "received"
        assert response.event_id == "evt_start"
    
    @pytest.mark.asyncio
    async def test_duplicate_event_returns_duplicate_status(self):
        """Duplicate event should return 'duplicate' status"""
        processor = EventProcessor()
        
        message = f"evt_dup:2026-04-12T08:00:00Z:run_dup"
        valid_sig = hmac.new(
            WEBHOOK_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        event = WorkflowEvent(
            event_type="workflow.started",
            run_id="run_dup",
            room_id="room_001",
            timestamp="2026-04-12T08:00:00Z",
            payload={},
            signature=valid_sig,
            event_id="evt_dup"
        )
        
        # First processing
        await processor.process_event(event)
        
        # Second processing (duplicate)
        response = await processor.process_event(event)
        
        assert response.status == "duplicate"


class TestEventValidation:
    """Test input validation"""
    
    def test_invalid_timestamp_rejected(self):
        """Invalid timestamp format should be rejected"""
        with pytest.raises(ValueError):
            WorkflowEvent(
                event_type="workflow.started",
                run_id="run_001",
                room_id="room_001",
                timestamp="not-a-timestamp",
                payload={},
                signature="sig",
                event_id="evt_001"
            )
    
    def test_valid_iso_timestamp_accepted(self):
        """Valid ISO 8601 timestamp should be accepted"""
        event = WorkflowEvent(
            event_type="workflow.started",
            run_id="run_001",
            room_id="room_001",
            timestamp="2026-04-12T08:00:00Z",
            payload={},
            signature="sig",
            event_id="evt_001"
        )
        assert event.timestamp == "2026-04-12T08:00:00Z"


class TestProcessingPerformance:
    """Test processing latency targets"""
    
    @pytest.mark.asyncio
    async def test_processing_under_200ms(self):
        """Event processing should complete in <200ms"""
        processor = EventProcessor()
        
        message = f"evt_perf:2026-04-12T08:00:00Z:run_perf"
        valid_sig = hmac.new(
            WEBHOOK_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        event = WorkflowEvent(
            event_type="workflow.started",
            run_id="run_perf",
            room_id="room_001",
            timestamp="2026-04-12T08:00:00Z",
            payload={"test": "data"},
            signature=valid_sig,
            event_id="evt_perf"
        )
        
        start = datetime.now(timezone.utc)
        await processor.process_event(event)
        elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        
        assert elapsed_ms < 200, f"Processing took {elapsed_ms:.1f}ms, expected <200ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
