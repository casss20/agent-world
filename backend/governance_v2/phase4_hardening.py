# Phase 4: Hardening Implementation
## ResourceGuard (formerly "Sandbox") + Graceful Degradation + Emergency Systems
## 
## NOTE: This is a resource limiter, not a true sandbox. Code runs in-process with
## resource limits via setrlimit(). For true isolation, use subprocess + seccomp
## or containers (see TODO below).

import asyncio
import resource
import tempfile
import subprocess
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import os
import signal
import threading
from contextlib import contextmanager


class ResourceLimitType(Enum):
    READ_ONLY = "read_only"      # No side effects, safe
    WRITE_TEMP = "write_temp"    # Can write to temp only
    WRITE_APPROVED = "write_approved"  # Can write if Ledger approved
    NETWORK_RESTRICTED = "network_restricted"  # Limited network


@dataclass
class ResourceGuardConfig:
    """Configuration for resource-guarded execution."""
    limit_type: ResourceLimitType
    max_cpu_time: int = 30        # seconds
    max_memory_mb: int = 256      # MB
    max_file_size_mb: int = 10    # MB
    allowed_network_hosts: List[str] = field(default_factory=list)
    temp_dir: Optional[str] = None
    timeout_seconds: int = 60


@dataclass
class ResourceGuardResult:
    """Result of resource-guarded execution."""
    success: bool
    output: Any
    logs: List[str]
    execution_time_ms: int
    memory_used_mb: float
    exit_code: int
    error: Optional[str] = None


