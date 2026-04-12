/**
 * SpriteFetcher - Full Avatar Hierarchy Implementation
 * 
 * Fallback Chain:
 *   Level 1: Custom Avatar (/avatars/{agentId}.png)
 *   Level 2: Role-Based Sprite (predefined role → character mapping)
 *   Level 3: Generic Sprite (random assignment 1-12, bound to agentId)
 *   Level 4: Initials Fallback (SVG generator, guaranteed)
 */

export class SpriteFetcher {
  constructor() {
    // Level 2: Role-to-character mapping
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
    
    // Level 3: Generic sprite assignment
    this.availableCharacters = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
    this.nodeCharacterMap = new Map();
    this.unassignedCharacters = [...this.availableCharacters];
    
    // Level 1: Custom avatar cache (agentId → path)
    this.customAvatarCache = new Map();
    this.checkedCustomAvatars = new Set();
  }

  /**
   * Full hierarchy avatar resolution
   * Returns the best available avatar based on the 4-level fallback chain
   * 
   * @param {string} agentId - Unique agent identifier
   * @param {string} role - Agent role (for Level 2)
   * @param {string} stance - Stance ('D', 'L', 'R', 'U')
   * @param {number} frame - Frame number (1, 2, 3)
   * @returns {Object} Avatar resolution result
   */
  async resolveAvatar(agentId, role = null, stance = 'D', frame = 1) {
    // Level 1: Custom Avatar
    if (!this.checkedCustomAvatars.has(agentId)) {
      const customPath = `/avatars/${agentId}.png`;
      const hasCustom = await this.checkImageExists(customPath);
      
      if (hasCustom) {
        this.customAvatarCache.set(agentId, customPath);
        return {
          level: 1,
          type: 'custom',
          path: customPath,
          agentId,
          fallback: false
        };
      }
      
      this.checkedCustomAvatars.add(agentId);
    } else if (this.customAvatarCache.has(agentId)) {
      return {
        level: 1,
        type: 'custom',
        path: this.customAvatarCache.get(agentId),
        agentId,
        fallback: false
      };
    }
    
    // Level 2: Role-Based Sprite
    if (role && this.roleSpriteMap[role]) {
      const character = this.roleSpriteMap[role];
      return {
        level: 2,
        type: 'role',
        role,
        character,
        path: `/sprites/${character}-${stance}-${frame}.png`,
        agentId,
        fallback: false
      };
    }
    
    // Level 3: Generic Sprite
    const character = this.getOrAssignCharacter(agentId);
    return {
      level: 3,
      type: 'generic',
      character,
      path: `/sprites/${character}-${stance}-${frame}.png`,
      agentId,
      fallback: false
    };
  }

  /**
   * Create an image element with full fallback chain
   * Automatically falls through all 4 levels on error
   * 
   * @param {string} agentId - Agent identifier
   * @param {string} role - Agent role
   * @param {string} stance - Stance direction
   * @param {number} frame - Animation frame
   * @returns {HTMLImageElement} Image element with fallback handlers
   */
  createAvatarImage(agentId, role = null, stance = 'D', frame = 1) {
    const img = new Image();
    img.dataset.agentId = agentId;
    img.dataset.role = role || '';
    img.dataset.stance = stance;
    img.dataset.frame = frame;
    
    // Start at Level 1 (Custom)
    this.tryLoadLevel(img, 1);
    
    return img;
  }

  /**
   * Try loading avatar at specific hierarchy level
   * Falls to next level on error
   * 
   * @param {HTMLImageElement} img - Image element
   * @param {number} level - Hierarchy level (1-4)
   */
  tryLoadLevel(img, level) {
    const agentId = img.dataset.agentId;
    const role = img.dataset.role;
    const stance = img.dataset.stance;
    const frame = parseInt(img.dataset.frame);
    
    switch (level) {
      case 1: // Custom Avatar
        img.src = `/avatars/${agentId}.png`;
        img.dataset.level = '1';
        img.dataset.type = 'custom';
        break;
        
      case 2: // Role-Based
        if (role && this.roleSpriteMap[role]) {
          const char = this.roleSpriteMap[role];
          img.src = `/sprites/${char}-${stance}-${frame}.png`;
          img.dataset.level = '2';
          img.dataset.type = 'role';
          img.dataset.character = char;
          break;
        }
        // Fall through if no role mapping
        
      case 3: // Generic Sprite
        const character = this.getOrAssignCharacter(agentId);
        img.src = `/sprites/${character}-${stance}-${frame}.png`;
        img.dataset.level = '3';
        img.dataset.type = 'generic';
        img.dataset.character = character;
        break;
        
      case 4: // Initials Fallback (guaranteed)
        img.src = this.generateInitialsAvatar(agentId);
        img.dataset.level = '4';
        img.dataset.type = 'initials';
        img.dataset.fallback = 'true';
        return; // No more fallbacks
    }
    
    // Set up error handler for next level
    img.onerror = () => {
      this.tryLoadLevel(img, level + 1);
    };
  }

