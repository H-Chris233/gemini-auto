const API_BASE = '/api'

// API 客户端封装
export const api = {
  // 健康检查
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`)
    return res.json()
  },

  // 获取配置
  async getConfig() {
    const res = await fetch(`${API_BASE}/config`)
    return res.json()
  },

  // ========== 任务相关 ==========

  // 创建任务
  async createTask(count, uploadMode = 'merge', scheduleOptions = null) {
    const payload = { count, upload_mode: uploadMode }
    if (scheduleOptions) {
      payload.schedule_enabled = scheduleOptions.scheduleEnabled
      payload.interval_hours = scheduleOptions.intervalHours
      payload.run_now = scheduleOptions.runNow
    }
    const res = await fetch(`${API_BASE}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error('创建任务失败')
    return res.json()
  },

  // 查询任务状态
  async getTask(taskId) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}`)
    if (!res.ok) throw new Error('任务不存在')
    return res.json()
  },

  // 停止任务
  async stopTask(taskId) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('停止任务失败')
    return res.json()
  },

  // 获取任务日志 (SSE)
  subscribeLogs(taskId, onMessage) {
    const eventSource = new EventSource(`${API_BASE}/tasks/${taskId}/logs`)

    eventSource.addEventListener('log', (e) => {
      const data = JSON.parse(e.data)
      onMessage(data)
    })

    eventSource.addEventListener('status', (e) => {
      onMessage({ type: 'status', status: e.data })
    })

    eventSource.onerror = () => {
      console.log('日志连接断开')
      eventSource.close()
    }

    return eventSource
  },

  // ========== 账号相关 ==========

  // 获取账号列表
  async getAccounts() {
    const res = await fetch(`${API_BASE}/accounts`)
    return res.json()
  },

  // 获取账号统计
  async getAccountStats() {
    const res = await fetch(`${API_BASE}/accounts/stats`)
    return res.json()
  },

  // 获取远程账号列表
  async getRemoteAccounts() {
    const res = await fetch(`${API_BASE}/accounts/remote`)
    if (!res.ok) throw new Error('远程账号获取失败')
    return res.json()
  },
}

// 工具函数
export function formatTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatDuration(seconds) {
  if (!seconds) return '0s'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}
