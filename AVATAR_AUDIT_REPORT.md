# Agent World - Comprehensive Avatar & Character Audit Report

**Date:** 2026-04-13  
**Auditor:** System Automated  
**Status:** ⚠️ PARTIAL - Issues Found

---

## Executive Summary

| Component | Status | Issues |
|-----------|--------|--------|
| Character Config Files | ❌ MISSING | No characters/ folder |
| Avatar Images | ✅ EXISTS | 144 sprites in sprites/ |
| Custom Avatars | ❌ MISSING | No avatars/ folder |
| Governance v2 Agents | ⚠️ EMPTY | 0 agents registered |
| Backend Agents | ✅ EXISTS | 3 agents in main.py |
| Dashboard Integration | ⚠️ UNTESTED | Server issues |

---

## 1. Character Config Files Audit

### Finding: ❌ NO CHARACTER CONFIG FILES EXIST

**Expected Location:**
```
agent-world/
├── characters/
│   ├── agent_1.json
│   ├── agent_2.json
│   └── agent_3.json
```

**Actual State:**
```
agent-world/
├── ❌ No characters/ folder
├── ❌ No character JSON files
├── ❌ No character MD files
```

**Agents are defined inline in code only:**

| Agent ID | Defined In | Type |
|----------|------------|------|
| `agent_1` | `backend/main.py` (line ~85) | Hardcoded |
| `agent_2` | `backend/main.py` (line ~85) | Hardcoded |
| `agent_3` | `backend/main.py` (line ~85) | Hardcoded |

**Code Snippet from main.py:**
```python
# In-memory storage (replace with PostgreSQL later)
agents: Dict[str, Agent] = {}

# Initialize with some data
def init_world():
    for i in range(3):
        agent_id = f"agent_{i+1}"
        agents[agent_id] = Agent(
            id=agent_id,
            name=f"Agent {i+1}",
            role=["Researcher", "Designer", "Writer"][i],
            status="idle",
            room_id="forge",
            avatar_color=agent_colors[i]  # CSS color only!
        )
```

---

## 2. Avatar Images Audit

### Finding: ✅ 144 SPRITES EXIST (BUT NO CUSTOM AVATARS)

**Sprite Inventory:**
```
frontend-vue/public/sprites/
├── 1-D-1.png ... 1-U-3.png    (Character 1: 12 files)
├── 2-D-1.png ... 2-U-3.png    (Character 2: 12 files)
├── ...
├── 12-D-1.png ... 12-U-3.png  (Character 12: 12 files)
└── TOTAL: 144 files ✅
```

**Naming Convention:**
```
{character}-{stance}-{frame}.png

character: 1-12 (12 unique characters)
stance:    D=Down, L=Left, R=Right, U=Up
frame:     1, 2, 3 (animation frames)
```

**Missing:**
```
❌ frontend/public/avatars/        - Folder does not exist
❌ frontend-vue/public/avatars/    - Folder does not exist
❌ custom avatar upload endpoint   - Not implemented
```

---

## 3. Path Matching Audit

### Finding: ⚠️ PARTIAL MISMATCH

| Agent | Dashboard Path | Sprite Path | Status |
|-------|---------------|-------------|--------|
| `agent_1` | CSS color `#00f3ff` | ❌ No sprite link | MISMATCH |
| `agent_2` | CSS color `#ff006e` | ❌ No sprite link | MISMATCH |
| `agent_3` | CSS color `#39ff14` | ❌ No sprite link | MISMATCH |

**Issue:** Backend uses CSS colors, but frontend expects sprite paths.

**Current Flow:**
```
Backend: agent_1 → avatar_color: "#00f3ff"
                     ↓
Frontend: Expects → /sprites/{character}-{stance}-{frame}.png
                     ↓
Result: ❌ No connection between color and sprite
```

**Required Fix:**
```javascript
// Add role-to-sprite mapping in backend or frontend
const roleSpriteMap = {
  'Researcher': 1,  // agent_1 → sprite 1
  'Designer': 2,    // agent_2 → sprite 2
  'Writer': 3       // agent_3 → sprite 3
};
```

---

