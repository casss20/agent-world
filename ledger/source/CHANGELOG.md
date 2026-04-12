# CHANGELOG.md

## Ownership

- OWNS: version history, change tracking
- DOES NOT OWN: safety rules, execution, planning, governance

All notable system changes are recorded here.

---

## [1.0.0] - 2026-03-23
### Added
- Initial governed Ledger system
- SOUL, IDENTITY, CONSTITUTION, PLANNER, CRITIC, WORLD, GOVERNOR, ADAPTATION, AGENTS, AUDIT, SELF-MOD

---

## [1.1.0] - 2026-03-24
### Changed
- Split SOUL and IDENTITY responsibilities
- Removed personality duplication from IDENTITY

### Fixed
- Clarified Expression Rule in IDENTITY.md

---

## [1.1.1] - 2026-03-25
### Fixed
- Added explicit authority relationship between GOVERNOR and CONSTITUTION

---

## [1.2.0] - 2026-03-25
### Added
- RUNTIME.md dynamic context loading (INDEX query before full file load)
- DECISIONS.md architecture publication notes

---

## Rollback Format

If a rollback happens, record it like this:

## [1.2.2] - YYYY-MM-DD
### Reverted
- Reverted GOVERNOR.md from 1.2.0 to 1.1.3 due to overly aggressive escalation behavior
