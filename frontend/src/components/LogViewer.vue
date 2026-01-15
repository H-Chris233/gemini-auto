<template>
  <div class="log-container" ref="logContainer">
    <div v-if="logs.length === 0" class="log-empty">
      暂无日志
    </div>
    <div v-else class="log-content">
      <div
        v-for="(log, index) in logs"
        :key="index"
        class="log-line"
      >
        <span class="time">{{ formatTime(log.timestamp) }}</span>
        <span class="level" :class="getLevelClass(log.level)">{{ log.level }}</span>
        <span class="message">{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'

export default {
  name: 'LogViewer',
  props: {
    logs: {
      type: Array,
      default: () => [],
    },
    autoScroll: {
      type: Boolean,
      default: true,
    },
  },
  setup(props) {
    const logContainer = ref(null)
    let autoScroll = true

    const formatTime = (ts) => {
      if (!ts) return ''
      const date = new Date(ts)
      return date.toLocaleTimeString('zh-CN', { hour12: false }) + '.' + String(date.getMilliseconds()).padStart(3, '0')
    }

    const getLevelClass = (level) => {
      const map = {
        'INFO': 'INFO',
        'WARN': 'WARN',
        'ERROR': 'ERROR',
        'OK': 'OK',
        '→': '→',
        '⚠': '⚠',
        '✗': '✗',
        '✓': '✓',
      }
      return map[level] || 'INFO'
    }

    const handleScroll = () => {
      if (!logContainer.value) return
      const { scrollTop, scrollHeight, clientHeight } = logContainer.value
      autoScroll = scrollHeight - scrollTop - clientHeight < 50
    }

    watch(() => props.logs.length, () => {
      if (props.autoScroll && autoScroll) {
        nextTick(() => {
          if (logContainer.value) {
            logContainer.value.scrollTop = logContainer.value.scrollHeight
          }
        })
      }
    })

    onMounted(() => {
      if (logContainer.value) {
        logContainer.value.addEventListener('scroll', handleScroll)
      }
    })

    onUnmounted(() => {
      if (logContainer.value) {
        logContainer.value.removeEventListener('scroll', handleScroll)
      }
    })

    return {
      logContainer,
      formatTime,
      getLevelClass,
    }
  }
}
</script>

<style scoped>
.log-container {
  background: #0d1117;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 16px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  max-height: 400px;
  overflow-y: auto;
}

.log-empty {
  color: #666;
  text-align: center;
  padding: 40px;
}

.log-line {
  margin-bottom: 4px;
  line-height: 1.6;
}

.log-line .time {
  color: #666;
  margin-right: 8px;
}

.log-line .level {
  display: inline-block;
  width: 50px;
  margin-right: 8px;
  font-weight: 500;
}

.log-line .level.INFO { color: #2196f3; }
.log-line .level.WARN { color: #ffc107; }
.log-line .level.ERROR { color: #f44336; }
.log-line .level.OK { color: #4caf50; }
.log-line .level.→ { color: #2196f3; }
.log-line .level.⚠ { color: #ffc107; }
.log-line .level.✗ { color: #f44336; }
.log-line .level.✓ { color: #4caf50; }

.log-line .message {
  color: #e4e4e4;
}
</style>
