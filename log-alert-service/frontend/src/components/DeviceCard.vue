<template>
  <div class="device-card" :class="`device-card-${statusClass}`">
    <div class="card-header">
      <div class="status-indicator" :class="statusClass">
        <div class="indicator-dot"></div>
      </div>
      <h3>{{ device.name }}</h3>
    </div>

    <div class="card-body">
      <div class="info-row">
        <span class="info-label">状态：</span>
        <span class="info-value" :class="`status-${statusClass}`">
          {{ statusText }}
        </span>
      </div>

      <div class="info-row">
        <span class="info-label">今日告警：</span>
        <span class="info-value alarm-count">
          <el-tag :type="device.today_alarm_count > 0 ? 'danger' : 'success'" size="small">
            {{ device.today_alarm_count }}
          </el-tag>
        </span>
      </div>

      <div class="info-row" v-if="device.last_heartbeat">
        <span class="info-label">最后心跳：</span>
        <span class="info-value time">{{ formatTime(device.last_heartbeat) }}</span>
      </div>
    </div>

    <div class="card-footer">
      <el-button
        @click="handleToggle"
        :type="buttonType"
        :loading="loading"
        size="large"
        :icon="buttonIcon"
        class="action-button"
      >
        {{ buttonText }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, VideoPause } from '@element-plus/icons-vue'
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
  return props.device.status === 'RUNNING' ? '暂停设备' : '启动设备'
})

const buttonIcon = computed(() => {
  return props.device.status === 'RUNNING' ? VideoPause : VideoPlay
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
.device-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  border: 1px solid #e4e7ed;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.device-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.device-card-status-running {
  border-left: 4px solid #67f233;
}

.device-card-status-paused {
  border-left: 4px solid #909399;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.status-indicator {
  position: relative;
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.indicator-dot {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.1);
  }
}

.status-running {
  color: #67f233;
}

.status-paused {
  color: #909399;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  flex: 1;
}

.card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
}

.info-label {
  font-size: 14px;
  color: #7f8c8d;
  font-weight: 500;
}

.info-value {
  font-size: 14px;
  color: #2c3e50;
  font-weight: 600;
}

.status-running {
  color: #67f233;
}

.status-paused {
  color: #909399;
}

.alarm-count .el-tag {
  font-weight: 600;
}

.time {
  font-size: 13px;
  font-family: 'Consolas', monospace;
}

.card-footer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.action-button {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .device-card {
    padding: 16px;
  }

  .card-header h3 {
    font-size: 16px;
  }

  .action-button {
    height: 40px;
    font-size: 14px;
  }
}
</style>
