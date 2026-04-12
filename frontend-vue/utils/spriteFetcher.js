/**
 * SpriteFetcher manages sprite image selection.
 * It provides random sprite selection and tracks used sprites to avoid duplicates.
 */
export class SpriteFetcher {
  constructor() {
    // Available character list (1-12)
    this.availableCharacters = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    // Map of characters already bound to node_id
    this.nodeCharacterMap = new Map()
    // Unassigned character pool for random allocation
    this.unassignedCharacters = [...this.availableCharacters]
  }

  /**
   * Get a random sprite image path.
   * @param {string} node_id - Node ID used to bind a character.
   * @param {string} stance - Stance ('D', 'L', 'R', 'U').
   * @param {number} frame - Frame number (1, 2, 3).
   * @returns {string} Image path.
   */
  fetchSprite(node_id = null, stance = 'D', frame = 1) {
    let character

    if (node_id) {
      // Use the bound character if this node already has one.
      if (this.nodeCharacterMap.has(node_id)) {
        character = this.nodeCharacterMap.get(node_id)
      } else {
        // If no character is bound, choose one at random.
        if (this.unassignedCharacters.length === 0) {
          // If all characters are assigned, pick one from the assigned pool.
          character = this.availableCharacters[Math.floor(Math.random() * this.availableCharacters.length)]
        } else {
          // Pick randomly from the unassigned pool.
          const randomIndex = Math.floor(Math.random() * this.unassignedCharacters.length)
          character = this.unassignedCharacters[randomIndex]
          this.unassignedCharacters.splice(randomIndex, 1)
        }

        // Bind the character to the node.
        this.nodeCharacterMap.set(node_id, character)
      }
    } else {
      // If no node_id is specified, select a random character.
      character = this.availableCharacters[Math.floor(Math.random() * this.availableCharacters.length)]
    }

    // Build the sprite path.
    const spritePath = `/sprites/${character}-${stance}-${frame}.png`

    return spritePath
  }

  /**
   * Generate a fallback initials avatar as SVG data URI.
   * Used when sprite image fails to load.
   * @param {string} node_id - Node ID to generate initials from.
   * @returns {string} SVG data URI.
   */
  generateInitialsAvatar(node_id) {
    // Extract initials from node_id (first letter, or first letters of words)
    const words = node_id.split(/[-_]/)
    const initials = words.length > 1 
      ? (words[0][0] + words[words.length - 1][0]).toUpperCase()
      : node_id.slice(0, 2).toUpperCase()
    
    // Generate consistent color from node_id
    const hash = node_id.split('').reduce((a, b) => {
      a = ((a << 5) - a) + b.charCodeAt(0)
      return a & a
    }, 0)
    const hue = Math.abs(hash % 360)
    const color = `hsl(${hue}, 70%, 50%)`
    const bgColor = `hsl(${hue}, 70%, 20%)`
    
    // Create SVG
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
    `.trim()
    
    return `data:image/svg+xml;base64,${btoa(svg)}`
  }

  /**
   * Create an image element with fallback handling.
   * @param {string} node_id - Node ID.
   * @param {string} stance - Stance ('D', 'L', 'R', 'U').
   * @param {number} frame - Frame number.
   * @returns {HTMLImageElement} Image element with fallback.
   */
  createImageWithFallback(node_id, stance = 'D', frame = 1) {
    const spritePath = this.fetchSprite(node_id, stance, frame)
    const img = new Image()
    
    img.onerror = () => {
      // Fallback to initials avatar
      img.src = this.generateInitialsAvatar(node_id)
      img.dataset.fallback = 'true'
    }
    
    img.src = spritePath
    img.dataset.character = this.nodeCharacterMap.get(node_id) || 'fallback'
    
    return img
  }

  /**
   * Get current usage status.
   * @returns {Object} Usage status summary.
   */
  getStatus() {
    return {
      totalCharacters: this.availableCharacters.length,
      assignedNodes: this.nodeCharacterMap.size,
      unassignedCount: this.unassignedCharacters.length,
      nodeCharacterMap: Object.fromEntries(this.nodeCharacterMap),
      unassignedCharacters: [...this.unassignedCharacters].sort((a, b) => a - b)
    }
  }

  /**
   * Reset usage state and clear used sprite records.
   */
  reset() {
    this.nodeCharacterMap.clear()
    this.unassignedCharacters = [...this.availableCharacters]
    console.log('Sprite usage state reset')
  }
}

// Create a singleton instance.
export const spriteFetcher = new SpriteFetcher()
