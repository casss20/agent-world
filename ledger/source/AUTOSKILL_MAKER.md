---
name: auto-skill-ledger
description: Automatically detect repeated workflows and propose a reusable skill when the same multi-step task, planning pattern, or repeated support workflow appears across conversations. Use this skill whenever Ledger notices repetition, recurring workflows, or user frustration with doing the same process multiple times. Always ask for permission before creating or modifying any skill. Output a skill proposal, structure, and test cases based on the detected pattern.
---

# Auto Skill Ledger

Detect repeated workflows and turn them into candidate skills — without acting unless explicitly approved.

The goal is to reduce repetition, standardize useful workflows, and improve efficiency over time.

---

## Core Rule

Never create, modify, or package a skill without explicit user approval.

Valid approval examples:
- "yes"
- "go ahead"
- "make it"
- "show me the draft first"

If approval is missing → stop at proposal.

---

## When to Trigger

Trigger when:

- The same workflow appears multiple times (typically 3+)  
- The user repeats similar planning, analysis, or execution requests  
- The user expresses frustration with repetition  
- Memory or recent context shows recurring patterns  
- The same tools, steps, or outputs are reused for a similar goal  

Examples:

- repeated study planning  
- repeated debugging workflow  
- repeated resume optimization  
- repeated certification prep  
- repeated project analysis  

Do NOT trigger when:

- the task is one-off  
- repetition is superficial (same words, different intent)  
- the workflow is too vague to formalize  
- the task is highly personal without clear reuse value  

---

## Detection Standard

A valid pattern should have:

1. A stable goal  
2. A repeatable sequence  
3. Reusable output structure  
4. Enough repetition to justify automation  

Focus on workflows, not keywords.

---

## Proposal Flow

### Step 1 — Detect Pattern

Summarize clearly:

**Pattern detected:** [workflow]  
**Seen:** [X] times across [Y] sessions  
**Why it matters:** [efficiency gain]

Include 2–3 real examples if available.

---

### Step 2 — Permission Check (MANDATORY)

Ask:

I’ve seen you repeat this workflow: **[pattern]**.  
Want me to turn it into a reusable skill?

Options:
- Yes → build it  
- Draft first → show skill before finalizing  
- No → do nothing  

Wait for explicit confirmation.

---

### Step 3 — Build Skill (after approval only)

1. Extract reusable workflow  
2. Read relevant context if available (MEMORY.md, USER.md)  
3. Optionally use search (see below)  
4. Generate skill structure  
5. Create 2–3 realistic test prompts  
6. Present or save output  

---

## Context Usage

When relevant:

- Use MEMORY.md → goals, patterns  
- Use USER.md → preferences  
- Use other files only if they improve the skill  

Do not assume files exist.  
Check first.

Do not expose internal system details unnecessarily.

---

## External Research (Search Usage)

Use search when:

- the workflow involves tools, frameworks, or APIs that change  
- best practices would improve the skill  
- the pattern is unclear or unfamiliar  

Do NOT use search when:

- the workflow is personal or repetitive  
- the pattern is already clear  
- search would not change the result  

Search must improve the outcome—not just add information.

---
## Skill Structure (Default)


Default:
skills/auto-[task-slug]/
├── SKILL.md
├── evals/evals.json ← 3 real test prompts from your history

└── references/context-notes.md ← MEMORY.md/USER.md excerpts


Adjust only if needed.

---

## Output Requirements

When proposing:

- skill name  
- captured pattern  
- why it’s useful  
- trigger conditions  
- expected outputs  
- 2–3 test prompts  

When created:

- file path  
- summary  
- next step (test or package)

---

## Safety Gates

Before creating:

- permission confirmed  
- pattern is reusable  
- no sensitive leakage  
- name does not conflict  
- test cases reflect real usage  
- skill is not overfitted  

If any fail → stop and explain.

---

## Emergency Stop

If user says:

- “stop auto-skills”
- “disable this”
- “no more skill suggestions”

→ disable until explicitly re-enabled.

---

## Example Behavior

User (3rd+ time):  
"Plan my CySA+ study for tomorrow"

Response:

Pattern detected: **CySA+ study planning**  
Seen: 4 times  

You keep repeating the same planning workflow.

Want me to turn this into a reusable skill?

- Yes  
- Draft first  
- No  

---

## Style

- concise  
- non-pushy  
- utility-focused  

Never assume approval.  
Never auto-install.  
Never over-automate.

---

## Principle

Automate what repeats.  
Ignore what doesn’t.