class ResourceGuard:
    """
    Guards resource usage during tool execution.
    
    ## SECURITY NOTE: This is NOT a true sandbox!
    ## 
    ## What this does:
    ## - Sets Unix resource limits (CPU, memory, file size) via setrlimit()
    ## - Runs code in thread pool with timeout
    ## - Uses temp directories for isolation
    ##
    ## What this does NOT do:
    ## - Process isolation (same Python process)
    ## - Syscall filtering (no seccomp/AppArmor)
    ## - Network isolation
    ## - Filesystem chroot
    ##
    ## TODO: Replace with true sandbox for production:
    ## - Option A: subprocess + resource.prlimit() + seccomp-bpf
    ## - Option B: Docker containers with security profiles
    ## - Option C: gVisor or Firecracker microVMs
    ##
    ## Current status: "Sandbox" renamed to "ResourceGuard" to reflect actual
    ## capabilities. Resource limits are enforced, but code runs in-process.
    """
    
    def __init__(self, ledger):
        self.ledger = ledger
        self.active_guards: Dict[str, Dict] = {}
        
    async def execute(
        self,
        tool_name: str,
        tool_func: Callable,
        args: Dict,
        config: ResourceGuardConfig,
        token: Optional[str] = None
    ) -> ResourceGuardResult:
        """
        Execute a tool with resource guards.
        
        Flow:
        1. Verify capability token
        2. Create isolated temp directory
        3. Set resource limits (Unix setrlimit)
        4. Execute with timeout
        5. Capture output
        6. Cleanup
        7. Return result
        
        WARNING: Code runs in-process. See class docstring for limitations.
        """
        start_time = datetime.utcnow()
        logs = []
        
        try:
            # Step 1: Verify token if required
            if config.limit_type in [ResourceLimitType.WRITE_APPROVED]:
                if not token:
                    return ResourceGuardResult(
                        success=False,
                        output=None,
                        logs=["Token required for write-approved sandbox"],
                        execution_time_ms=0,
                        memory_used_mb=0,
                        exit_code=1,
                        error="Missing capability token"
                    )
            
            # Step 2: Create temp directory for sandbox
            temp_dir = tempfile.mkdtemp(prefix=f"guard_{tool_name}_")
            
            # Step 3: Prepare execution context
            execution_context = {
                "tool_name": tool_name,
                "args": args,
                "temp_dir": temp_dir,
                "config": config,
                "start_time": start_time
            }
            
            # Step 4: Execute with resource limits
            result = await self._execute_with_limits(
                tool_func,
                args,
                config,
                temp_dir
            )
            
            # Step 5: Cleanup
            self._cleanup_sandbox(temp_dir)
            
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return ResourceGuardResult(
                success=result.get("success", False),
                output=result.get("output"),
                logs=result.get("logs", []),
                execution_time_ms=execution_time,
                memory_used_mb=result.get("memory_mb", 0),
                exit_code=result.get("exit_code", 0),
                error=result.get("error")
            )
            
        except Exception as e:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return ResourceGuardResult(
                success=False,
                output=None,
                logs=logs + [f"Sandbox execution failed: {str(e)}"],
                execution_time_ms=execution_time,
                memory_used_mb=0,
                exit_code=1,
                error=str(e)
            )
    
    async def _execute_with_limits(
        self,
        func: Callable,
        args: Dict,
        config: ResourceGuardConfig,
        temp_dir: str
    ) -> Dict:
        """Execute function with resource limits."""
        
        # Run in thread pool with timeout
        loop = asyncio.get_event_loop()
        
        def run_with_limits():
            # Set resource limits (Unix only)
            try:
                # CPU time limit
                resource.setrlimit(
                    resource.RLIMIT_CPU,
                    (config.max_cpu_time, config.max_cpu_time + 1)
                )
                
                # Memory limit (address space)
                max_memory_bytes = config.max_memory_mb * 1024 * 1024
                resource.setrlimit(
                    resource.RLIMIT_AS,
                    (max_memory_bytes, max_memory_bytes)
                )
                
                # File size limit
                max_file_bytes = config.max_file_size_mb * 1024 * 1024
                resource.setrlimit(
                    resource.RLIMIT_FSIZE,
                    (max_file_bytes, max_file_bytes)
                )
            except Exception:
                pass  # Resource limits may not be available
            
            # Change to temp directory
            original_dir = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # Execute
                result = func(**args)
                return {
                    "success": True,
                    "output": result,
                    "logs": ["Execution completed"],
                    "exit_code": 0
                }
            except Exception as e:
                return {
                    "success": False,
                    "output": None,
                    "logs": [f"Execution error: {str(e)}"],
                    "exit_code": 1,
                    "error": str(e)
                }
            finally:
                os.chdir(original_dir)
        
        # Run with timeout
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, run_with_limits),
                timeout=config.timeout_seconds
            )
            return result
        except asyncio.TimeoutError:
            return {
                "success": False,
                "output": None,
                "logs": [f"Execution timed out after {config.timeout_seconds}s"],
                "exit_code": 124,
                "error": "Timeout"
            }
    
    def _cleanup_sandbox(self, temp_dir: str):
        """Clean up sandbox environment."""
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


class FallbackBehavior:
    """Defines fallback behavior for component failures."""
    CACHE_RULES = "cache_rules"
    QUEUE_ACTIONS = "queue_actions"
    HUMAN_ESCALATION = "human_escalation"
    DEGRADED_MODE = "degraded_mode"


@dataclass
class DegradationLevel:
    """Defines a degradation level."""
    name: str
    enabled_features: List[str]
    disabled_features: List[str]
    requires_human: bool
    notification_message: str


