<template>
  <div id="app">
    <el-container>
      <el-header style="background-color: #409eff; color: white; display: flex; align-items: center; justify-content: space-between;">
        <h2 style="margin: 0;">设备监控平台</h2>
        <div style="display: flex; align-items: center; gap: 16px;">
          <span style="font-size: 14px;">WebSocket: {{ connected ? '已连接' : '未连接' }}</span>
          <el-button @click="loadDevices" size="small" type="primary">
            刷新设备
          </el-button>
        </div>
      </el-header>

      <el-main style="padding: 20px;">
        <!-- 设备状态卡片 -->
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px; margin-bottom: 24px;">
          <device-card
            v-for="device in devices"
            :key="device.name"
            :device="device"
            @status-changed="handleStatusChanged"
          />
        </div>

        <!-- 告警列表 -->
        <alarm-list />
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import DeviceCard from './components/DeviceCard.vue'
import AlarmList from './components/AlarmList.vue'
import { useDevices } from './composables/useDevices'
import { useWebSocket } from './composables/useWebSocket'
import type { Device } from './types'

const { devices, loading: devicesLoading, fetchDevices } = useDevices()
const { connected } = useWebSocket()

const loadDevices = async () => {
  await fetchDevices()
}

const handleStatusChanged = (device: Device) => {
  console.log('设备状态变更:', device)
}

// 监听设备状态变更事件
window.addEventListener('device-status-changed', ((event: CustomEvent) => {
  const data = event.detail
  // 刷新设备列表
  loadDevices()
}) as EventListener)

onMounted(() => {
  loadDevices()
})
</script>
