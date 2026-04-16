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
          <span class="stat-icon stat-icon--green">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          </span>
          <span class="badge badge-green">+12%</span>
        </div>
        <div class="stat-value-large stat-value--green">{{ formatMoney(stats.total_actual_revenue) }}</div>
        <div class="stat-label-large">Total Revenue</div>
        <div class="stat-footer">Est: {{ formatMoney(stats.total_estimated_revenue) }}</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-icon stat-icon--cyan">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          </span>
          <span class="badge badge-cyan">+5</span>
        </div>
        <div class="stat-value-large stat-value--cyan">{{ stats.total_content_published }}</div>
        <div class="stat-label-large">Content Published</div>
        <div class="stat-footer">{{ activeWorkflows }} active workflows</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-icon stat-icon--cyan">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          </span>
          <span class="badge badge-cyan">{{ avgScore }}</span>
        </div>
        <div class="stat-value-large stat-value--cyan">{{ conversionRate }}%</div>
        <div class="stat-label-large">Conversion Rate</div>
        <div class="stat-footer">Avg score: {{ stats.avg_opportunity_score }}/10</div>
      </div>

      <div class="stat-card">
        <div class="stat-header">
          <span class="stat-icon stat-icon--pink">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
          </span>
          <span class="badge badge-pink">ROI</span>
        </div>
        <div class="stat-value-large stat-value--pink">{{ roi }}%</div>
        <div class="stat-label-large">ROI</div>
        <div class="stat-footer">Profit: {{ formatMoney(stats.total_profit) }}</div>
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
/* ── Layout ─────────────────────────────────────────────────────── */
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem 2rem 4rem;
}

