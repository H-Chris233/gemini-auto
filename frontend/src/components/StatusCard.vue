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
