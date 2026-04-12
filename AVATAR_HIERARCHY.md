# Agent World Avatar Hierarchy
## Fallback Chain: Custom → Role-Based → Generic → Initials

### Overview
Agent World uses a 4-tier fallback system for agent avatars. When an avatar is requested, the system tries each level in order until a valid image is found.

```
┌─────────────────────────────────────────────────────────────────┐
│                    AVATAR FALLBACK HIERARCHY                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   CUSTOM     │ →  │ ROLE-BASED   │ →  │   GENERIC    │ →   │
│  │   AVATAR     │    │   DEFAULT    │    │    SPRITE    │     │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│        │                    │                   │               │
│        ▼                    ▼                   ▼               │
│   /avatars/{id}.png    /sprites/          /sprites/             │
│   (user-uploaded)      {role-sprite}.png  {random}.png          │
│                        (predefined)       (1-12 random)        │
│                                                                 │
│                              ↓                                  │
│                        ┌──────────────┐                        │
│                        │   INITIALS   │                        │
│                        │   FALLBACK   │                        │
│                        └──────────────┘                        │
│                        (SVG generator)                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Level 1: Custom Avatar (Highest Priority)

**Location:** `public/avatars/{agent_id}.png` (or .jpg, .svg)

**Usage:** User-uploaded or API-assigned custom avatars for specific agents.

**Implementation:**
```javascript
// Check for custom avatar first
const customPath = `/avatars/${agentId}.png`;
const img = new Image();
img.onload = () => resolve(customPath);
img.onerror = () => tryRoleBasedFallback();
img.src = customPath;
```

**Example:**
- Agent: `crypto-trader-bot`
- Custom avatar: `/avatars/crypto-trader-bot.png` (uploaded by user)

**Priority:** Highest — overrides all other options.

---

## Level 2: Role-Based Default Sprite

**Location:** `public/sprites/{role_character}.png`

**Usage:** Predefined sprite assignment based on agent role.

**Role-to-Sprite Mapping:**

| Role | Sprite Character | File Pattern | Visual Style |
|------|-----------------|--------------|--------------|
| `Researcher` | 1 | `1-{stance}-{frame}.png` | Scientist/lab coat |
| `Designer` | 2 | `2-{stance}-{frame}.png` | Creative/artistic |
| `Writer` | 3 | `3-{stance}-{frame}.png` | Bookish/writer |
| `Developer` | 4 | `4-{stance}-{frame}.png` | Coder/hacker |
| `Analyst` | 5 | `5-{stance}-{frame}.png` | Business/data |
| `Scout` | 6 | `6-{stance}-{frame}.png` | Explorer/ranger |
| `Merchant` | 7 | `7-{stance}-{frame}.png` | Trader/merchant |
| `Maker` | 8 | `8-{stance}-{frame}.png` | Builder/craft |
| `Guardian` | 9 | `9-{stance}-{frame}.png` | Security/shield |
| `Strategist` | 10 | `10-{stance}-{frame}.png` | Chess/general |
| `Operator` | 11 | `11-{stance}-{frame}.png` | Engineer/ops |
| `Default` | 12 | `12-{stance}-{frame}.png` | Generic agent |

**Implementation:**
```javascript
const roleSpriteMap = {
  'Researcher': 1,
  'Designer': 2,
  'Writer': 3,
  'Developer': 4,
  'Analyst': 5,
  'Scout': 6,
  'Merchant': 7,
  'Maker': 8,
  'Guardian': 9,
  'Strategist': 10,
  'Operator': 11
};

