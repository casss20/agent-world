<template>
  <div class="dashboard">
    <!-- Header -->
    <header class="dashboard-header">
      <div>
        <h1>Dashboard</h1>
        <p class="subtitle">Content Arbitrage Performance</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-primary" @click="startWorkflow">
          <span>+ New Campaign</span>
        </button>
      </div>
    </header>

    <!-- Stats Grid -->
    <section class="stats-grid">
      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-icon">💰</span>
          <span class="badge badge-green">+12%</span>
        </div>
        <div class="stat-value-large">{{ formatMoney(stats.total_actual_revenue) }}</div>
        <div class="stat-label-large">Total Revenue</div>
        <div class="stat-footer">
          Est: {{ formatMoney(stats.total_estimated_revenue) }}
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-icon">📝</span>
          <span class="badge badge-cyan">+5</span>
        </div>
        <div class="stat-value-large">{{ stats.total_content_published }}</div>
        <div class="stat-label-large">Content Published</div>
        <div class="stat-footer">
          {{ activeWorkflows }} active workflows
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-icon">🎯</span>
          <span class="badge badge-purple">{{ avgScore }}</span>
        </div>
        <div class="stat-value-large">{{ conversionRate }}%</div>
        <div class="stat-label-large">Conversion Rate</div>
        <div class="stat-footer">
          Avg score: {{ stats.avg_opportunity_score }}/10
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-icon">📈</span>
          <span class="badge badge-pink">ROI</span>
        </div>
        <div class="stat-value-large">{{ roi }}%</div>
        <div class="stat-label-large">ROI</div>
        <div class="stat-footer">
          Profit: {{ formatMoney(stats.total_profit) }}
        </div>
      </div>
    </section>

    <!-- Platform Breakdown -->
    <section class="dashboard-section">
      <div class="section-header">
        <h2>Platform Performance</h2>
      </div>
      
      <div class="platform-grid">
        <div v-for="(data, platform) in stats.platforms" :key="platform" class="platform-card">
          <div class="platform-icon" :class="platform">
            {{ getPlatformIcon(platform) }}
          </div>
          <div class="platform-info">
            <div class="platform-name">{{ platform }}</div>
            <div class="platform-stats">
              <span>{{ data.count }} posts</span>
              <span class="platform-revenue">{{ formatMoney(data.revenue) }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Recent Activity -->
    <section class="dashboard-section">
      <div class="section-header">
        <h2>Recent Content</h2>
        <router-link to="/revenue" class="view-all">View All →</router-link>
      </div>
      
      <div class="content-list">
        <div v-for="entry in stats.recent_entries" :key="entry.tracking_id" class="content-item">
          <div class="content-status" :class="entry.platform">
            <span class="status-dot" :class="getStatusClass(entry)"></span>
          </div>
          
          <div class="content-info">
            <div class="content-title">{{ entry.content_title }}</div>
            <div class="content-meta">
              <span class="badge" :class="getPlatformBadgeClass(entry.platform)">
                {{ entry.platform }}
              </span>
              <span class="meta-date">{{ formatDate(entry.timestamp) }}</span>
              <span class="meta-score">Score: {{ entry.opportunity_score }}/10</span>
            </div>
          </div>
          
          <div class="content-revenue">
            <div class="revenue-actual">{{ formatMoney(entry.actual_revenue) }}</div>
            <div class="revenue-est">est: {{ formatMoney(entry.estimated_revenue) }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- Top Performers -->
    <section class="dashboard-section">
      <div class="section-header">
        <h2>Top Performers</h2>
      </div>
      
      <div class="leaderboard">
        <div v-for="(entry, index) in stats.top_content" :key="entry.tracking_id" class="leader-item">
          <div class="leader-rank" :class="{ 'top-3': index < 3 }">#{{ index + 1 }}</div>
          
          <div class="leader-info">
            <div class="leader-title">{{ entry.content_title }}</div>
            <div class="leader-meta">{{ entry.platform }} • {{ entry.views }} views</div>
          </div>
          
          <div class="leader-revenue">{{ formatMoney(entry.actual_revenue) }}</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const stats = ref({
  total_workflows: 47,
  total_content_published: 47,
  total_actual_revenue: 2847.50,
  total_estimated_revenue: 5200.00,
  total_profit: 2347.50,
  avg_opportunity_score: 7.2,
  platforms: {
    ghost: { count: 23, revenue: 1450.00 },
    wordpress: { count: 15, revenue: 875.50 },
    etsy: { count: 9, revenue: 522.00 }
  },
  recent_entries: [],
  top_content: []
})

const activeWorkflows = ref(3)

// Computed
const avgScore = computed(() => Math.round(stats.value.avg_opportunity_score * 10) / 10)
const conversionRate = computed(() => '3.2')
const roi = computed(() => {
  if (stats.value.total_actual_revenue === 0) return 0
  return Math.round((stats.value.total_profit / 500) * 100) // Assuming $500 cost
})

// Methods
function formatMoney(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(amount || 0)
}

function formatDate(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function getPlatformIcon(platform) {
  const icons = {
    ghost: '👻',
    wordpress: '📝',
    etsy: '🛍️',
    medium: '📰',
    shopify: '🛒'
  }
  return icons[platform] || '📄'
}

function getPlatformBadgeClass(platform) {
  const classes = {
    ghost: 'badge-cyan',
    wordpress: 'badge-purple',
    etsy: 'badge-pink',
    medium: 'badge-green'
  }
  return classes[platform] || 'badge-cyan'
}

function getStatusClass(entry) {
  if (entry.actual_revenue > entry.estimated_revenue) return 'status-online'
  if (entry.actual_revenue > 0) return 'status-working'
  return 'status-idle'
}

function startWorkflow() {
  router.push('/launch')
}

// Fetch data on mount
onMounted(async () => {
  try {
    const response = await fetch('http://localhost:8000/revenue/stats')
    if (response.ok) {
      const data = await response.json()
      stats.value = { ...stats.value, ...data }
    }
  } catch (e) {
    console.log('Using mock data - API not available')
  }
})
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.subtitle {
  color: var(--text-secondary);
  margin: 0.25rem 0 0;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: var(--cyber-dark);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  transition: all 0.3s ease;
}

.stat-card:hover {
  border-color: var(--neon-cyan);
  box-shadow: 0 4px 20px rgba(0, 243, 255, 0.1);
}

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.stat-icon {
  font-size: 1.5rem;
}

.stat-value-large {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  font-family: 'JetBrains Mono', monospace;
}

.stat-value-large[style*="revenue"],
.stat-card:first-child .stat-value-large {
  color: var(--neon-green);
  text-shadow: var(--glow-green);
}

.stat-label-large {
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.stat-footer {
  color: var(--text-muted);
  font-size: 0.75rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-color);
}

/* Sections */
.dashboard-section {
  margin-bottom: 2rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h2 {
  font-size: 1.25rem;
  color: var(--text-primary);
}

.view-all {
  color: var(--neon-cyan);
  font-size: 0.875rem;
}

/* Platform Grid */
.platform-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.platform-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: var(--cyber-dark);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 1rem;
}

.platform-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  background: var(--cyber-gray);
}

.platform-info {
  flex: 1;
}

.platform-name {
  font-weight: 600;
  text-transform: capitalize;
  color: var(--text-primary);
}

.platform-stats {
  display: flex;
  justify-content: space-between;
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.platform-revenue {
  color: var(--neon-green);
  font-weight: 600;
}

/* Content List */
.content-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.content-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: var(--cyber-dark);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 1rem;
  transition: all 0.2s ease;
}

.content-item:hover {
  border-color: var(--neon-cyan);
}

.content-status {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
}

.content-info {
  flex: 1;
  min-width: 0;
}

.content-title {
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.content-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.25rem;
  font-size: 0.75rem;
}

.meta-date,
.meta-score {
  color: var(--text-muted);
}

.content-revenue {
  text-align: right;
}

.revenue-actual {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--neon-green);
  font-family: 'JetBrains Mono', monospace;
}

.revenue-est {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* Leaderboard */
.leaderboard {
  background: var(--cyber-dark);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 1rem;
}

.leader-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.875rem;
  border-bottom: 1px solid var(--border-color);
}

.leader-item:last-child {
  border-bottom: none;
}

.leader-rank {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-weight: 700;
  font-size: 0.875rem;
  background: var(--cyber-gray);
  color: var(--text-secondary);
}

.leader-rank.top-3 {
  background: var(--gradient-cyber);
  color: var(--cyber-black);
}

.leader-info {
  flex: 1;
  min-width: 0;
}

.leader-title {
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.leader-meta {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.125rem;
}

.leader-revenue {
  font-size: 1rem;
  font-weight: 600;
  color: var(--neon-green);
  font-family: 'JetBrains Mono', monospace;
}

/* Responsive */
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .dashboard-header {
    flex-direction: column;
    gap: 1rem;
  }
  
  .platform-grid {
    grid-template-columns: 1fr;
  }
}
</style>
