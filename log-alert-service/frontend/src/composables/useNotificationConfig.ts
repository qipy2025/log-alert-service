import { ref } from 'vue'
import axios from 'axios'

const API_BASE = '/api'

export interface NotificationConfig {
  enabled: boolean
  allowed_levels: string[]
}

export function useNotificationConfig() {
  const config = ref<NotificationConfig>({
    enabled: false,
    allowed_levels: []
  })

  const loading = ref(false)
  const updating = ref(false)
  const error = ref<string | null>(null)

  const fetchConfig = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await axios.get(`${API_BASE}/notification-config`)
      config.value = response.data
      return config.value
    } catch (e: any) {
      error.value = e.message
      console.error('获取通知配置失败:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  const updateConfig = async (newConfig: NotificationConfig) => {
    updating.value = true
    error.value = null

    try {
      const response = await axios.put(`${API_BASE}/notification-config`, newConfig)
      config.value = response.data.config || newConfig
      return config.value
    } catch (e: any) {
      error.value = e.message
      console.error('更新通知配置失败:', e)
      throw e
    } finally {
      updating.value = false
    }
  }

  return {
    config,
    loading,
    updating,
    error,
    fetchConfig,
    updateConfig
  }
}
