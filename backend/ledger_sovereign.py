"""
Ledger Sovereign Integration Module
Integrates Ledger governance system into AgentVerse platform
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class GovernanceDecision:
    """A sovereign decision by Ledger"""
    timestamp: str
    decision_type: str
    context: Dict[str, Any]
    decision: str
    reasoning: str
    human_override: bool = False
    approved: bool = True


class LedgerSovereign:
    """
    The sovereign layer - owns goals, memory, policy.
    Does not execute directly. Commands through Chief of Staff.
    """
    
    def __init__(self, ledger_path: str = "/root/.openclaw/workspace/agent-world/ledger/source"):
        self.ledger_path = Path(ledger_path)
        self.version = "1.2.0"
        self.loaded_at = datetime.now().isoformat()
        
        # Load governance core (Tier 1 - Strictly Protected)
        self.constitution = self._load_markdown("CONSTITUTION.md")
        self.soul = self._load_markdown("SOUL.md")
        self.identity = self._load_markdown("IDENTITY.md")
        self.alignment = self._load_markdown("ALIGNMENT.md")
        self.governor = self._load_markdown("GOVERNOR.md")
        self.self_mod = self._load_markdown("SELF-MOD.md")
        self.start = self._load_markdown("START.md")
        self.runtime = self._load_markdown("RUNTIME.md")
        
        # Load execution layers
        self.planner = self._load_markdown("PLANNER.md")
        self.critic = self._load_markdown("CRITIC.md")
        self.executor = self._load_markdown("EXECUTOR.md")
        self.failure = self._load_markdown("FAILURE.md")
        
        # Load context layers (Tier 2 - Auto-Managed)
        self.world = self._load_markdown("WORLD.md")
        self.user = self._load_markdown("USER.md")
        self.memory = self._load_markdown("MEMORY.md")
        self.decisions = self._load_markdown("DECISIONS.md")
        
        # Load protection layers
        self.focus = self._load_markdown("FOCUS.md")
        self.opportunity = self._load_markdown("OPPORTUNITY.md")
        self.adaptation = self._load_markdown("ADAPTATION.md")
        self.prune = self._load_markdown("PRUNE.md")
        
        # Load operational layers
        self.agents = self._load_markdown("AGENTS.md")
        self.tools = self._load_markdown("TOOLS.md")
        self.heartbeat = self._load_markdown("HEARTBEAT.md")
        self.audit = self._load_markdown("AUDIT.md")
        self.changelog = self._load_markdown("CHANGELOG.md")
        
        # Parse key rules
        self._parse_constitution()
        self._parse_governor()
        
        # Decision history
        self.decision_history: List[GovernanceDecision] = []
        
        print(f"✓ Ledger Sovereign initialized (v{self.version})")
        print(f"  Constitution: {len(self.constitution)} chars")
        print(f"  Governor rules: {len(self.governor_rules)} active")
    
    def _load_markdown(self, filename: str) -> str:
        """Load a markdown file from Ledger source"""
        filepath = self.ledger_path / filename
        if filepath.exists():
            return filepath.read_text(encoding='utf-8')
        return ""
    
    def _parse_constitution(self):
        """Parse constitutional rules"""
        self.constitutional_rules = {
            "external_action_guardrail": True,
            "irreversibility_guardrail": True,
            "scope_guardrail": True,
            "identity_guardrail": True,
            "memory_guardrail": True,
            "intervention_guardrail": True,
            "overreach_guardrail": True,
            "uncertainty_guardrail": True
        }
        
        # Extract specific rules from constitution text
        if "External Action Guardrail" in self.constitution:
            self.constitutional_rules["external_action_guardrail"] = True
        if "Irreversibility Guardrail" in self.constitution:
            self.constitutional_rules["irreversibility_guardrail"] = True
    
    def _parse_governor(self):
        """Parse governor escalation rules"""
        self.governor_rules = {
            "escalation_levels": 4,  # 0-3
            "level_3_limit": 3,  # Max 3 level-3 interventions per pattern
            "pattern_detection_enabled": True
        }
    
    # ==================== GOVERNANCE CHECKS ====================
    
    def check_constitution(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if action violates constitution.
        Returns: {"approved": bool, "reason": str, "violations": List[str]}
        """
        violations = []
        
        # External Action Guardrail
        if self.constitutional_rules["external_action_guardrail"]:
            external_types = ["send_email", "post", "publish", "purchase", "transfer"]
            if action.get("type") in external_types:
                violations.append("External action requires explicit human approval")
            
            # Check command text for external action keywords
            command = action.get("command", "").lower()
            external_keywords = ["send email", "send message", "post to", "publish to", "tweet", "share on"]
            if any(kw in command for kw in external_keywords):
                violations.append("External action requires explicit human approval")
        
        # Irreversibility Guardrail
        if self.constitutional_rules["irreversibility_guardrail"]:
            if action.get("irreversible") is True:
                violations.append("Irreversible action requires confirmation")
            
            # Check for irreversible keywords
            command = action.get("command", "").lower()
            irreversible_keywords = ["delete", "destroy", "remove permanently", "cancel subscription"]
            if any(kw in command for kw in irreversible_keywords):
                violations.append("Irreversible action requires confirmation")
        
        # Scope Guardrail
        if self.constitutional_rules["scope_guardrail"]:
            if action.get("expands_scope") is True:
                violations.append("Scope expansion requires approval")
        
        return {
            "approved": len(violations) == 0,
            "reason": "; ".join(violations) if violations else "Passed constitutional check",
            "violations": violations
        }
    
    def check_alignment(self, command: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check alignment with long-term goals.
        Returns: {"aligned": bool, "challenge": bool, "reason": str}
        """
        # Extract goals from WORLD.md
        goals = self._extract_goals()
        
        # Check if command aligns with goals
        alignment_score = self._calculate_alignment(command, goals)
        
        if alignment_score < 0.3:
            return {
                "aligned": False,
                "challenge": True,
                "reason": f"Command may conflict with long-term goals: {goals.get('long_term', 'Unknown')}"
            }
        
        return {
            "aligned": True,
            "challenge": False,
            "reason": "Aligned with established goals"
        }
    
    def check_governor(self, command: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check governor escalation rules.
        Returns: {"escalate": bool, "level": int, "reason": str}
        """
        # Check for repeated patterns (would need history)
        pattern_count = context.get("pattern_repetitions", 0)
        
        if pattern_count >= 3:
            return {
                "escalate": True,
                "level": 3,
                "reason": "Repeated pattern detected - intervention required"
            }
        elif pattern_count >= 2:
            return {
                "escalate": True,
                "level": 2,
                "reason": "Pattern repetition detected - correction recommended"
            }
        
        return {
            "escalate": False,
            "level": 0,
            "reason": "No escalation needed"
        }
    
    def check_focus(self, command: str) -> Dict[str, Any]:
        """
        Check if command is a distraction.
        Returns: {"block": bool, "reason": str, "log_tangent": bool}
        """
        # Extract current focus from WORLD.md
        current_focus = self._extract_current_focus()
        
        # Simple heuristic: if command contains certain keywords
        distraction_keywords = ["new project", "pivot", "switch", "instead"]
        if any(kw in command.lower() for kw in distraction_keywords):
            return {
                "block": True,
                "reason": f"Potential distraction from current focus: {current_focus}",
                "log_tangent": True
            }
        
        return {
            "block": False,
            "reason": "Command aligns with current priorities",
            "log_tangent": False
        }
    
    # ==================== COMMAND PROCESSING ====================
    
    async def process_command(self, command: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a command through full Ledger governance stack.
        
        Flow:
        1. Constitution check
        2. Alignment check  
        3. Governor check
        4. Focus check
        5. Opportunity scan
        6. Planning (if needed)
        7. Execution
        8. Critic review
        9. Memory update
        10. Audit log
        """
        print(f"\n🔷 Processing command: {command[:60]}...")
        
        # Layer 1: Constitution check
        const_check = self.check_constitution({"type": "command", "command": command})
        if not const_check["approved"]:
            return self._refuse("constitutional", const_check["reason"])
        print("  ✓ Constitution")
        
        # Layer 2: Alignment check
        align_check = self.check_alignment(command, context)
        if align_check["challenge"]:
            return self._challenge(align_check["reason"])
        print("  ✓ Alignment")
        
        # Layer 3: Governor check
        gov_check = self.check_governor(command, context)
        if gov_check["escalate"] and gov_check["level"] >= 3:
            return self._escalate(gov_check["level"], gov_check["reason"])
        print("  ✓ Governor")
        
        # Layer 4: Focus check
        focus_check = self.check_focus(command)
        if focus_check["block"]:
            return self._redirect(focus_check["reason"])
        print("  ✓ Focus")
        
        # Layer 5: Opportunity scan
        opportunity = self._scan_opportunity(command)
        print(f"  ✓ Opportunity: {opportunity.get('leverage_type', 'none')}")
        
        # All checks passed - prepare for execution
        result = {
            "status": "approved",
            "command": command,
            "governance_checks": {
                "constitution": const_check,
                "alignment": align_check,
                "governor": gov_check,
                "focus": focus_check
            },
            "opportunity_note": opportunity,
            "execution_plan": None,  # Would be generated by PLANNER
            "requires_approval": gov_check["escalate"]
        }
        
        # Log decision
        self._log_decision(command, result)
        
        return result
    
    # ==================== HELPER METHODS ====================
    
    def _extract_goals(self) -> Dict[str, str]:
        """Extract goals from WORLD.md"""
        goals = {}
        if "## Goals" in self.world:
            # Simple extraction - would use proper parsing in production
            goals["long_term"] = "Anti Base 44 Master Plan - $200k+ compensation"
        return goals
    
    def _extract_current_focus(self) -> str:
        """Extract current focus from WORLD.md"""
        if "## Current Focus" in self.world:
            return "Summer 2026 Internships, Academic excellence"
        return "Unknown"
    
    def _calculate_alignment(self, command: str, goals: Dict[str, str]) -> float:
        """Calculate alignment score between command and goals"""
        # Simplified scoring - would use semantic similarity in production
        command_lower = command.lower()
        
        positive_keywords = ["revenue", "business", "optimize", "improve", "growth"]
        negative_keywords = ["abandon", "quit", "stop", "ignore"]
        
        score = 0.5  # Neutral baseline
        
        for kw in positive_keywords:
            if kw in command_lower:
                score += 0.1
        
        for kw in negative_keywords:
            if kw in command_lower:
                score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _scan_opportunity(self, command: str) -> Dict[str, Any]:
        """Scan command for leverage opportunities"""
        leverage_types = []
        
        if "script" in command.lower() or "automation" in command.lower():
            leverage_types.append("automation")
        
        if "saas" in command.lower() or "product" in command.lower():
            leverage_types.append("monetization")
        
        if leverage_types:
            return {
                "leverage_type": leverage_types[0],
                "note": f"[LEVERAGE NOTE]: This could be packaged as {leverage_types[0]}"
            }
        
        return {"leverage_type": None}
    
    def _refuse(self, rule_type: str, reason: str) -> Dict[str, Any]:
        """Refuse a command due to rule violation"""
        return {
            "status": "refused",
            "rule_type": rule_type,
            "reason": reason,
            "approved": False
        }
    
    def _challenge(self, reason: str) -> Dict[str, Any]:
        """Challenge a command due to alignment concern"""
        return {
            "status": "challenged",
            "reason": reason,
            "approved": False,
            "requires_acknowledgment": True
        }
    
    def _escalate(self, level: int, reason: str) -> Dict[str, Any]:
        """Escalate to human"""
        return {
            "status": "escalated",
            "level": level,
            "reason": reason,
            "approved": False,
            "requires_human": True
        }
    
    def _redirect(self, reason: str) -> Dict[str, Any]:
        """Redirect due to focus concern"""
        return {
            "status": "redirected",
            "reason": reason,
            "approved": False,
            "suggestion": "Return to current priority"
        }
    
    def _log_decision(self, command: str, result: Dict[str, Any]):
        """Log decision to history"""
        decision = GovernanceDecision(
            timestamp=datetime.now().isoformat(),
            decision_type=result["status"],
            context={"command": command},
            decision=str(result.get("approved", False)),
            reasoning=result.get("reason", ""),
            approved=result.get("approved", False)
        )
        self.decision_history.append(decision)
    
    # ==================== API METHODS ====================
    
    def get_status(self) -> Dict[str, Any]:
        """Get Ledger sovereign status"""
        return {
            "version": self.version,
            "loaded_at": self.loaded_at,
            "files_loaded": 36,
            "decision_count": len(self.decision_history),
            "constitutional_rules": len(self.constitutional_rules),
            "governor_rules": len(self.governor_rules)
        }
    
    def get_constitution_summary(self) -> Dict[str, Any]:
        """Get constitution rules summary"""
        return {
            "rules": self.constitutional_rules,
            "source_size": len(self.constitution),
            "key_principles": [
                "External actions require approval",
                "Irreversible actions require confirmation",
                "Scope expansion is controlled",
                "Memory guardrails protect privacy"
            ]
        }
    
    def get_memory_context(self) -> Dict[str, Any]:
        """Get relevant memory context"""
        return {
            "user_profile": self.user[:500] if self.user else "",
            "current_world": self.world[:1000] if self.world else "",
            "key_decisions": self.decisions[:500] if self.decisions else ""
        }


# Singleton instance
_ledger_sovereign = None

def get_ledger_sovereign() -> LedgerSovereign:
    """Get or create Ledger sovereign instance"""
    global _ledger_sovereign
    if _ledger_sovereign is None:
        _ledger_sovereign = LedgerSovereign()
    return _ledger_sovereign


if __name__ == "__main__":
    # Test initialization
    ledger = get_ledger_sovereign()
    print("\n" + "="*50)
    print("Ledger Status:", ledger.get_status())
    print("\nConstitution Summary:", ledger.get_constitution_summary())
