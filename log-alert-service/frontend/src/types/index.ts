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

// 设备配置类型（用于设备管理）
export interface DeviceConfig {
  device_name: string        // 设备名称
  log_path: string          // 日志路径
  auto_notify: boolean      // 是否自动通知（只读）
  polling_interval: number  // 轮询间隔（只读）
  encoding: string         // 编码（只读）
  enabled: boolean          // 是否启用
  created_at?: string       // 创建时间（可选）
}

// 设备表单数据类型（用于添加/编辑）
export interface DeviceFormData {
  device_name: string
  log_path: string
  enabled: boolean
}

// API 响应类型
export interface DevicesResponse {
  devices: DeviceConfig[]
}

export interface DeviceOperationResponse {
  success: boolean
  device?: DeviceConfig
  message?: string
}

export interface ApiError {
  error: string
}
