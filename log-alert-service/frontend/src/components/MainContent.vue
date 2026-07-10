<template>
  <div class="main-content">
    <breadcrumb :current-page="currentPage" />

    <div class="content-area">
      <!-- 设备监控页面 -->
      <div v-show="currentPage === 'monitoring'" class="page-view">
        <notification-config />
        <div class="devices-section">
          <div class="section-header">
            <h2>设备状态</h2>
            <span class="device-count">{{ devices.length }} 个设备</span>
          </div>
          <div class="device-grid">
            <device-card
              v-for="device in devices"
              :key="device.name"
              :device="device"
              @status-changed="handleStatusChanged"
            />
          </div>
        </div>
        <div class="alarms-section">
          <alarm-list />
        </div>
      </div>

      <!-- 通知配置页面 -->
      <div v-show="currentPage === 'notification'" class="page-view">
        <div class="full-page-config">
          <div class="config-header-page">
            <h2>通知配置管理</h2>
            <p class="description">配置飞书告警通知的开关和级别过滤</p>
          </div>
          <notification-config />
        </div>
      </div>

      <!-- 设备管理页面 -->
      <div v-show="currentPage === 'devices'" class="page-view">
        <div class="devices-management">
          <h2>设备管理</h2>
          <el-alert
            title="设备管理功能"
            type="info"
            :closable="false"
            show-icon
          >
            这里可以添加、删除和配置设备。该功能正在开发中...
          </el-alert>
        </div>
      </div>

      <!-- 历史数据页面 -->
      <div v-show="currentPage === 'history'" class="page-view">
        <div class="history-data">
          <h2>历史数据</h2>
          <el-alert
            title="历史告警记录"
            type="info"
            :closable="false"
            show-icon
          >
            这里可以查看历史告警记录和统计分析。该功能正在开发中...
          </el-alert>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import DeviceCard from './DeviceCard.vue'
import AlarmList from './AlarmList.vue'
import NotificationConfig from './NotificationConfig.vue'
import Breadcrumb from './Breadcrumb.vue'
import { useDevices } from '../composables/useDevices'
import { useWebSocket } from '../composables/useWebSocket'
import type { Device } from '../types'

interface Props {
  currentPage: string
}

const props = defineProps<Props>()

const { devices, fetchDevices } = useDevices()
const { connected } = useWebSocket()

const loadDevices = async () => {
  await fetchDevices()
}

const handleStatusChanged = (device: Device) => {
  console.log('设备状态变更:', device)
}

onMounted(() => {
  if (props.currentPage === 'monitoring') {
    loadDevices()
  }
})

// 监听设备状态变更事件
window.addEventListener('device-status-changed', ((event: CustomEvent) => {
  if (props.currentPage === 'monitoring') {
    loadDevices()
  }
}) as EventListener)
</script>

<style scoped>
.main-content {
  flex: 1;
  padding: 24px;
  margin-left: 200px;
  transition: margin-left 0.3s ease;
  max-width: calc(100% - 200px);
}

.page-view {
  min-height: 400px;
}

.devices-section {
  margin: 24px 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 0 4px;
}

.section-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #2c3e50;
}

.device-count {
  font-size: 14px;
  color: #7f8c8d;
  background: white;
  padding: 6px 14px;
  border-radius: 16px;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.alarms-section {
  margin-top: 24px;
}

.full-page-config {
  max-width: 900px;
  margin: 0 auto;
}

.config-header-page {
  margin-bottom: 24px;
  text-align: center;
}

.config-header-page h2 {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 600;
  color: #2c3e50;
}

.config-header-page .description {
  margin: 0;
  font-size: 16px;
  color: #7f8c8d;
}

.devices-management,
.history-data {
  max-width: 900px;
  margin: 0 auto;
}

.devices-management h2,
.history-data h2 {
  margin: 0 0 20px 0;
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .main-content {
    margin-left: 64px;
    max-width: calc(100% - 64px);
    padding: 16px;
  }

  .device-grid {
    grid-template-columns: 1fr;
  }

  .full-page-config,
  .devices-management,
  .history-data {
    margin: 0 auto;
  }
}

/* 侧边栏折叠状态 */
@media (min-width: 769px) {
  .main-content.collapsed {
    margin-left: 64px;
    max-width: calc(100% - 64px);
  }
}
</style>
