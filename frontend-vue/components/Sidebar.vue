<template>
    <div class="sidebar" :class="{ 'is-hidden': isHidden }" @mouseenter="isHidden = false">
        <nav class="sidebar-nav">
            <router-link to="/">{{ $t('nav.home') }}</router-link>
            
            <router-link to="/dashboard">Dashboard</router-link>
            
            <router-link to="/tutorial">{{ $t('nav.tutorial') }}</router-link>
            
            <router-link
                to="/workflows"
                :class="{ active: isWorkflowsActive }"
            >{{ $t('nav.workflows') }}</router-link>
            
            <router-link to="/revenue">Revenue</router-link>
            
            <router-link to="/launch" target="_blank" rel="noopener">{{ $t('nav.launch') }}</router-link>
            
            <router-link to="/batch-run" target="_blank" rel="noopener">{{ $t('nav.laboratory') }}</router-link>
        </nav>
        
        <div class="sidebar-actions">
            <button class="settings-nav-btn" @click="showSettingsModal = true" :title="$t('settings.title')">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
            </button>
        </div>
    </div>
    
    <div class="sidebar-hit-area" v-if="isHidden" @mouseenter="isHidden = false"></div>
    
    <SettingsModal
      :is-visible="showSettingsModal"
      @update:is-visible="showSettingsModal = $event"
    />
</template>

<script setup>
import { RouterLink, useRoute } from 'vue-router'
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import SettingsModal from './SettingsModal.vue'

const showSettingsModal = ref(false)
const isHidden = ref(false)

watch(isHidden, (val) => {
    if (val) {
        document.body.classList.add('nav-hidden')
    } else {
        document.body.classList.remove('nav-hidden')
    }
})

const route = useRoute()
const isWorkflowsActive = computed(() => route.path.startsWith('/workflows'))

let lastScrollY = 0
const handleScroll = (e) => {
    const currentScrollY = e.target.scrollTop || window.scrollY || 0;
    // Minimize small scroll jitters
    if (Math.abs(currentScrollY - lastScrollY) < 5) return;

    // Scrolling down -> hide (if past slight threshold). Scrolling up -> show
    if (currentScrollY > lastScrollY && currentScrollY > 10) {
        isHidden.value = true;
    } else if (currentScrollY < lastScrollY) {
        isHidden.value = false;
    }
    lastScrollY = currentScrollY <= 0 ? 0 : currentScrollY;
}

const toggleScrollListener = (shouldListen) => {
    if (shouldListen) {
        window.addEventListener('scroll', handleScroll, true);
    } else {
        window.removeEventListener('scroll', handleScroll, true);
        isHidden.value = false; // Reset state when leaving
    }
}

watch(() => route.path, () => {
    toggleScrollListener(!!route.meta.hideNavOnScroll);
}, { immediate: true }) // immediate: true runs this once on mount

onUnmounted(() => {
    toggleScrollListener(false);
    document.body.classList.remove('nav-hidden');
})
</script>

<style scoped>
.sidebar {
    width: 100%;
    background-color: rgba(10, 22, 40, 0.97);
    padding: 0 24px 0 0;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    height: 55px;
    position: sticky;
    top: 0;
    z-index: 100;
    border-bottom: 1px solid rgba(0, 243, 255, 0.2);
    justify-content: center;
    backdrop-filter: blur(10px);
    box-shadow: 0 2px 20px rgba(0, 243, 255, 0.05);
    transition: margin-top 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    margin-top: 0;
    transform: translateY(0);
}

.sidebar.is-hidden {
    margin-top: -55px;
    transform: translateY(-100%);
}

.sidebar-hit-area {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 25px;
    z-index: 99;
}

.sidebar-actions {
    position: absolute;
    right: 24px;
    top: 50%;
    transform: translateY(-50%);
}

.sidebar-nav {
    display: flex;
    flex-direction: row;
    gap: 24px;
    align-items: center;
    margin-left: auto;
    margin-right: auto;
}

.sidebar-nav a {
    text-decoration: none;
    color: #7fb3d5;
    font-weight: 500;
    font-size: 13px;
    font-family: 'Rajdhani', 'Segoe UI', sans-serif;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    transition: color 0.25s ease, text-shadow 0.25s ease;
}

.sidebar-nav a:hover {
    color: #fff;
    text-shadow: 0 0 12px rgba(0, 243, 255, 0.6);
}

.sidebar-nav a.router-link-active,
.sidebar-nav a.active {
    color: #00f3ff;
    text-shadow: 0 0 16px rgba(0, 243, 255, 0.7);
    -webkit-text-fill-color: unset;
}

.settings-nav-btn {
  background: transparent;
  border: none;
  color: #7fb3d5;
  cursor: pointer;
  padding: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.25s ease, text-shadow 0.25s ease;
  border-radius: 4px;
}

.settings-nav-btn:hover {
  color: #00f3ff;
  filter: drop-shadow(0 0 6px rgba(0, 243, 255, 0.6));
}
</style>
