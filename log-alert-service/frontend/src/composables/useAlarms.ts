import { ref } from 'vue'
import axios from 'axios'
import type { Alarm, AlarmSummary } from '../types'

const API_BASE = '/api'

export function useAlarms() {
  const alarms = ref<Alarm[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const fetchAlarms = async (params: {
    device?: string
    level?: string
    limit?: number
    offset?: number
  } = {}) => {
    loading.value = true
    error.value = null

    try {
      const response = await axios.get(`${API_BASE}/alarms`, { params })
      alarms.value = response.data.alarms
      total.value = response.data.total
    } catch (e: any) {
      error.value = e.message
      console.error('获取告警列表失败:', e)
    } finally {
      loading.value = false
    }
  }

  const fetchAlarmSummary = async (device?: string, date?: string) => {
    try {
      const params: any = {}
      if (device) params.device = device
      if (date) params.date = date

      const response = await axios.get(`${API_BASE}/alarms/summary`, { params })
      return response.data as AlarmSummary
    } catch (e: any) {
      console.error('获取告警统计失败:', e)
      throw e
    }
  }

  return {
    alarms,
    total,
    loading,
    error,
    fetchAlarms,
    fetchAlarmSummary
  }
}
