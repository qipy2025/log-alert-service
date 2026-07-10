import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import type { DeviceConfig, DeviceFormData } from '../types'

const API_BASE = '/api'

export function useDeviceManagement() {
  const devices = ref<DeviceConfig[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 获取设备配置列表
  const fetchDevices = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await axios.get<{devices: DeviceConfig[]}>(`${API_BASE}/devices/config`)
      devices.value = response.data.devices
    } catch (e: any) {
      error.value = e.message
      ElMessage.error('获取设备列表失败')
      console.error('获取设备列表失败:', e)
    } finally {
      loading.value = false
    }
  }

  // 添加设备
  const addDevice = async (formData: DeviceFormData): Promise<boolean> => {
    loading.value = true
    try {
      const response = await axios.post<{success: boolean; device: DeviceConfig}>(
        `${API_BASE}/devices`,
        formData
      )

      if (response.data.success) {
        ElMessage.success('设备已添加')
        await fetchDevices() // 刷新列表
        return true
      }
      return false
    } catch (e: any) {
      handleApiError(e)
      return false
    } finally {
      loading.value = false
    }
  }

  // 更新设备
  const updateDevice = async (deviceName: string, formData: DeviceFormData): Promise<boolean> => {
    loading.value = true
    try {
      const response = await axios.put<{success: boolean; device: DeviceConfig}>(
        `${API_BASE}/devices/${encodeURIComponent(deviceName)}`,
        formData
      )

      if (response.data.success) {
        ElMessage.success('设备已更新')
        await fetchDevices() // 刷新列表
        return true
      }
      return false
    } catch (e: any) {
      handleApiError(e)
      return false
    } finally {
      loading.value = false
    }
  }

  // 删除设备
  const deleteDevice = async (device: DeviceConfig): Promise<boolean> => {
    return new Promise((resolve) => {
      ElMessageBox.confirm(
        `确定要删除设备"${device.device_name}"吗？历史告警记录将被保留。`,
        '删除确认',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(async () => {
        loading.value = true
        try {
          const response = await axios.delete<{success: boolean; message: string}>(
            `${API_BASE}/devices/${encodeURIComponent(device.device_name)}`
          )

          if (response.data.success) {
            ElMessage.success('设备已删除')
            await fetchDevices() // 刷新列表
            resolve(true)
          } else {
            resolve(false)
          }
        } catch (e: any) {
          handleApiError(e)
          resolve(false)
        } finally {
          loading.value = false
        }
      }).catch(() => {
        // 用户取消删除
        resolve(false)
      })
    })
  }

  // API 错误处理
  const handleApiError = (error: any) => {
    if (error.response) {
      const status = error.response.status
      const data = error.response.data

      if (status === 409) {
        ElMessage.error(data.error || '设备名称已存在')
      } else if (status === 404) {
        ElMessage.error(data.error || '设备不存在')
      } else if (status === 400) {
        ElMessage.error(data.error || '请求参数错误')
      } else {
        ElMessage.error('操作失败，请稍后重试')
      }
    } else {
      ElMessage.error('网络错误，请检查连接')
    }
  }

  return {
    devices,
    loading,
    error,
    fetchDevices,
    addDevice,
    updateDevice,
    deleteDevice
  }
}
