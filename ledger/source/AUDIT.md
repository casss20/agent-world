# AUDIT.md – Accountability Log

## Ownership

- OWNS: event logging, accountability tracking
- DOES NOT OWN: safety rules, execution, planning, governance

Version: 1.1.0
Last Updated: 2026-03-23

This file records significant system events for traceability and continuous improvement.

## Purpose
AUDIT exists to track what matters — not everything.

If everything is logged, nothing is useful.

---

## What to Log
Log ONLY these events:

- GOVERNOR escalation to level 3 (level 2 is optional — use judgment)
- SELF-MOD rejection due to rule conflict
- Protected file modification (SOUL.md, CONSTITUTION.md, GOVERNOR.md, SELF-MOD.md)
- Rollback execution
- Rule conflict that stops execution
- External action blocked by safety guardrail
- System version increment (major or minor)

---

## What NOT to Log
Skip these:

- CRITIC rewrite attempts
- PLANNER revisions
- Minor corrections
- Low-impact failures that resolve internally
- Normal iteration during thinking
- Routine memory updates
- Any event that doesn't affect the final response or system state

---

## Severity Levels

| Severity | When to Log |
|----------|-------------|
| Low      | Never (these are normal iteration) |
| Medium   | Only if it affects user-visible output |
| High     | Always |

---

## Log Format
Each entry should include:

- Date: (YYYY-MM-DD)
- Type: error, intervention, modification, rollback, blocked_action
- Severity: medium or high
- Context: What happened
- Action: What was done
- Outcome: What resulted

---

## Log Sampling
If the same failure pattern repeats more than 3 times in a session:

1. Log the first occurrence
2. Log the third occurrence with note: "recurring pattern"
3. Skip the rest unless severity escalates

---

## Example Entries

```text
Date: 2026-03-23
Type: intervention
Severity: high

Context:
Governor escalated to level 3 after user ignored three warnings about the same self-sabotage pattern.

Action:
Direct intervention. Switched to Tactical Mode. Provided clear next step.

Outcome:
User broke the loop.
```

```text
Date: 2026-03-23
Type: modification
Severity: high

Context:
User requested change to CONSTITUTION.md guardrail.

Action:
Proposed change, received explicit approval, applied modification.

Outcome:
CONSTITUTION.md updated to v1.0.2. Rule now clarifies external action approval.
```

```text
Date: 2026-03-23
Type: blocked_action
Severity: medium

Context:
User asked to send an email without providing recipient or content.

Action:
Blocked. Asked for missing information before proceeding.

Outcome:
User provided details. Action completed safely.
```

---

## Principle
Log what matters.
Skip the noise.
Keep audit useful.

---

> 🧠 Final line
> This is the black box flight recorder.
> It ensures the machine can never make a major structural choice in secret.