/* ── Header ──────────────────────────────────────────────────────── */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.dashboard-header h1 {
  font-family: 'Orbitron', monospace;
  font-size: 1.5rem;
  color: #00f3ff;
  text-shadow: 0 0 20px rgba(0, 243, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin: 0;
}

.subtitle {
  color: #7fb3d5;
  font-size: 0.85rem;
  margin: 0.3rem 0 0;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.header-actions { display: flex; gap: 1rem; }

/* ── Stats Grid ──────────────────────────────────────────────────── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.25rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: rgba(10, 22, 40, 0.95);
  border: 1px solid rgba(0, 243, 255, 0.2);
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 243, 255, 0.4), transparent);
}

.stat-card:hover {
  border-color: #00f3ff;
  box-shadow: 0 4px 30px rgba(0, 243, 255, 0.12), 0 0 0 1px rgba(0, 243, 255, 0.1);
  transform: translateY(-2px);
}

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

/* Stat Icons */
.stat-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-icon--cyan { color: #00f3ff; background: rgba(0, 243, 255, 0.1); }
.stat-icon--pink { color: #ff006e; background: rgba(255, 0, 110, 0.1); }
.stat-icon--green { color: #39ff14; background: rgba(57, 255, 20, 0.08); }

/* Stat Values */
.stat-value-large {
  font-size: 1.9rem;
  font-weight: 700;
  font-family: 'Orbitron', monospace;
  line-height: 1;
  margin-bottom: 0.3rem;
}

.stat-value--cyan  { color: #00f3ff; text-shadow: 0 0 12px rgba(0, 243, 255, 0.5); }
.stat-value--pink  { color: #ff006e; text-shadow: 0 0 12px rgba(255, 0, 110, 0.5); }
.stat-value--green { color: #39ff14; text-shadow: 0 0 12px rgba(57, 255, 20, 0.4); }

.stat-label-large {
  color: #7fb3d5;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
}

.stat-footer {
  color: #475569;
  font-size: 0.72rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(0, 243, 255, 0.1);
}

/* ── Sections ────────────────────────────────────────────────────── */
.dashboard-section { margin-bottom: 2rem; }

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h2 {
  font-family: 'Orbitron', monospace;
  font-size: 0.85rem;
  color: #7fb3d5;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.view-all {
  color: #00f3ff;
  font-size: 0.8rem;
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  transition: text-shadow 0.2s;
}

.view-all:hover { text-shadow: 0 0 12px rgba(0, 243, 255, 0.7); }

/* ── Platform Grid ───────────────────────────────────────────────── */
.platform-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.platform-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: rgba(10, 22, 40, 0.95);
  border: 1px solid rgba(0, 243, 255, 0.15);
  border-radius: 8px;
  padding: 1rem;
  transition: all 0.25s ease;
}

.platform-card:hover {
  border-color: rgba(0, 243, 255, 0.4);
  box-shadow: 0 0 20px rgba(0, 243, 255, 0.08);
}

.platform-icon {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
  background: rgba(0, 243, 255, 0.08);
  border: 1px solid rgba(0, 243, 255, 0.15);
}

.platform-name {
  font-weight: 600;
  font-size: 0.9rem;
  text-transform: capitalize;
  color: #e0e1dd;
}

.platform-stats {
  display: flex;
  justify-content: space-between;
  margin-top: 0.25rem;
  font-size: 0.8rem;
  color: #7fb3d5;
}

.platform-revenue {
  color: #39ff14;
  font-weight: 600;
  font-family: 'Orbitron', monospace;
  font-size: 0.75rem;
}

/* ── Content List ────────────────────────────────────────────────── */
.content-list { display: flex; flex-direction: column; gap: 0.6rem; }

.content-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: rgba(10, 22, 40, 0.8);
  border: 1px solid rgba(0, 243, 255, 0.12);
  border-radius: 8px;
  padding: 0.9rem 1rem;
  transition: all 0.2s ease;
}

.content-item:hover {
  border-color: rgba(0, 243, 255, 0.35);
  background: rgba(10, 22, 40, 0.95);
}

.content-status { width: 28px; display: flex; justify-content: center; }

.content-info { flex: 1; min-width: 0; }

.content-title {
  font-size: 0.9rem;
  font-weight: 500;
  color: #e0e1dd;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.content-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.25rem;
  font-size: 0.72rem;
}

.meta-date, .meta-score { color: #475569; }

.content-revenue { text-align: right; }

.revenue-actual {
  font-size: 1rem;
  font-weight: 700;
  color: #39ff14;
  font-family: 'Orbitron', monospace;
  text-shadow: 0 0 8px rgba(57, 255, 20, 0.4);
}

.revenue-est { font-size: 0.7rem; color: #475569; margin-top: 2px; }

/* ── Leaderboard ─────────────────────────────────────────────────── */
.leaderboard {
  background: rgba(10, 22, 40, 0.95);
  border: 1px solid rgba(0, 243, 255, 0.2);
  border-radius: 12px;
  padding: 0.5rem;
  overflow: hidden;
}

.leader-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.875rem 1rem;
  border-bottom: 1px solid rgba(0, 243, 255, 0.08);
  transition: background 0.2s;
}

.leader-item:hover { background: rgba(0, 243, 255, 0.04); }
.leader-item:last-child { border-bottom: none; }

.leader-rank {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-weight: 700;
  font-size: 0.8rem;
  font-family: 'Orbitron', monospace;
  background: rgba(0, 243, 255, 0.08);
  color: #7fb3d5;
  border: 1px solid rgba(0, 243, 255, 0.15);
}

.leader-rank.top-3 {
  background: linear-gradient(135deg, #00f3ff, #ff006e);
  color: #050a14;
  border-color: transparent;
  box-shadow: 0 0 12px rgba(0, 243, 255, 0.4);
}

.leader-info { flex: 1; min-width: 0; }

.leader-title {
  font-size: 0.88rem;
  font-weight: 500;
  color: #e0e1dd;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.leader-meta { font-size: 0.72rem; color: #475569; margin-top: 2px; }

.leader-revenue {
  font-size: 0.95rem;
  font-weight: 700;
  color: #39ff14;
  font-family: 'Orbitron', monospace;
  text-shadow: 0 0 8px rgba(57, 255, 20, 0.4);
}

/* ── Responsive ──────────────────────────────────────────────────── */
@media (max-width: 1200px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: 1fr; }
  .dashboard { padding: 1rem 1rem 3rem; }
  .dashboard-header { flex-direction: column; gap: 1rem; }
  .platform-grid { grid-template-columns: 1fr; }
}
</style>