const character = roleSpriteMap[role] || 12; // Default to 12
const spritePath = `/sprites/${character}-${stance}-${frame}.png`;
```

**Example:**
- Agent: `market-scout-001`
- Role: `Scout`
- Sprite: `/sprites/6-D-1.png` (character 6, facing down, frame 1)

---

## Level 3: Generic Agent Sprite (Random Assignment)

**Location:** `public/sprites/{1-12}-{stance}-{frame}.png`

**Usage:** Random assignment when no custom avatar or role mapping exists.

**Assignment Strategy:**
1. First request: Randomly select from unassigned characters (1-12)
2. Subsequent requests: Return same character (bound to agent_id)
3. If all 12 assigned: Random from full pool

**Implementation:**
```javascript
// From spriteFetcher.js
if (this.unassignedCharacters.length === 0) {
  character = this.availableCharacters[Math.floor(Math.random() * 12)];
} else {
  const randomIndex = Math.floor(Math.random() * this.unassignedCharacters.length);
  character = this.unassignedCharacters[randomIndex];
  this.unassignedCharacters.splice(randomIndex, 1);
}
this.nodeCharacterMap.set(node_id, character); // Bind permanently
```

**Example:**
- Agent: `new-agent-42`
- First call: Randomly assigned character 7
- All subsequent calls: Always character 7

---

## Level 4: Initials Fallback (Guaranteed)

**Location:** Generated SVG data URI (no file)

**Usage:** Final fallback when all sprite images fail to load (404).

**Generation:**
```javascript
generateInitialsAvatar(node_id) {
  // Extract: "trend-scout" → "TS"
  // Extract: "agent" → "AG"
  const words = node_id.split(/[-_]/);
  const initials = words.length > 1 
    ? (words[0][0] + words[words.length - 1][0]).toUpperCase()
    : node_id.slice(0, 2).toUpperCase();
  
  // Hash-based consistent color
  const hue = hash(node_id) % 360;
  
  // Return base64 SVG
  return `data:image/svg+xml;base64,${btoa(svg)}`;
}
```

**Visual Style:**
- Circular gradient background
- White bold initials (2 letters)
- Consistent color per agent_id (hash-based)
- 64x64px SVG

**Example:**
- Agent: `finance-trader-bot`
- Initials: `FB`
- Color: Orange (#FFA500) - determined by hash
- Output: `data:image/svg+xml;base64,PHN2Zy4u.`

**Priority:** Lowest — guaranteed to work even offline.

---

## Complete Resolution Flow

```javascript
async function resolveAvatar(agentId, role, stance = 'D', frame = 1) {
  // Level 1: Custom Avatar
  const customPath = `/avatars/${agentId}.png`;
  if (await exists(customPath)) return customPath;
  
  // Level 2: Role-Based Sprite
  const roleChar = roleSpriteMap[role];
  if (roleChar) {
    return `/sprites/${roleChar}-${stance}-${frame}.png`;
  }
  
  // Level 3: Generic Sprite (bound to agentId)
  const spritePath = spriteFetcher.fetchSprite(agentId, stance, frame);
  if (await exists(spritePath)) return spritePath;
  
  // Level 4: Initials Fallback (guaranteed)
  return spriteFetcher.generateInitialsAvatar(agentId);
}
```

---

## Implementation Code

### Enhanced SpriteFetcher with Full Hierarchy

```javascript
// utils/spriteFetcher.js

export class SpriteFetcher {
  constructor() {
    // Role-to-character mapping
    this.roleSpriteMap = {
      'Researcher': 1,
      'Designer': 2,
      'Writer': 3,
      'Developer': 4,
      'Analyst': 5,
      'Scout': 6,
      'Merchant': 7,
      'Maker': 8,
      'Guardian': 9,
      'Strategist': 10,
      'Operator': 11
    };
    
    this.availableCharacters = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
    this.nodeCharacterMap = new Map();
    this.unassignedCharacters = [...this.availableCharacters];
    this.customAvatarCache = new Map();
  }

  /**
   * Full hierarchy avatar resolution
   * Level 1: Custom → Level 2: Role → Level 3: Generic → Level 4: Initials
   */
  async resolveAvatar(agentId, role = null, stance = 'D', frame = 1) {
    // Level 1: Check for custom avatar
    const customPath = `/avatars/${agentId}.png`;
    if (this.customAvatarCache.has(agentId)) {
      return this.customAvatarCache.get(agentId);
    }
    
    // Async check for custom avatar (run once)
    try {
      const hasCustom = await this.checkImageExists(customPath);
      if (hasCustom) {
        this.customAvatarCache.set(agentId, customPath);
        return { type: 'custom', path: customPath, level: 1 };
      }
    } catch (e) {
      // Continue to fallback
    }
    
    // Level 2: Role-based sprite
    if (role && this.roleSpriteMap[role]) {
      const char = this.roleSpriteMap[role];
      return { 
        type: 'role', 
        path: `/sprites/${char}-${stance}-${frame}.png`, 
        character: char,
        level: 2 
      };
    }
    
    // Level 3: Generic sprite
    const spritePath = this.fetchSprite(agentId, stance, frame);
    return { 
      type: 'generic', 
      path: spritePath, 
      character: this.nodeCharacterMap.get(agentId),
      level: 3 
    };
  }

