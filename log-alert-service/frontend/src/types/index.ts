export interface Device {
  name: string
  status: 'RUNNING' | 'PAUSED'
  last_heartbeat: string | null
  last_alarm_time: string | null
  today_alarm_count: number
  enabled: boolean
}

export interface Alarm {
  id: number
  device_name: string
  alarm_level: string
  alarm_content: string
  ai_analysis: string | null
  log_timestamp: string
  created_at: string
}

export interface AlarmSummary {
  date: string
  device: string
  total: number
  by_level: Record<string, number>
  peak_hour: string | null
}

export interface WebSocketMessage {
  type: 'alarm' | 'device_status_changed'
  data: any
}
