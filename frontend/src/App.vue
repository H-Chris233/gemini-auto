<template>
  <div class="app">
    <!-- 顶部导航 -->
    <header class="header">
      <div class="container">
        <div class="header-content">
          <h1 class="logo">
            <span class="logo-icon">✨</span>
            Gemini Auto
          </h1>
          <nav class="nav">
            <a href="#" class="nav-item" :class="{ active: currentView === 'dashboard' }" @click.prevent="currentView = 'dashboard'">
              任务控制
            </a>
            <a href="#" class="nav-item" :class="{ active: currentView === 'accounts' }" @click.prevent="currentView = 'accounts'">
              账号管理
            </a>
          </nav>
          <div class="header-status">
            <span class="status-indicator" :class="{ online: isHealthy }"></span>
            <span class="status-text">{{ isHealthy ? '在线' : '离线' }}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main">
      <div class="container">
        <Dashboard v-if="currentView === 'dashboard'" />
        <Accounts v-if="currentView === 'accounts'" />
      </div>
    </main>

    <!-- 页脚 -->
    <footer class="footer">
      <p>Gemini Auto Web v{{ version }} - Gemini Business 自动注册工具</p>
    </footer>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import Dashboard from './views/Dashboard.vue'
import Accounts from './views/Accounts.vue'
import { api } from './api'

export default {
  name: 'App',
  components: {
    Dashboard,
    Accounts,
  },
  setup() {
    const currentView = ref('dashboard')
    const isHealthy = ref(false)
    const version = ref('1.0.0')
    let healthCheckInterval = null

    const checkHealth = async () => {
      try {
        const res = await api.getHealth()
        isHealthy.value = res.status === 'healthy'
        version.value = res.version
      } catch (e) {
        isHealthy.value = false
      }
    }

    onMounted(() => {
      checkHealth()
      healthCheckInterval = setInterval(checkHealth, 10000)
    })

    onUnmounted(() => {
      if (healthCheckInterval) {
        clearInterval(healthCheckInterval)
      }
    })

    return {
      currentView,
      isHealthy,
      version,
    }
  }
}
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background: rgba(255, 255, 255, 0.05);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding: 16px 0;
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  font-size: 1.5rem;
  font-weight: 700;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-icon {
  font-size: 1.8rem;
}

.nav {
  display: flex;
  gap: 8px;
}

.nav-item {
  padding: 8px 16px;
  color: #888;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.nav-item:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.nav-item.active {
  color: #fff;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.header-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #888;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f44336;
}

.status-indicator.online {
  background: #4caf50;
  box-shadow: 0 0 10px rgba(76, 175, 80, 0.5);
}

.main {
  flex: 1;
  padding: 20px 0;
}

.footer {
  padding: 20px;
  text-align: center;
  color: #666;
  font-size: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
</style>
