<template>
  <div class="dashboard">
    <!-- 任务控制卡片 -->
    <div class="card">
      <h2 class="card-title">
        <span>🚀</span>
        任务控制台
      </h2>

      <!-- 配置表单 -->
      <div class="task-config">
        <div class="config-section">
          <h3 class="section-title">📝 任务配置</h3>
          <div class="config-row">
            <div class="input-group">
              <label>注册数量</label>
              <input
                type="number"
                class="form-input"
                v-model.number="taskConfig.count"
                min="1"
                max="100"
                :disabled="currentTaskId !== null"
              />
            </div>

          </div>
        </div>

        <div class="task-actions">
          <button
            class="btn btn-primary btn-lg"
            @click="startTask"
            :disabled="currentTaskId !== null || !isReady"
          >
            {{ currentTaskId ? '⏳ 任务运行中...' : '🚀 开始注册' }}
          </button>

          <button
            class="btn btn-danger"
            @click="stopTask"
            :disabled="currentTaskId === null"
          >
            ⏹️ 停止任务
          </button>
        </div>
      </div>

      <!-- 统计信息 -->
      <div class="stat-grid" v-if="taskProgress">
        <StatusCard
          :value="taskProgress.success"
          label="成功"
          color="#4caf50"
        />
        <StatusCard
          :value="taskProgress.fail"
          label="失败"
          color="#f44336"
        />
        <StatusCard
          :value="formatDuration(taskProgress.totalTime)"
          label="总耗时"
          color="#ff9800"
        />
        <StatusCard
          :value="taskProgress.avgTime > 0 ? taskProgress.avgTime.toFixed(1) + 's' : '-'"
          label="平均用时"
          color="#2196f3"
        />
      </div>

      <!-- 任务状态 -->
      <div class="task-status" v-if="currentTaskId">
        <span class="status-badge running">任务运行中</span>
        <span class="task-id">ID: {{ currentTaskId }}</span>
      </div>
    </div>

    <!-- 日志卡片 -->
    <div class="card">
      <h2 class="card-title">
        <span>📋</span>
        实时日志
        <button class="btn btn-secondary" style="margin-left: auto; padding: 6px 12px; font-size: 12px;" @click="clearLogs">
          清空日志
        </button>
      </h2>

      <LogViewer :logs="logs" :auto-scroll="true" />
    </div>

    <!-- 配置状态卡片 -->
    <div class="card">
      <h2 class="card-title">
        <span>⚙️</span>
        环境状态
      </h2>

      <div class="status-grid">
        <div class="status-item">
          <span class="status-label">Headless 模式</span>
          <span class="status-value" :class="{ active: config.headlessMode }">
            {{ config.headlessMode ? '已启用' : '已禁用' }}
          </span>
        </div>
        <div class="status-item">
          <span class="status-label">邮箱 API</span>
          <span class="status-value" :class="{ active: config.mailKeySet }">
            {{ config.mailKeySet ? '已配置' : '未配置' }}
          </span>
        </div>
        <div class="status-item">
          <span class="status-label">自动上传</span>
          <span class="status-value" :class="{ active: config.uploadApiHostSet }">
            {{ config.uploadApiHostSet ? '已配置' : '未配置' }}
          </span>
        </div>
        <div class="status-item">
          <span class="status-label">上传模式</span>
          <span class="status-value">{{ config.uploadMode === 'merge' ? '合并' : '覆盖' }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">版本</span>
          <span class="status-value">{{ config.version || '-' }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">运行时间</span>
          <span class="status-value">{{ formatUptime(uptime) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { api, formatDuration } from '../api'
import StatusCard from '../components/StatusCard.vue'
import LogViewer from '../components/LogViewer.vue'

export default {
  name: 'Dashboard',
  components: {
    StatusCard,
    LogViewer,
  },
  setup() {
    // 任务配置
    const taskConfig = reactive({
      count: 5,
    })

    // 任务状态
    const currentTaskId = ref(null)
    const taskProgress = ref(null)
    const logs = ref([])
    const logSource = ref(null)

    // 配置信息
    const config = reactive({
      headlessMode: true,
      mailKeySet: false,
      version: '',
      uploadApiHostSet: false,
      uploadMode: 'merge',
    })

    // 服务运行时间
    const uptime = ref(0)
    let uptimeInterval = null

    // 是否就绪
    const isReady = computed(() => {
      return config.mailKeySet || config.headlessMode !== undefined
    })

    // 格式化运行时间
    const formatUptime = (seconds) => {
      if (!seconds) return '-'
      const h = Math.floor(seconds / 3600)
      const m = Math.floor((seconds % 3600) / 60)
      const s = Math.floor(seconds % 60)
      if (h > 0) return `${h}h ${m}m ${s}s`
      if (m > 0) return `${m}m ${s}s`
      return `${s}s`
    }

    // 加载配置
    const loadConfig = async () => {
      try {
        const res = await api.getConfig()
        config.headlessMode = res.headless_mode
        config.mail_api = res.mail_api
        config.mail_key_set = res.mail_key_set
        config.version = res.version
        config.uploadApiHostSet = res.upload_api_host_set
        config.uploadMode = res.upload_mode
      } catch (e) {
        console.error('加载配置失败:', e)
      }
    }

    // 开始任务
    const startTask = async () => {
      try {
        logs.value = []
        const res = await api.createTask(taskConfig.count)
        currentTaskId.value = res.id
        taskProgress.value = { success: 0, fail: 0, totalTime: 0, avgTime: 0 }
        logs.value.push({
          timestamp: new Date().toISOString(),
          level: 'INFO',
          message: `任务已启动，目标注册 ${taskConfig.count} 个账号`,
        })

        // 订阅日志
        logSource.value = api.subscribeLogs(res.id, (data) => {
          if (data.type === 'status') {
            // 任务结束
            if (data.status === 'completed' || data.status === 'failed') {
              currentTaskId.value = null
              updateTaskStatus(res.id)
            }
          } else {
            logs.value.push(data)
          }
        })

        // 定期更新任务状态
        updateTaskStatus(res.id)

      } catch (e) {
        logs.value.push({
          timestamp: new Date().toISOString(),
          level: 'ERROR',
          message: `启动任务失败: ${e.message}`,
        })
      }
    }

    // 停止任务
    const stopTask = async () => {
      if (!currentTaskId.value) return

      try {
        await api.stopTask(currentTaskId.value)
        if (logSource.value) {
          logSource.value.close()
          logSource.value = null
        }
        logs.value.push({
          timestamp: new Date().toISOString(),
          level: 'WARN',
          message: '任务已手动停止',
        })
        currentTaskId.value = null
      } catch (e) {
        logs.value.push({
          timestamp: new Date().toISOString(),
          level: 'ERROR',
          message: `停止任务失败: ${e.message}`,
        })
      }
    }

    // 更新任务状态
    const updateTaskStatus = async (taskId) => {
      if (!taskId || currentTaskId.value !== taskId) return

      try {
        const res = await api.getTask(taskId)
        taskProgress.value = {
          success: res.success_count,
          fail: res.fail_count,
          totalTime: res.total_time,
          avgTime: res.avg_time,
        }

        // 继续轮询直到任务结束
        if (res.status !== 'running') {
          currentTaskId.value = null
          if (logSource.value) {
            logSource.value.close()
            logSource.value = null
          }
        } else {
          setTimeout(() => updateTaskStatus(taskId), 2000)
        }
      } catch (e) {
        console.error('获取任务状态失败:', e)
      }
    }

    // 清空日志
    const clearLogs = () => {
      logs.value = []
    }

    onMounted(() => {
      loadConfig()

      // 启动运行时间计时
      const startTime = Date.now()
      uptimeInterval = setInterval(() => {
        uptime.value = (Date.now() - startTime) / 1000
      }, 1000)
    })

    onUnmounted(() => {
      if (logSource.value) {
        logSource.value.close()
      }
      if (uptimeInterval) {
        clearInterval(uptimeInterval)
      }
    })

    return {
      taskConfig,
      currentTaskId,
      taskProgress,
      logs,
      config,
      uptime,
      isReady,
      formatDuration,
      formatUptime,
      startTask,
      stopTask,
      clearLogs,
    }
  }
}
</script>

<style scoped>
.task-config {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 20px;
}

.config-section {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  padding: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #888;
  margin-bottom: 12px;
}

.config-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.task-actions {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  padding-top: 8px;
}

.btn-lg {
  padding: 12px 32px;
  font-size: 16px;
}

.task-status {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.task-id {
  font-family: monospace;
  font-size: 12px;
  color: #888;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.status-label {
  color: #888;
  font-size: 14px;
}

.status-value {
  font-weight: 500;
  color: #666;
}

.status-value.active {
  color: #4caf50;
}
</style>
