# Ledger 2.0 Governance System
## All Phases Integrated

import asyncio

from .phase1_core import (
    CapabilityIssuer,
    CapabilityToken,
    RiskClassifier,
    RiskLevel,
    FeatureFlagController,
    LedgerGovernanceV2
)

from .phase2_orchestration import (
    AgentCapability,
    AgentRegistration,
    AgentCapabilityRegistry,
    AgentHealth,
    Task,
    ChiefOfStaff,
    ScheduledJob,
    AutoGovernor
)

from .phase3_memory import (
    EventType,
    GovernanceEvent,
    EventStream,
    ConsolidationResult,
    MemoryConsolidator,
    TracePropagator
)

from .phase4_hardening import (
    SandboxType,
    SandboxConfig,
    SandboxResult,
    SandboxedExecutor,
    FallbackBehavior,
    GracefulDegradation,
    EmergencyKillSwitch
)

# Optional audit service (requires asyncpg)
try:
    from .audit_service import AuditLogService, get_audit_service
    AUDIT_SERVICE_AVAILABLE = True
except ImportError:
    AUDIT_SERVICE_AVAILABLE = False
    AuditLogService = None
    get_audit_service = None

# Integration class that ties everything together
class LedgerGovernanceSystem:
    """
    Complete Ledger 2.0 Governance System.
    
    Integrates all 4 phases:
    - Phase 1: Core Governance (capabilities, risk, flags)
    - Phase 2: Orchestration (registry, chief of staff, auto-governor)
    - Phase 3: Memory & Audit (events, consolidation, tracing)
    - Phase 4: Hardening (sandboxing, degradation, kill switches)
    """
    
    def __init__(self, ledger_sovereign, storage_path: str = "./governance_data"):
        self.ledger = ledger_sovereign
        self.storage_path = storage_path
        
        # Phase 1: Core
        self.governance = LedgerGovernanceV2(ledger_sovereign)
        
        # Phase 2: Orchestration
        self.registry = AgentCapabilityRegistry()
        self.chief_of_staff = ChiefOfStaff(self.registry, ledger_sovereign)
        self.auto_governor = AutoGovernor(self.chief_of_staff, self.registry)
        
        # Phase 3: Memory & Audit
        self.event_stream = EventStream(f"{storage_path}/events")
        self.memory_consolidator = MemoryConsolidator(
            self.event_stream,
            f"{storage_path}/memory"
        )
        self.tracer = TracePropagator()
        
        # Phase 4: Hardening
        self.sandbox_executor = SandboxedExecutor(ledger_sovereign)
        self.degradation = GracefulDegradation(ledger_sovereign)
        self.kill_switches = EmergencyKillSwitch(self.governance.feature_flags)
        
        # Register default kill switches
        self._setup_kill_switches()
        
    def _setup_kill_switches(self):
        """Setup emergency kill switches."""
        self.kill_switches.register_kill_switch(
            "autonomous_mode",
            ["auto_governor", "autonomous_repair"]
        )
        self.kill_switches.register_kill_switch(
            "all_writes",
            ["write", "update", "create", "delete"]
        )
        self.kill_switches.register_kill_switch(
            "external_actions",
            ["publish", "send", "notify", "post"]
        )
    
    async def start(self):
        """Start all background services."""
        # Start event stream
        asyncio.create_task(self.event_stream.start())
        
        # Start auto-governor
        asyncio.create_task(self.auto_governor.start())
        
        print("✅ Ledger 2.0 Governance System started")
    
    def stop(self):
        """Stop all background services."""
        self.event_stream.stop()
        self.auto_governor.stop()
    
    async def execute_action(
        self,
        agent_id: str,
        action: str,
        resource: str,
        context: dict,
        use_sandbox: bool = True
    ) -> dict:
        """
        Execute an action through the full governance pipeline.
        
        Pipeline:
        1. Check degradation level
        2. Check kill switches
        3. Start trace
        4. Check feature flags
        5. Classify risk
        6. Issue capability token
        7. Execute (sandboxed if requested)
        8. Emit event
        9. Record decision for consolidation
        """
        trace_id = self.tracer.start_trace()
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Check degradation
            if self.degradation.current_level != "normal":
                result = await self.degradation.handle_action(action, context)
                if not result.get("success"):
                    return result
            
            # Step 2: Check feature flags
            business_id = context.get("business_id")
            if not self.governance.feature_flags.can_use(action, business_id):
                return {
                    "status": "blocked",
                    "reason": "Feature not enabled",
                    "trace_id": trace_id
                }
            
            # Step 3: Classify and execute
            result = await self.governance.execute_action(
                agent_id, action, resource, context
            )
            
            # Step 4: Emit event
            latency = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            event = GovernanceEvent(
                event_id=GovernanceEvent.generate_id(),
                trace_id=trace_id,
                timestamp=datetime.utcnow(),
                event_type=EventType.ACTION,
                agent_id=agent_id,
                business_id=business_id or 0,
                action=action,
                resource=resource,
                risk_level=result.get("risk_level", "unknown"),
                decision=result.get("status", "unknown"),
                reasoning=result.get("reason", ""),
                constitution_rules=[],
                latency_ms=latency,
                metadata=context
            )
            
            await self.event_stream.emit(event)
            
            # Step 5: Record for consolidation
            self.memory_consolidator.record_decision()
            
            result["trace_id"] = trace_id
            return result
            
        finally:
            self.tracer.end_trace()
    
    def get_status(self) -> dict:
        """Get full system status."""
        return {
            "phase1_governance": {
                "feature_flags": self.governance.feature_flags.get_status()
            },
            "phase2_orchestration": {
                "registered_agents": len(self.registry.agents),
                "queue_status": self.chief_of_staff.get_queue_status(),
                "auto_governor": self.auto_governor.get_status()
            },
            "phase3_memory": {
                "consolidation_state": self.memory_consolidator._get_state()
            },
            "phase4_hardening": {
                "degradation_level": self.degradation.current_level,
                "kill_switches": self.kill_switches.get_status()
            }
        }


__all__ = [
    # Phase 1
    'CapabilityIssuer', 'CapabilityToken', 'RiskClassifier', 'RiskLevel',
    'FeatureFlagController', 'LedgerGovernanceV2',
    # Phase 2
    'AgentCapability', 'AgentRegistration', 'AgentCapabilityRegistry',
    'AgentHealth', 'Task', 'ChiefOfStaff', 'ScheduledJob', 'AutoGovernor',
    # Phase 3
    'EventType', 'GovernanceEvent', 'EventStream', 'ConsolidationResult',
    'MemoryConsolidator', 'TracePropagator',
    # Phase 4
    'SandboxType', 'SandboxConfig', 'SandboxResult', 'SandboxedExecutor',
    'FallbackBehavior', 'GracefulDegradation', 'EmergencyKillSwitch',
    # Integration
    'LedgerGovernanceSystem'
]

# Version
__version__ = "2.0.0"
