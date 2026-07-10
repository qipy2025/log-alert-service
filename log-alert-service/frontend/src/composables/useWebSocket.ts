import { ref, onMounted, onUnmounted } from 'vue'
import { io, Socket } from 'socket.io-client'
import type { WebSocketMessage } from '../types'
import { ElNotification } from 'element-plus'

export function useWebSocket() {
  const socket = ref<Socket | null>(null)
  const connected = ref(false)

  const connect = () => {
    // 使用Socket.IO客户端
    socket.value = io('ws://localhost:5000', {
      transports: ['websocket', 'polling']
    })

    socket.value.on('connect', () => {
      console.log('WebSocket已连接')
      connected.value = true
    })

    socket.value.on('disconnect', () => {
      console.log('WebSocket已断开')
      connected.value = false
    })

    socket.value.on('alarm', (message: WebSocketMessage) => {
      if (message.type === 'alarm') {
        const alarm = message.data

        // 显示通知
        ElNotification({
          title: `${alarm.device_name} 告警`,
          message: alarm.alarm_content,
          type: 'error',
          duration: 5000
        })

        // 触发自定义事件，让组件知道有新告警
        window.dispatchEvent(new CustomEvent('new-alarm', { detail: alarm }))
      }
    })

    socket.value.on('device_status_changed', (message: WebSocketMessage) => {
      if (message.type === 'device_status_changed') {
        const data = message.data

        // 显示通知
        ElNotification({
          title: `${data.device_name} 状态变更`,
          message: `${data.old_status} → ${data.new_status}`,
          type: 'info',
          duration: 3000
        })

        // 触发自定义事件
        window.dispatchEvent(new CustomEvent('device-status-changed', { detail: data }))
      }
    })

    socket.value.on('error', (error: any) => {
      console.error('WebSocket错误:', error)
    })
  }

  const disconnect = () => {
    if (socket.value) {
      socket.value.disconnect()
      socket.value = null
      connected.value = false
    }
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    connect,
    disconnect
  }
}