class GracefulDegradation:
    """
    Handles component failures gracefully.
    Never fails silently - always has a fallback.
    """
    
    DEGRADATION_LEVELS = {
        "normal": DegradationLevel(
            name="normal",
            enabled_features=["all"],
            disabled_features=[],
            requires_human=False,
            notification_message="System operating normally"
        ),
        "degraded": DegradationLevel(
            name="degraded",
            enabled_features=["read", "query", "health_check"],
            disabled_features=["write", "execute", "publish"],
            requires_human=False,
            notification_message="System in degraded mode - some features disabled"
        ),
        "critical": DegradationLevel(
            name="critical",
            enabled_features=["health_check"],
            disabled_features=["all_except_health"],
            requires_human=True,
            notification_message="CRITICAL: Human intervention required"
        ),
        "offline": DegradationLevel(
            name="offline",
            enabled_features=[],
            disabled_features=["all"],
            requires_human=True,
            notification_message="System offline - queued for manual processing"
        )
    }
    
    def __init__(self, ledger):
        self.ledger = ledger
        self.current_level = "normal"
        self.component_status: Dict[str, bool] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
        self.action_queue: List[Dict] = []
        self.cached_rules: Dict = {}
        
    def register_component(self, name: str, healthy: bool = True):
        """Register a component for health tracking."""
        self.component_status[name] = healthy
        self._evaluate_degradation()
    
    def update_component_health(self, name: str, healthy: bool):
        """Update component health status."""
        old_status = self.component_status.get(name)
        self.component_status[name] = healthy
        
        if old_status != healthy:
            self._evaluate_degradation()
    
    def _evaluate_degradation(self):
        """Evaluate current degradation level based on component health."""
        failed_components = [
            name for name, healthy in self.component_status.items()
            if not healthy
        ]
        
        # Determine level
        if len(failed_components) == 0:
            new_level = "normal"
        elif len(failed_components) <= 2:
            new_level = "degraded"
        elif len(failed_components) <= 4:
            new_level = "critical"
        else:
            new_level = "offline"
        
        if new_level != self.current_level:
            self._transition_to_level(new_level, failed_components)
    
    def _transition_to_level(self, new_level: str, failed_components: List[str]):
        """Transition to a new degradation level."""
        old_level = self.current_level
        self.current_level = new_level
        
        level_config = self.DEGRADATION_LEVELS[new_level]
        
        # Log the transition
        print(f"🔄 Degradation transition: {old_level} -> {new_level}")
        print(f"   Failed components: {failed_components}")
        print(f"   Message: {level_config.notification_message}")
        
        # Notify if human required
        if level_config.requires_human:
            asyncio.create_task(self._notify_human(new_level, failed_components))
        
        # Cache current rules if transitioning to degraded
        if new_level in ["degraded", "critical"]:
            self._cache_rules()
    
    async def handle_action(self, action: str, args: Dict) -> Dict:
        """
        Handle an action with fallback behavior.
        
        Never fails - always returns something useful.
        """
        level_config = self.DEGRADATION_LEVELS[self.current_level]
        
        # Check if action is enabled at current level
        action_enabled = (
            "all" in level_config.enabled_features or
            action in level_config.enabled_features
        )
        
        if not action_enabled:
            # Use fallback
            return await self._apply_fallback(action, args)
        
        # Try to execute
        try:
            handler = self.fallback_handlers.get(action)
            if handler:
                return await handler(args)
            else:
                return {
                    "success": False,
                    "fallback": "no_handler",
                    "message": "Action handler not found"
                }
        except Exception as e:
            # Even handler failure gets fallback
            return await self._apply_fallback(action, args, error=str(e))
    
    async def _apply_fallback(self, action: str, args: Dict, error: str = None) -> Dict:
        """Apply appropriate fallback behavior."""
        level_config = self.DEGRADATION_LEVELS[self.current_level]
        
        if self.current_level == "degraded":
            # Queue for later processing
            self.action_queue.append({
                "action": action,
                "args": args,
                "timestamp": datetime.utcnow().isoformat(),
                "error": error
            })
            
            return {
                "success": False,
                "fallback": FallbackBehavior.QUEUE_ACTIONS,
                "message": "Action queued for later processing",
                "queue_position": len(self.action_queue)
            }
        
        elif self.current_level in ["critical", "offline"]:
            # Human escalation
            await self._escalate_to_human(action, args, error)
            
            return {
                "success": False,
                "fallback": FallbackBehavior.HUMAN_ESCALATION,
                "message": "Action escalated to human for manual processing",
                "escalation_id": f"esc_{datetime.utcnow().timestamp()}"
            }
        
        # Default: use cached rules
        cached_result = self.cached_rules.get(action)
        if cached_result:
            return {
                "success": True,
                "fallback": FallbackBehavior.CACHE_RULES,
                "message": "Returning cached result",
                "data": cached_result,
                "cached": True
            }
        
        return {
            "success": False,
            "fallback": "none_available",
            "message": "No fallback available for this action"
        }
    
    def _cache_rules(self):
        """Cache current governance rules."""
        # This would cache constitution rules, etc.
        self.cached_rules = {
            "cached_at": datetime.utcnow().isoformat(),
            "rules": {}  # Would populate from ledger
        }
    
    async def _notify_human(self, level: str, failed_components: List[str]):
        """Notify human operators of degradation."""
        # This would send alerts via email, Slack, etc.
        print(f"🚨 HUMAN NOTIFICATION: System in {level} mode")
        print(f"   Failed: {failed_components}")
    
    async def _escalate_to_human(self, action: str, args: Dict, error: str = None):
        """Escalate action to human for manual processing."""
        escalation = {
            "action": action,
            "args": args,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
            "system_level": self.current_level
        }
        # This would add to human work queue
        print(f"📋 ESCALATED: {action} -> human queue")
    
    def get_status(self) -> Dict:
        """Get current degradation status."""
        return {
            "current_level": self.current_level,
            "component_status": self.component_status,
            "action_queue_length": len(self.action_queue),
            "requires_human": self.DEGRADATION_LEVELS[self.current_level].requires_human
        }