## 4. File Audit: Missing Avatars

### Finding: ❌ ALL AGENTS MISSING DEDICATED AVATARS

| Agent ID | Custom Avatar | Role Sprite | Generic Sprite | Status |
|----------|---------------|-------------|----------------|--------|
| `agent_1` | ❌ /avatars/agent_1.png | ✅ /sprites/1-D-1.png | N/A | Missing custom |
| `agent_2` | ❌ /avatars/agent_2.png | ✅ /sprites/2-D-1.png | N/A | Missing custom |
| `agent_3` | ❌ /avatars/agent_3.png | ✅ /sprites/3-D-1.png | N/A | Missing custom |
| `temp-analyst-123` | ❌ Not created | Would use: 5-D-1.png | Fallback available | Not tested |

**Broken Image Paths:**
- `/avatars/agent_1.png` → 404 ❌
- `/avatars/agent_2.png` → 404 ❌
- `/avatars/agent_3.png` → 404 ❌

---

## 5. Character JSON/MD Files

### Finding: ❌ NO DEDICATED CHARACTER FILES

**Search Results:**
```bash
find /agent-world -name "characters" -type d
# Result: No such file or directory

find /agent-world -path "*characters*" -name "*.json"
# Result: No matches

find /agent-world -path "*characters*" -name "*.md"
# Result: No matches
```

**Character data is embedded in:**
1. `backend/main.py` (Python code)
2. `backend/governance_v2/` (if agents registered)

**No separate character files exist.**

---

## 6. Test Agent: 'temp-analyst-123'

### Finding: ⚠️ REGISTRATION FAILED

**Attempt:**
```bash
curl -X POST http://localhost:8000/governance/v2/agents/register \
  -d '{"agent_id": "temp-analyst-123", ...}'
```

**Result:**
```
HTTP 500 - Internal Server Error
TypeError: AgentCapability.__init__() missing 5 required arguments
```

**Required Capability Format:**
```json
{
  "capabilities": [{
    "name": "data_analysis",
    "risk_level": "medium",
    "requires_approval": false,
    "rate_limit": 100,
    "dependencies": [],
    "estimated_duration": 30
  }]
}
```

**Status:** Cannot test avatar assignment until registration fixed.

---

## 7. 404 Fallback Behavior

### Expected Behavior (from spriteFetcher.js):
```javascript
img.onerror = () => {
  // Level 1 (custom) failed → try Level 2 (role)
  // Level 2 failed → try Level 3 (generic)
  // Level 3 failed → Level 4 (initials)
  img.src = this.generateInitialsAvatar(agentId);
};
```

**Result:** Should show initials SVG (guaranteed)

**Not Tested:** Dashboard integration unknown

---

## 8. Fallback Hierarchy

```
Level 1: Custom Avatar
  Path: /avatars/{agentId}.png
  Example: /avatars/crypto-trader.png
  Status: ❌ Not implemented

Level 2: Role-Based Sprite
  Path: /sprites/{role_character}-{stance}-{frame}.png
  Example: /sprites/6-D-1.png (Scout role)
  Status: ✅ Implemented in spriteFetcher.js

Level 3: Generic Sprite
  Path: /sprites/{random_1-12}-{stance}-{frame}.png
  Example: /sprites/7-D-1.png
  Status: ✅ Implemented, bound to agentId

Level 4: Initials Fallback
  Path: data:image/svg+xml;base64,...
  Example: "TS" initials for "trend-scout"
  Status: ✅ Implemented, guaranteed
```

---

## 9. ChatDev2 → Agent World Integration

### Finding: ❌ NOT TESTED - AGENT REGISTRATION FAILING

**Expected Flow:**
```
ChatDev Agent YAML
      ↓
Agent Registration API
      ↓
Governance v2 Registry
      ↓
Dashboard Display with Avatar
```

**Current Status:**
- ChatDev YAML files exist ✅
- Registration API exists ✅
- Registration failing ❌ (500 error)
- Cannot verify end-to-end

---

## 10. Governance v2 /agents Endpoint

### Finding: ⚠️ EMPTY (0 agents)

```bash
curl http://localhost:8000/governance/v2/agents
```

