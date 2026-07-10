<template>
  <div class="alarm-list">
    <div class="list-header">
      <div class="header-content">
        <h3>告警列表</h3>
        <p class="subtitle">实时监控设备告警信息</p>
      </div>
      <el-button @click="loadAlarms" :loading="loading" :icon="Refresh">
        刷新
      </el-button>
    </div>

    <el-card shadow="hover" class="table-card">
      <el-table
        :data="displayAlarms"
        stripe
        style="width: 100%"
        :empty-text="emptyText"
        class="alarm-table"
      >
        <el-table-column prop="log_timestamp" label="时间" width="180">
          <template #default="{ row }">
            <div class="time-cell">
              <el-icon><Clock /></el-icon>
              {{ formatTime(row.log_timestamp) }}
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="device_name" label="设备" width="140">
          <template #default="{ row }">
            <el-tag type="info" size="small" effect="plain">
              {{ row.device_name }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="alarm_level" label="级别" width="120">
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.alarm_level)" effect="dark" size="small">
              {{ row.alarm_level }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="alarm_content" label="内容">
          <template #default="{ row }">
            <div class="content-cell">
              {{ row.alarm_content }}
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="100" fixed="right">
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
            <el-tag v-else type="info" size="small" effect="plain">
              待分析
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > 0"
        class="pagination"
        layout="prev, pager, next, total"
        :total="total"
        :page-size="limit"
        :current-page="currentPage"
        @current-change="handlePageChange"
        small
        background
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Clock, Refresh } from '@element-plus/icons-vue'
import type { Alarm } from '../types'
import { useAlarms } from '../composables/useAlarms'

const { alarms, total, loading, fetchAlarms } = useAlarms()

const limit = 10
const currentPage = ref(1)
const displayAlarms = computed(() => alarms.value.slice(0, limit))

const emptyText = computed(() => {
  return loading.value ? '加载中...' : '暂无告警记录'
})

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

<style scoped>
.alarm-list {
  margin-top: 24px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  padding: 0 4px;
}

.header-content h3 {
  margin: 0 0 4px 0;
  font-size: 20px;
  font-weight: 600;
  color: #2c3e50;
}

.subtitle {
  margin: 0;
  font-size: 14px;
  color: #7f8c8d;
  font-weight: 400;
}

.table-card {
  border-radius: 12px;
  border: 1px solid #e4e7ed;
}

.alarm-table {
  border-radius: 8px;
}

.time-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
  font-family: 'Consolas', monospace;
}

.content-cell {
  max-width: 500px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #2c3e50;
}

.pagination {
  margin-top: 20px;
  justify-content: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .list-header {
    flex-direction: column;
    gap: 12px;
  }

  .alarm-table {
    font-size: 12px;
  }

  .content-cell {
    max-width: 200px;
  }
}
</style>
