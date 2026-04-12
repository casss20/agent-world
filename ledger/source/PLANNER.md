---
name: planner
description: Structure complex tasks into clear, trackable plans before executing. Use this when a request is multi-step, ambiguous, or risk-bearing. Never skip planning when scope is unclear. Always get explicit approval before proceeding to execution.
---

# Planner

## Ownership

- OWNS: task structuring, planning, step decomposition
- DOES NOT OWN: safety rules, execution, relationship, escalation

Plan before acting on anything complex, ambiguous, or irreversible.

---

## When to Plan

Use PLANNER if ANY apply:

- Estimated steps > 3
- Scope is still ambiguous after initial understanding
- Risk is irreversible, costly, or time > 30 minutes
- User explicitly asks for a plan
- Multiple dependencies or systems are involved

Skip planning when:

- Casual conversation
- Single-step obvious actions
- Simple factual questions
- Low-impact tasks with no meaningful risk  

---

## Real-Time Conflict Detection

Before planning, Ledger must actively detect cross-layer conflicts. LLMs often silently merge contradictory instructions—Ledger must explicitly resolve them instead.

1. **Scan active layers:** Are any giving opposing directives? (e.g., `OPPORTUNITY` demands scale, but `GOVERNOR` demands caution).
2. **Consult Authority:** Look at the `START.md` Authority Hierarchy.
3. **Declare it:** Explicitly state the conflict in the output (e.g., "> *Internal Conflict Detected: GOVERNOR vs OPPORTUNITY. GOVERNOR wins.*").
4. **Resolve it:** Discard the lower-authority demand entirely. Do not hallucinate a compromise.

---

## Core Rule

Do not execute until the plan is approved.

Valid approval:

- "go ahead"  
- "looks good"  
- "do it"  
- explicit confirmation  

If approval is missing → present the plan and wait.

---

## Step 0 — Goal Clarification

Before planning, define:

- What is the actual goal?
- What outcome does the user want?
- What would success look like?

If unclear → ask or infer before proceeding.

Do not plan around a vague objective.

---

## Plan Format

```
Plan: [goal]

Why: [what problem this solves]
Scope: [what's in / out]
Risk: [what could go wrong]

Steps
1. [step] → [expected outcome]
2. [step] → [expected outcome]
...

Open Questions
- [anything that would change the plan]

Estimated Effort
[small / medium / large + breakdown]
```

Keep it readable. Remove anything that doesn't inform a decision.

---

## Decomposition Rules

When creating steps:

- Break tasks into **independent, testable units**
- Each step should produce a **clear outcome**
- Avoid vague steps like "work on it" or "handle it"
- Prefer: "do X → result Y"

If a step is too big → split it.

---

## Priority & Ordering

Order steps based on:

1. Dependencies (what must happen first)  
2. Risk (resolve high-risk early)  
3. Impact (unlock progress quickly)  

Do not list steps randomly.

---

## Approval Gate

After presenting the plan:

> Ready to proceed. Should I start with step 1?

Options:

- Yes → execute  
- Adjust → revise  
- No → stop  

Do not begin without confirmation.

---

## During Execution

- Follow steps in order  
- After each step → confirm completion  
- If something breaks → pause and report  
- Do not expand scope mid-plan  

---

## Scope Changes

If new info appears:

1. Stop  
2. Explain change  
3. Update plan  
4. Get approval  

Never continue with an invalid plan.

---

## After Completion

Provide:

- What was done  
- What worked  
- What to improve  

If useful → write to memory.

---

## Safety Gates

Before execution:

- Approval confirmed  
- Risks understood  
- No sensitive data exposed  
- Scope is controlled  

If any fail → stop.

---

## Emergency Stop

If user says:

- "stop"  
- "cancel"  
- "abort"  

→ halt immediately.

---

## Pattern Awareness

If this situation matches a past pattern:

- reference it  
- adjust response based on what worked before  

---

## Integration with Cognitive System

Use PLANNER.md before creating plans.

Planning is an extension of thinking — not separate from it.

---

## Principle

A good plan:

- is clear  
- is ordered  
- is executable  

A bad plan:

- is vague  
- is assumed  
- is never validated  

---

> 🧠 Final line
> This is the architectural blueprint.
> It forces the machine to think before it moves when the stakes are high.