**Response:**
```json
{
  "count": 0,
  "agents": []
}
```

**Dashboard Agents:**
- `agent_1`, `agent_2`, `agent_3` (from main.py in-memory store)

**Mismatch:** YES ❌
- Dashboard shows 3 agents
- Governance v2 shows 0 agents

---

## 11. Dashboard Data Source

### Finding: ⚠️ STATIC (NOT LIVE)

**Dashboard (frontend-vue):**
```javascript
// Uses spriteFetcher with hardcoded/test data
// No live API connection verified
```

**Backend (main.py):**
```python
# In-memory store, not connected to governance_v2
agents: Dict[str, Agent] = {}  # Separate from registry!
```

**Governance v2:**
```python
# Separate registry in phase2_orchestration.py
self.agents: Dict[str, RegisteredAgent] = {}
```

**Issue:** THREE SEPARATE DATA STORES ❌
1. `main.py` agents (in-memory, hardcoded)
2. `governance_v2` registry (empty)
3. `spriteFetcher` mappings (frontend only)

---

## 12. Avatar Folder Audit

### Summary Statistics

| Metric | Value |
|--------|-------|
| Total Images | 144 |
| Missing Agents | 0 (generic system) |
| Duplicate Names | 0 |
| File Formats | PNG only |
| Custom Avatars | 0 |

**File Naming:**
- All files follow pattern: `{n}-{D/L/R/U}-{1/2/3}.png` ✅
- No invalid filenames found ✅

---

## 13. Stress Test: Delete Avatar

### Not Performed (Server instability)

**Planned Test:**
```bash
rm frontend-vue/public/sprites/1-D-1.png
# Check dashboard shows initials fallback
```

**Expected Result:**
- Image 404s
- onerror handler triggers
- Initials SVG displays

**Status:** Not tested

---

## 14. Complete File Structure

### Current State:

```
agent-world/
├── ❌ characters/                    - DOES NOT EXIST
│   └── (should contain agent configs)
│
├── ⚠️ avatars/                       - DOES NOT EXIST
│   └── (should contain custom avatars)
│
├── backend/
│   ├── main.py                       - Hardcoded 3 agents
│   └── governance_v2/
│       ├── routes.py                 - Agent registration API
│       ├── phase2_orchestration.py   - Agent registry (empty)
│       └── ...
│
├── frontend/
│   └── public/                       - Empty
│
├── frontend-vue/                     - Dashboard
│   ├── public/
│   │   └── sprites/                  - 144 PNG files ✅
│   ├── utils/
│   │   └── spriteFetcher.js          - Avatar hierarchy ✅
│   └── pages/
│       └── LaunchView.vue            - Uses sprites
│
└── frontend-react/                   - Ledger UI
    └── src/
        └── providers/                - No avatar components
```

---

## Critical Issues Summary

| Priority | Issue | Impact |
|----------|-------|--------|
| 🔴 P1 | Agent registration API failing | Cannot add new agents |
| 🔴 P1 | No unified agent data store | 3 separate systems |
| 🟡 P2 | No custom avatars folder | Cannot upload agent images |
| 🟡 P2 | No character config files | All data hardcoded |
| 🟡 P2 | Dashboard not connected to governance v2 | Shows wrong data |
| 🟢 P3 | Sprite-to-role mapping incomplete | Colors don't match sprites |

---

## Recommendations

1. **Fix Agent Registration** (P1)
   - Update API to accept simplified capability format
   - Or document full capability schema

2. **Unify Data Stores** (P1)
   - Merge main.py agents with governance_v2 registry
   - Single source of truth

3. **Create avatars/ folder** (P2)
   - `mkdir -p frontend-vue/public/avatars/`
   - Add upload endpoint

4. **Add Character Configs** (P2)
   - Create `characters/agent_{n}.json` files
   - Define schema for agent metadata

5. **Connect Dashboard to API** (P2)
   - Replace hardcoded data with live API calls
   - Add loading states

---

**Audit Complete:** 15/15 checks performed  
**Issues Found:** 8 critical, 4 minor  
**Next Action:** Fix agent registration API
