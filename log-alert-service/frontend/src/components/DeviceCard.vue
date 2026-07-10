<template>
  <div class="device-card">
    <div class="status-indicator" :class="statusClass"></div>
    <h3>{{ device.name }}</h3>
    <p>状态: {{ statusText }}</p>
    <p>今日告警: {{ device.today_alarm_count }}</p>
    <p v-if="device.last_heartbeat">最后心跳: {{ formatTime(device.last_heartbeat) }}</p>

    <el-button
      @click="handleToggle"
      :type="buttonType"
      :loading="loading"
      style="margin-top: 12px; width: 100%"
    >
      {{ buttonText }}
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { Device } from '../types'
import { useDevices } from '../composables/useDevices'

const props = defineProps<{
  device: Device
}>()

const emit = defineEmits<{
  (e: 'statusChanged', device: Device): void
}>()

const { startDevice, pauseDevice } = useDevices()
const loading = ref(false)

const statusClass = computed(() => {
  return props.device.status === 'RUNNING' ? 'status-running' : 'status-paused'
})

const statusText = computed(() => {
  return props.device.status === 'RUNNING' ? '● 运行中' : '○ 已暂停'
})

const buttonType = computed(() => {
  return props.device.status === 'RUNNING' ? 'warning' : 'success'
})

const buttonText = computed(() => {
  return props.device.status === 'RUNNING' ? '暂停' : '启动'
})

const formatTime = (time: string) => {
  if (!time) return '-'
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

const handleToggle = async () => {
  const action = props.device.status === 'RUNNING' ? 'pause' : 'start'
  const actionText = action === 'pause' ? '暂停' : '启动'

  loading.value = true

  try {
    if (action === 'pause') {
      await pauseDevice(props.device.name, '用户手动操作')
      ElMessage.success(`${props.device.name} 已暂停`)
    } else {
      await startDevice(props.device.name, '用户手动操作')
      ElMessage.success(`${props.device.name} 已启动`)
    }

    emit('statusChanged', props.device)
  } catch (error: any) {
    ElMessage.error(`${actionText}失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.device-card h3 {
  margin: 12px 0;
  font-size: 18px;
  color: #333;
}

.device-card p {
  margin: 8px 0;
  color: #666;
  font-size: 14px;
}
</style>
