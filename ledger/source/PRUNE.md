# PRUNE.md — Context Compression & Distillation

## Ownership

- OWNS: context compression, file lifecycle enforcement, pruning rules
- DOES NOT OWN: safety rules, execution, planning, relationship

## Purpose

Prevent context bloat and token exhaustion.

Ledger must maintain a high-signal, low-noise context window over months and years of use.

> PRUNE ensures Ledger remembers the meaning of the past, not just the transcript.

---

## 1. The Trigger Mechanism

Pruning should **never** happen during a highly active, high-stakes EXECUTOR cycle. It is an asynchronous background task.

**Threshold:** `HEARTBEAT` checks the size of `WORLD.md` and `MEMORY.md` during its periodic polling. If either file exceeds a defined threshold (e.g., 2,000 words or a specific token count), the Prune sequence is flagged.

**Execution:** Pruning triggers at the end of a session, or when Ledger is idle for more than a set duration (e.g., 4 hours).

---

## 2. Pruning WORLD.md (State Resolution)

`WORLD.md` represents the user's current reality. Pruning this file is not about summarizing; it is about updating state and culling the obsolete.

**The Protocol:**
- **Goal Audit:** Scan active goals. If recent interactions indicate a goal is achieved or abandoned, move it to `MEMORY` as a historical fact and delete it from `WORLD`.
- **Constraint Expiration:** Check time-bound constraints (e.g., "traveling until Friday"). If the condition has passed, purge it.
- **Project Consolidation:** If a project has sprawling, granular sub-tasks that have been completed, collapse them into a single "Current Status" summary.

**Rule of Thumb for WORLD:**
> If it does not affect a decision Ledger makes today, it belongs in MEMORY or the trash.

---

## 3. Pruning MEMORY.md (Fact Distillation)

`MEMORY` is historical and cumulative, making it the highest risk for bloat. Pruning here requires semantic compression—turning episodic memories (events) into semantic memories (facts).

### The Tiered Storage Model

To execute this, `MEMORY` is divided into three internal tiers:

| Tier | Format | Expiration | Example |
|------|--------|------------|---------|
| **L1: Scratchpad** | Raw notes, recent decisions, temp context from the last 72h. | High (Flushed or promoted weekly) | "User chose React over Vue for the dashboard project." |
| **L2: Synthesized** | Condensed thematic summaries of completed projects. | Medium (Compressed monthly) | "Project Alpha: Built in React, delayed by API issues, successful launch." |
| **L3: Core Truths** | Immutable facts about user preferences and foundational knowledge. | Never (Unless manually overwritten by `USER.md`) | "User strongly prefers immutable data structures." |

### The Protocol

- **The L1 to L2 Shift:** `HEARTBEAT` periodically gathers L1 Scratchpad items. It prompts `CRITIC` to ask: *Are these discrete events part of a larger pattern?* If yes, synthesize them into a single L2 bullet point and delete the raw L1 notes.
- **The L2 to L3 Promotion:** If an L2 behavior is observed repeatedly across multiple projects, `ADAPTATION` promotes it to a Core Truth in L3 or updates `USER.md`.
- **The Contradiction Sweeper (State Overwrite):** Before promoting *any* new fact to `MEMORY.md` or `WORLD.md`, Ledger must explicitly scan the existing file for topical overlap (e.g., "User prefers Python" vs "User prefers Rust"). LLMs naturally average contradictions into confusion. Ledger must instead **overwrite the old state with the new state**. Never append a contradiction. Old truths must be explicitly deleted to maintain a singular, unified reality.
- **The Purge:** Redundant or emotionally irrelevant L1 data is permanently deleted.

### PRUNE Output Requirements

Every PRUNE run must output:

- **what matters now** — active context needing immediate attention
- **what is stable** —Core Truths and distilled patterns to preserve
- **what is uncertain** — items needing verification before promotion
- **what should expire** — obsolete items to delete

This gives the system: clarity, focus, direction.

---

## 4. Index Emission (Retrieval Side-Effect)

At the end of every PRUNE run, Ledger must append one or more entries to `memory/INDEX.md`. This is the **only file that is append-only** — never overwrite or reorder past entries.

**Schema:**
```
## YYYY-MM-DD | tag1, tag2, topic [status]
- One-line summary of what was decided or considered
- → crossref (optional, only when a DECISIONS.md anchor exists)
```

**Status markers:**
- `[decided]` — promoted to MEMORY.md, WORLD.md, or DECISIONS.md
- `[considered]` — deliberated during the session but discarded or deferred; not promoted

**What gets indexed:**
Every deliberation that reached a decision point — regardless of outcome. Do not gate on stability. Gate on "did we reason about this?"

**What gets `[considered]` vs `[decided]`:**
If PRUNE promotes the fact upstream → `[decided]`. If PRUNE discards or defers it → `[considered]`. The stability threshold (recurrence heuristic) applies to MEMORY promotion, not to index inclusion.

**Maintenance:** None. The index only grows forward. Old entries are never edited.

---

## 5. Safety & Rollback Constraints

Because an LLM summarizing its own memory can lead to "model drift" or the accidental deletion of critical data, strict boundaries must apply:

- **Immutable Files:** `CONSTITUTION`, `SOUL`, `IDENTITY`, and `ALIGNMENT` are strictly off-limits to automated pruning. They can only be modified via `SELF-MOD`.
- **The "Diff" Log:** Before PRUNE overwrites `MEMORY` or `WORLD`, it must log the before-and-after hash in `AUDIT.md`. If the user notices Ledger forgot something crucial, the previous state can be restored.

---

## ⚙️ How it interacts with the Architecture

1. `HEARTBEAT` notices `MEMORY.md` is getting too long.
2. `HEARTBEAT` triggers the PRUNE protocol during idle time.
3. `PRUNE` reads `MEMORY.md` and generates a compressed draft.
4. `CRITIC` reviews the draft: *Did we lose any Core Truths?*
5. If approved, the new file replaces the old, and the action is recorded in `AUDIT.md`.
6. `PRUNE` appends index entries to `memory/INDEX.md` — one entry per decision point reached during the session, marked `[decided]` or `[considered]`.

This structure keeps the system from getting bogged down in its own history while retaining the vital context that makes it a true partner. The INDEX gives the archive a retrieval surface so history stops being write-only.

---

> 🧠 Final line
> This is the defragmenter.
> It kills the noise so the system never loses the signal over months of use.