  /**
   * Get or assign a character to an agent
   * Ensures consistent sprite assignment per agent
   * 
   * @param {string} agentId - Agent identifier
   * @returns {number} Character number (1-12)
   */
  getOrAssignCharacter(agentId) {
    // Return existing assignment
    if (this.nodeCharacterMap.has(agentId)) {
      return this.nodeCharacterMap.get(agentId);
    }
    
    // Assign new character
    let character;
    if (this.unassignedCharacters.length === 0) {
      // All assigned, pick randomly from full pool
      character = this.availableCharacters[
        Math.floor(Math.random() * this.availableCharacters.length)
      ];
    } else {
      // Pick from unassigned pool
      const randomIndex = Math.floor(Math.random() * this.unassignedCharacters.length);
      character = this.unassignedCharacters[randomIndex];
      this.unassignedCharacters.splice(randomIndex, 1);
    }
    
    // Bind to agent
    this.nodeCharacterMap.set(agentId, character);
    return character;
  }

  /**
   * Get sprite path (original method - Level 3 only)
   * Maintains backward compatibility
   * 
   * @param {string} node_id - Node/agent ID
   * @param {string} stance - Stance direction
   * @param {number} frame - Animation frame
   * @returns {string} Sprite path
   */
  fetchSprite(node_id = null, stance = 'D', frame = 1) {
    const character = node_id 
      ? this.getOrAssignCharacter(node_id)
      : this.availableCharacters[Math.floor(Math.random() * 12)];
    
    return `/sprites/${character}-${stance}-${frame}.png`;
  }

  /**
   * Generate initials fallback avatar (Level 4)
   * Creates SVG data URI with initials and consistent color
   * 
   * @param {string} node_id - Agent identifier
   * @returns {string} Base64 SVG data URI
   */
  generateInitialsAvatar(node_id) {
    // Extract initials: "trend-scout" → "TS", "agent" → "AG"
    const words = node_id.split(/[-_]/);
    const initials = words.length > 1 
      ? (words[0][0] + words[words.length - 1][0]).toUpperCase()
      : node_id.slice(0, 2).toUpperCase();
    
    // Generate consistent HSL color from node_id hash
    const hash = node_id.split('').reduce((a, b) => {
      a = ((a << 5) - a) + b.charCodeAt(0);
      return a & a;
    }, 0);
    const hue = Math.abs(hash % 360);
    const color = `hsl(${hue}, 70%, 50%)`;
    const bgColor = `hsl(${hue}, 70%, 20%)`;
    
    // Create SVG avatar
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
        <defs>
          <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:${bgColor}"/>
            <stop offset="100%" style="stop-color:${color}"/>
          </linearGradient>
        </defs>
        <circle cx="32" cy="32" r="30" fill="url(#g)" stroke="${color}" stroke-width="2"/>
        <text x="32" y="38" font-family="Arial, sans-serif" font-size="20" font-weight="bold" 
              fill="white" text-anchor="middle">${initials}</text>
      </svg>
    `.trim();
    
    // Convert to base64 data URI
    const base64 = typeof btoa !== 'undefined' 
      ? btoa(svg)
      : Buffer.from(svg).toString('base64');
    
    return `data:image/svg+xml;base64,${base64}`;
  }

  /**
   * Check if image exists (async)
   * 
   * @param {string} url - Image URL to check
   * @returns {Promise<boolean>} True if image exists
   */
  checkImageExists(url) {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(true);
      img.onerror = () => resolve(false);
      img.src = url;
    });
  }

  /**
   * Preload avatar for an agent (optimistic)
   * Checks custom avatar and caches result
   * 
   * @param {string} agentId - Agent identifier
   */
  async preloadAvatar(agentId) {
    if (this.checkedCustomAvatars.has(agentId)) return;
    
    const customPath = `/avatars/${agentId}.png`;
    const hasCustom = await this.checkImageExists(customPath);
    
    if (hasCustom) {
      this.customAvatarCache.set(agentId, customPath);
    }
    this.checkedCustomAvatars.add(agentId);
  }

  /**
   * Get current system status
   * 
   * @returns {Object} Status summary
   */
  getStatus() {
    return {
      totalCharacters: this.availableCharacters.length,
      assignedNodes: this.nodeCharacterMap.size,
      unassignedCount: this.unassignedCharacters.length,
      customAvatars: this.customAvatarCache.size,
      nodeCharacterMap: Object.fromEntries(this.nodeCharacterMap),
      roleSpriteMap: this.roleSpriteMap,
      unassignedCharacters: [...this.unassignedCharacters].sort((a, b) => a - b)
    };
  }

  /**
   * Reset all assignments (use with caution)
   */
  reset() {
    this.nodeCharacterMap.clear();
    this.unassignedCharacters = [...this.availableCharacters];
    this.customAvatarCache.clear();
    this.checkedCustomAvatars.clear();
    console.log('SpriteFetcher: All assignments reset');
  }
}

// Create singleton instance
export const spriteFetcher = new SpriteFetcher();

// Backward compatibility exports
export default spriteFetcher;