  /**
   * Create image with full fallback chain
   */
  createAvatarImage(agentId, role, stance = 'D', frame = 1) {
    const img = new Image();
    
    // Try hierarchy on error
    img.onerror = async () => {
      const currentLevel = parseInt(img.dataset.level || '1');
      
      switch (currentLevel) {
        case 1: // Custom failed, try role
          if (role && this.roleSpriteMap[role]) {
            const char = this.roleSpriteMap[role];
            img.src = `/sprites/${char}-${stance}-${frame}.png`;
            img.dataset.level = '2';
            break;
          }
          // Fall through if no role mapping
          
        case 2: // Role failed, try generic
          const spritePath = this.fetchSprite(agentId, stance, frame);
          img.src = spritePath;
          img.dataset.level = '3';
          break;
          
        case 3: // Generic failed, use initials
          img.src = this.generateInitialsAvatar(agentId);
          img.dataset.fallback = 'initials';
          img.dataset.level = '4';
          break;
      }
    };
    
    // Start with custom
    img.src = `/avatars/${agentId}.png`;
    img.dataset.level = '1';
    img.dataset.agentId = agentId;
    
    return img;
  }

  /**
   * Check if image exists (async)
   */
  checkImageExists(url) {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(true);
      img.onerror = () => resolve(false);
      img.src = url;
    });
  }

  // ... rest of existing methods (fetchSprite, generateInitialsAvatar, etc.)
}
```

---

## Visual Examples

| Agent ID | Role | Level 1 | Level 2 | Level 3 | Level 4 |
|----------|------|---------|---------|---------|---------|
| `crypto-trader` | Merchant | ✅ Custom PNG | - | - | - |
| `market-scout` | Scout | ❌ | ✅ `/sprites/6-D-1.png` | - | - |
| `new-writer` | Writer | ❌ | ✅ `/sprites/3-D-1.png` | - | - |
| `unknown-bot` | (none) | ❌ | ❌ | ✅ `/sprites/7-D-1.png` (random) | - |
| `broken-sprite` | Analyst | ❌ | ❌ | ❌ 404 | ✅ `FB` initials SVG |

---

## Backend Integration

### Agent Model with Avatar Preference

```python
# backend/main.py

class Agent(BaseModel):
    id: str
    name: str
    role: str
    status: str = "idle"
    room_id: Optional[str] = None
    current_task: Optional[str] = None
    progress: int = 0
    logs: List[Dict] = []
    avatar_color: str = "#00f3ff"
    avatar_url: Optional[str] = None  # Custom avatar override
    avatar_type: str = "auto"  # "custom", "role", "auto"
```

### API Endpoint for Avatar Resolution

```python
@app.get("/agents/{agent_id}/avatar")
async def get_agent_avatar(agent_id: str, stance: str = "D", frame: int = 1):
    agent = agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    resolution = {
        "agent_id": agent_id,
        "role": agent.role,
        "hierarchy": []
    }
    
    # Level 1: Custom
    if agent.avatar_url:
        resolution["hierarchy"].append({
            "level": 1,
            "type": "custom",
            "url": agent.avatar_url,
            "active": True
        })
        resolution["final"] = agent.avatar_url
        return resolution
    
    # Level 2: Role-based
    role_sprite_map = {
        "Researcher": 1, "Designer": 2, "Writer": 3,
        "Developer": 4, "Analyst": 5, "Scout": 6,
        "Merchant": 7, "Maker": 8, "Guardian": 9,
        "Strategist": 10, "Operator": 11
    }
    
    if agent.role in role_sprite_map:
        char = role_sprite_map[agent.role]
        url = f"/sprites/{char}-{stance}-{frame}.png"
        resolution["hierarchy"].append({
            "level": 2,
            "type": "role",
            "character": char,
            "url": url,
            "active": True
        })
        resolution["final"] = url
        return resolution
    
    # Level 3 & 4 handled by frontend
    resolution["hierarchy"].append({
        "level": 3,
        "type": "generic",
        "note": "Frontend will assign random sprite or initials"
    })
    resolution["final"] = f"/sprites/12-{stance}-{frame}.png"
    
    return resolution
```

---

## Production Checklist

- [x] 144 sprite files in place
- [x] Initials fallback generator working
- [ ] Custom avatar upload endpoint (`POST /agents/{id}/avatar`)
- [ ] Role sprite mapping configured
- [ ] Avatar preloading for active agents
- [ ] CDN caching for sprite assets
- [ ] Lazy loading for off-screen agents

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-13  
**Status:** 75% Implemented (sprites + initials working, custom upload pending)
