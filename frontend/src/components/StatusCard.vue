<template>
  <div class="stat-item">
    <div class="stat-value" :style="{ color: color }">{{ value }}</div>
    <div class="stat-label">{{ label }}</div>
  </div>
</template>

<script>
export default {
  name: 'StatusCard',
  props: {
    value: [String, Number],
    label: String,
    color: {
      type: String,
      default: '#667eea',
    },
  },
}
</script>

<style scoped>
.stat-item {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
  transition: all 0.3s ease;
}

.stat-item:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-2px);
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: v-bind(color);
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
</style>
