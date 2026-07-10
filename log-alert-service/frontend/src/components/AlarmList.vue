<template>
  <div class="alarm-list">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <h3>告警列表</h3>
      <el-button @click="loadAlarms" :loading="loading" size="small">
        刷新
      </el-button>
    </div>

    <el-table :data="displayAlarms" stripe style="width: 100%">
      <el-table-column prop="log_timestamp" label="时间" width="180">
        <template #default="{ row }">
          {{ formatTime(row.log_timestamp) }}
        </template>
      </el-table-column>

      <el-table-column prop="device_name" label="设备" width="120" />

      <el-table-column prop="alarm_level" label="级别" width="100">
        <template #default="{ row }">
          <el-tag :type="getLevelType(row.alarm_level)">
            {{ row.alarm_level }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="alarm_content" label="内容">
        <template #default="{ row }">
          <div class="alarm-content">{{ row.alarm_content }}</div>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button
            v-if="row.ai_analysis"
            type="primary"
            size="small"
            link
            @click="showAnalysis(row)"
          >
            查看分析
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > 0"
      style="margin-top: 16px; justify-content: center"
      layout="prev, pager, next"
      :total="total"
      :page-size="limit"
      :current-page="currentPage"
      @current-change="handlePageChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import type { Alarm } from '../types'
import { useAlarms } from '../composables/useAlarms'

const { alarms, total, loading, fetchAlarms } = useAlarms()

const limit = 10
const currentPage = ref(1)
const displayAlarms = computed(() => alarms.value.slice(0, limit))

const formatTime = (time: string) => {
  if (!time) return '-'
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

const getLevelType = (level: string) => {
  const types: Record<string, any> = {
    'CRITICAL': 'danger',
    'ERROR': 'warning',
    'WARNING': 'info',
    'INFO': 'info'
  }
  return types[level] || 'info'
}

const showAnalysis = (alarm: Alarm) => {
  ElMessageBox.alert(alarm.ai_analysis || '暂无分析', 'AI分析结果', {
    confirmButtonText: '关闭',
    type: 'info'
  })
}

const loadAlarms = async () => {
  await fetchAlarms({ limit, offset: (currentPage.value - 1) * limit })
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  loadAlarms()
}

onMounted(() => {
  loadAlarms()
})

// 监听新告警事件
window.addEventListener('new-alarm', ((event: CustomEvent) => {
  const newAlarm = event.detail
  alarms.value.unshift(newAlarm)
  if (alarms.value.length > limit) {
    alarms.value.pop()
  }
}) as EventListener)
</script>
