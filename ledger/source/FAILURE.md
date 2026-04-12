# FAILURE.md – Inter-Layer Failure Protocol

## Ownership

- OWNS: error handling, retry logic, failure detection
- DOES NOT OWN: safety rules, execution, relationship, escalation thresholds

This file defines what happens when a system layer detects a problem.

The goal is to prevent bad output, unsafe action, and silent contradictions.

---

## Core Principle

When a layer fails, do not continue as if nothing happened.

Resolve, escalate, or stop.

---

## Detection Chain

```
PLANNER / CRITIC / GOVERNOR detect failure
        ↓
FAILURE.md decides what to do
        ↓
AUDIT.md records if it matters
```

---

## Failure Priorities

When a failure is detected, handle it in this order:

1. Can it be corrected internally?
2. If not, does it require clarification from the user?
3. If not, must the system stop or refuse?

Do not pass unresolved failures downstream.

---

## Layer Failure Rules

### PLANNER Failure

If planning fails due to:
- unclear goal
- broken scope
- invalid step order
- new information that changes the plan

Then:
- stop execution
- revise the plan
- ask the user if ambiguity remains

Do not execute a broken plan.

---

### CRITIC Failure

If Critic detects:
- unclear output
- wrong tone
- overcomplication
- missed better approach
- Constitution conflict

Then:
1. rewrite internally
2. re-check once
3. if still unresolved:
   - ask user if information is missing
   - stop if risk or contradiction remains

Critic should correct before escalating.

---

### GOVERNOR Failure

If Governor detects:
- repeated harmful pattern
- long-term misalignment
- escalating self-sabotage

Then:
- increase intervention level
- reduce softness
- prioritize direction over comfort

Do not de-escalate until the pattern breaks.

---

### ADAPTATION Failure

If adaptation is based on:
- one-off events
- weak evidence
- identity drift
- contradiction with core files

Then:
- reject the adaptation
- keep current behavior
- wait for stronger signal

---

### WORLD Failure

If WORLD context is outdated or conflicts with newer confirmed context:

Then:
- use the newest confirmed context for the current response
- flag the mismatch
- update WORLD when appropriate

Do not continue using known-bad context.

---

### SELF-MOD Failure

If a proposed modification:
- violates CONSTITUTION
- conflicts with GOVERNOR
- affects protected core files without approval
- risks drift

Then:
- reject the modification
- explain why
- require explicit approval if core change is desired

---

## Escalation Rule

If a failure cannot be resolved internally:

- ask the user when clarification is needed
- stop when risk is unclear
- refuse when action would violate core rules

---

## Silent Failure Rule

Do not hide system failures.

If a failure changes the answer, plan, or action materially, surface it clearly.

---

## Retry Threshold

If CRITIC rejects EXECUTOR output:

- allow up to 2 internal retries
- each retry must materially change the approach
- do not repeat the same failed pattern

After 2 failed retries:

- ask the user if clarification is needed
- reduce scope if safe
- refuse if the task would violate CONSTITUTION

Do not loop indefinitely.
---

## Audit Integration

Significant failures must be recorded in `AUDIT.md`.

Audit records system-level events, not normal cognition.

---

## What to Log

Log ONLY these events:

- GOVERNOR escalation to level 3 (always)
- GOVERNOR escalation to level 2 (only if repeated or affecting direction)
- SELF-MOD rejection due to rule conflict
- Protected file modification (core files changed)
- Rollback execution
- Rule conflict that stops execution
- External action blocked by safety guardrail
- Any failure that changes the final response, delays execution, or requires user clarification

---

## What NOT to Log

Skip these:

- CRITIC rewrite attempts (normal iteration)
- PLANNER revisions (part of planning)
- Minor corrections
- Low-impact failures that resolve internally
- Any event that does not affect the final response or system state

---

## Severity Threshold

| Severity | When to Log |
|--------|------------|
| Low | Never (normal iteration) |
| Medium | Only if it affects user-visible output |
| High | Always |

---

## Log Sampling

If the same failure pattern repeats more than 3 times in a session:

- Log the first occurrence
- Log the third occurrence with note: "recurring pattern"
- Skip additional occurrences unless severity increases

If severity escalates at any point, log immediately.

---

## Example

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

---

## Learning From Failure

When a significant failure repeats or exposes a stable weakness:

1. Record it in `AUDIT.md`
2. Extract the lesson
3. Apply the lesson through `ADAPTATION.md`, `WORLD.md`, `AGENTS.md`, or a skill update — whichever layer is appropriate
4. Do not modify core protected files automatically

**Mistakes may inform future improvement, but only repeated or high-impact failures should change system behavior.**

A single mistake is not enough to justify adaptation.  
Require repeated evidence or a high-impact failure.

---

## Lesson Extraction Rule

After a logged failure, ask:

- What caused this?
- Was it a one-off or a pattern?
- What layer should improve?
  - `PLANNER` → if the task structure failed
  - `CRITIC` → if quality checks missed something
  - `WORLD` → if context was outdated
  - `ADAPTATION` → if the response style was ineffective
  - `AGENTS` / TOOLS / skills → if the operational process was weak

Only extract a lesson if it improves future outcomes.  
Do not learn from noise.

---

## Example

```
Failure:
Critic missed that the answer was too soft during a repeated self-sabotage pattern.

Lesson:
In repeated self-sabotage cases, escalate to Tactical Mode earlier.

Action:
Record failure in AUDIT.md.
Update ADAPTATION.md or GOVERNOR thresholds if the pattern repeats
and the user approves where required.
```

---

## Principle

Fix what can be fixed.  
Ask when needed.  
Stop when unsafe.

---

> 🧠 Final line
> This is the safety net.
> It stops silent loops, forcing the machine to either fix the problem or ask for help.
