<template>
  <div class="accounts">
    <!-- 统计卡片 -->
    <div class="stat-grid">
      <StatusCard :value="displayStats.total" label="总数" color="#667eea" />
      <StatusCard :value="displayStats.active" label="有效" color="#4caf50" />
      <StatusCard :value="displayStats.disabled" label="禁用" color="#ff9800" />
      <StatusCard :value="displayStats.expired" label="过期" color="#f44336" />
    </div>

    <!-- 账号列表卡片 -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">
          <span>👥</span>
          账号列表
        </h2>
        <div class="card-actions">
          <button
            class="btn btn-secondary btn-toggle"
            :class="{ active: viewMode === 'local' }"
            @click="switchView('local')"
          >
            本地
          </button>
          <button
            class="btn btn-secondary btn-toggle"
            :class="{ active: viewMode === 'remote' }"
            @click="switchView('remote')"
          >
            远程
          </button>
          <button class="btn btn-secondary" @click="refreshAccounts">
            刷新
          </button>
        </div>
      </div>

      <!-- 账号表格 -->
      <div class="table-container">
        <div v-if="viewMode === 'remote' && remoteError" class="error-state">
          {{ remoteError }}
        </div>
        <table class="data-table" v-if="displayAccounts.length > 0">
          <thead>
            <tr>
              <th>序号</th>
              <th>账号 ID</th>
              <th>状态</th>
              <th>过期时间</th>
              <th>剩余时长</th>
              <th>累计对话</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(account, index) in displayAccounts" :key="account.id">
              <td>{{ index + 1 }}</td>
              <td class="account-id">{{ account.id }}</td>
              <td>
                <span class="status-badge" :class="getStatusClass(account)">
                  {{ getStatusText(account) }}
                </span>
              </td>
              <td>{{ formatTime(account.expires_at) }}</td>
              <td>{{ account.remaining_display || '-' }}</td>
              <td>{{ account.conversation_count || 0 }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-state">
          <span class="empty-icon">📭</span>
          <p>暂无账号数据</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../api'
import StatusCard from '../components/StatusCard.vue'

export default {
  name: 'Accounts',
  components: {
    StatusCard,
  },
  setup() {
    const viewMode = ref('local')
    const accounts = ref([])
    const remoteAccounts = ref([])
    const stats = reactive({
      total: 0,
      active: 0,
      disabled: 0,
      expired: 0,
    })
    const remoteStats = reactive({
      total: 0,
      active: 0,
      disabled: 0,
      expired: 0,
    })
    const remoteError = ref('')

    const displayAccounts = computed(() => {
      return viewMode.value === 'remote' ? remoteAccounts.value : accounts.value
    })

    const displayStats = computed(() => {
      return viewMode.value === 'remote' ? remoteStats : stats
    })

    // 格式化时间
    const formatTime = (ts) => {
      if (!ts || ts === '未设置') return '未设置'
      try {
        const date = new Date(ts)
        return date.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        })
      } catch {
        return ts
      }
    }

    // 获取状态样式
    const getStatusClass = (account) => {
      if (account.disabled) return 'warning'
      if (!account.expires_at || account.expires_at === '未设置') return 'success'
      try {
        const date = new Date(account.expires_at)
        if (date < new Date()) return 'error'
      } catch {}
      return 'success'
    }

    // 获取状态文本
    const getStatusText = (account) => {
      if (account.disabled) return '禁用'
      if (!account.expires_at || account.expires_at === '未设置') return '正常'
      try {
        const date = new Date(account.expires_at)
        if (date < new Date()) return '已过期'
      } catch {}
      return '正常'
    }

    const applyStats = (target, accountList) => {
      let active = 0
      let disabled = 0
      let expired = 0

      const now = new Date()
      accountList.forEach((acc) => {
        if (acc.disabled) {
          disabled += 1
          return
        }
        if (acc.expires_at && acc.expires_at !== '未设置') {
          try {
            const date = new Date(acc.expires_at)
            if (date < now) {
              expired += 1
              return
            }
          } catch {}
        }
        active += 1
      })

      target.total = accountList.length
      target.active = active
      target.disabled = disabled
      target.expired = expired
    }

    // 加载账号列表
    const loadLocalAccounts = async () => {
      try {
        accounts.value = await api.getAccounts()
        try {
          const statsRes = await api.getAccountStats()
          stats.total = statsRes.total
          stats.active = statsRes.active
          stats.disabled = statsRes.disabled
          stats.expired = statsRes.expired
        } catch {
          applyStats(stats, accounts.value)
        }
      } catch (e) {
        console.error('加载账号失败:', e)
        applyStats(stats, [])
      }
    }

    const loadRemoteAccounts = async () => {
      try {
        const res = await api.getRemoteAccounts()
        remoteAccounts.value = res.accounts || []
        applyStats(remoteStats, remoteAccounts.value)
        remoteError.value = ''
      } catch (e) {
        remoteAccounts.value = []
        applyStats(remoteStats, [])
        remoteError.value = e.message || '远程账号获取失败'
      }
    }

    const switchView = (mode) => {
      viewMode.value = mode
      if (mode === 'remote') {
        loadRemoteAccounts()
      } else {
        loadLocalAccounts()
      }
    }

    // 刷新账号
    const refreshAccounts = () => {
      if (viewMode.value === 'remote') {
        loadRemoteAccounts()
      } else {
        loadLocalAccounts()
      }
    }

    onMounted(() => {
      loadLocalAccounts()
    })

    return {
      viewMode,
      displayAccounts,
      displayStats,
      remoteError,
      formatTime,
      getStatusClass,
      getStatusText,
      switchView,
      refreshAccounts,
    }
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.btn-toggle.active {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.4);
  color: #fff;
}

.table-container {
  overflow-x: auto;
}

.error-state {
  padding: 12px 16px;
  margin-bottom: 12px;
  border-radius: 8px;
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
  font-size: 13px;
}

.account-id {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: monospace;
  font-size: 12px;
}

.btn-delete {
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  border-radius: 4px;
  transition: background 0.3s;
}

.btn-delete:hover {
  background: rgba(244, 67, 54, 0.2);
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.empty-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
}
</style>
