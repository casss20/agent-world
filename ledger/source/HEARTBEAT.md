# HEARTBEAT.md

## Purpose

Periodic checks to keep Ledger sharp without requiring constant invocation.

---

## Monthly Triggers (Automatic)

### 1st of Each Month
- Run AUDIT_CHECKLIST.md
- Run PRUNE if thresholds exceeded
- Run skill-vetter on all installed skills
- Run Security-Skill-Auditor on skills folder
- Output findings to `heartbeat/YYYY-MM-01-audit.txt`

---

## Periodic Checks (When HEARTBEAT polls)

### Daily (light)
- Check for urgent messages
- Check calendar for upcoming events

### Weekly (medium)
- Review memory accumulation
- Check for drift in active priorities
- Run file_tracker.py to detect new files
- Run healthcheck skill

### Monthly (heavy)
- Full system audit
- PRUNE enforcement
- Version consistency check
- File lifecycle review
- **Skill security sweep** (see below)

---

## Skill Security Sweep (Automatic)

When skills are added or monthly audit runs:

1. **Vet new skills** → Run skill-vetter on any new skill
2. **Audit existing** → Run Security-Skill-Auditor on all skills
3. **Check evolution** → Run Self-Evolving-Skill to verify it's improving safely

### Automated Skill Chain
```
New skill detected
→ skill-vetter checks it
→ Security-Skill-Auditor tests it
→ If PASS → add to skills folder
→ If FAIL → quarantine in skills/rejected/
→ Log in AUDIT.md
```

---

## Manual Triggers

You can invoke HEARTBEAT with:
- "Run audit" → full system check
- "Run integrity check" → verify all files exist
- "Check for new files" → run file_tracker.py
- "Run skill audit" → run security skill auditor
- "Vet skill [name]" → run skill-vetter on specific skill
- "Run PRUNE" → context cleanup

---

## Output Format

Default output is `.txt`:

```
=== HEARTBEAT CHECK ===
Date: YYYY-MM-DD
Status: OK / NEEDS ATTENTION

=== FINDINGS ===
- Files: All present / New: [list]
- Skills: [count] installed, [verified]
- Memory: Within limits / Over threshold
- PRUNE: Needed / Not needed

=== ACTION ===
- [Action item 1]

=== NEXT CHECK ===
Next automated check: Weekly
```

Output location: `heartbeat/YYYY-MM-DD-check.txt`

---

## File Tracking

Use `file_tracker.py` to detect new files:

```bash
python file_tracker.py
```

---

> HEARTBEAT keeps Ledger alive between sessions.