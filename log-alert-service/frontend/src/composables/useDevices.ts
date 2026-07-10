import { ref } from 'vue'
import axios from 'axios'
import type { Device } from '../types'

const API_BASE = '/api'

export function useDevices() {
  const devices = ref<Device[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const fetchDevices = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await axios.get(`${API_BASE}/devices`)
      devices.value = response.data.devices
    } catch (e: any) {
      error.value = e.message
      console.error('获取设备列表失败:', e)
    } finally {
      loading.value = false
    }
  }

  const startDevice = async (deviceName: string, reason: string = '手动启动') => {
    try {
      await axios.post(`${API_BASE}/devices/${deviceName}/start`, { reason })
      await fetchDevices() // 刷新列表
    } catch (e: any) {
      console.error('启动设备失败:', e)
      throw e
    }
  }

  const pauseDevice = async (deviceName: string, reason: string = '手动暂停') => {
    try {
      await axios.post(`${API_BASE}/devices/${deviceName}/pause`, { reason })
      await fetchDevices() // 刷新列表
    } catch (e: any) {
      console.error('暂停设备失败:', e)
      throw e
    }
  }

  return {
    devices,
    loading,
    error,
    fetchDevices,
    startDevice,
    pauseDevice
  }
}