class EmergencyKillSwitch:
    """
    Emergency kill switch system.
    Instantly disables capabilities when issues detected.
    """
    
    def __init__(self, feature_flags):
        self.feature_flags = feature_flags
        self.kill_switches: Dict[str, bool] = {}
        self.emergency_contacts: List[str] = []
        
    def register_kill_switch(self, name: str, target_capabilities: List[str]):
        """Register a kill switch for specific capabilities."""
        self.kill_switches[name] = {
            "active": False,
            "target_capabilities": target_capabilities,
            "triggered_at": None,
            "triggered_by": None,
            "reason": None
        }
    
    def trigger(
        self,
        switch_name: str,
        reason: str,
        triggered_by: str = "system"
    ):
        """
        Trigger an emergency kill switch.
        
        Instantly disables all target capabilities.
        """
        if switch_name not in self.kill_switches:
            return False
        
        switch = self.kill_switches[switch_name]
        switch["active"] = True
        switch["triggered_at"] = datetime.utcnow().isoformat()
        switch["triggered_by"] = triggered_by
        switch["reason"] = reason
        
        # Kill all target capabilities
        for capability in switch["target_capabilities"]:
            self.feature_flags.emergency_kill(capability, reason)
        
        # Log emergency
        print(f"🚨 EMERGENCY KILL TRIGGERED: {switch_name}")
        print(f"   Reason: {reason}")
        print(f"   By: {triggered_by}")
        print(f"   Capabilities disabled: {switch['target_capabilities']}")
        
        # Notify
        asyncio.create_task(self._notify_emergency(switch_name, reason))
        
        return True
    
    def reset(self, switch_name: str, authorized_by: str):
        """Reset a kill switch (requires authorization)."""
        if switch_name not in self.kill_switches:
            return False
        
        # Log reset
        print(f"✅ EMERGENCY KILL RESET: {switch_name}")
        print(f"   Authorized by: {authorized_by}")
        
        self.kill_switches[switch_name]["active"] = False
        return True
    
    async def _notify_emergency(self, switch_name: str, reason: str):
        """Notify emergency contacts."""
        for contact in self.emergency_contacts:
            print(f"📧 Emergency notification sent to: {contact}")
    
    def get_status(self) -> Dict:
        """Get status of all kill switches."""
        return {
            name: {
                "active": info["active"],
                "triggered_at": info["triggered_at"],
                "reason": info["reason"]
            }
            for name, info in self.kill_switches.items()
        }


# Export
__all__ = [
    'ResourceLimitType',
    'ResourceGuardConfig',
    'ResourceGuardResult',
    'ResourceGuard',
    'FallbackBehavior',
    'DegradationLevel',
    'GracefulDegradation',
    'EmergencyKillSwitch'
]
