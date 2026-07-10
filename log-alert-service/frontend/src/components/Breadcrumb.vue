<template>
  <el-breadcrumb separator="/">
    <el-breadcrumb-item :to="{ path: '/' }">
      <el-icon><HomeFilled /></el-icon>
    </el-breadcrumb-item>
    <el-breadcrumb-item>{{ currentPage }}</el-breadcrumb-item>
  </el-breadcrumb>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { HomeFilled } from '@element-plus/icons-vue'

interface Props {
  currentPage: string
}

const props = defineProps<Props>()

const currentPage = computed(() => {
  const pages: Record<string, string> = {
    monitoring: '设备监控',
    notification: '通知配置',
    devices: '设备管理',
    history: '历史数据'
  }
  return pages[props.currentPage] || props.currentPage
})
</script>

<style scoped>
.el-breadcrumb {
  margin-bottom: 20px;
  font-size: 14px;
}

:deep(.el-breadcrumb__item) {
  font-weight: 500;
}

:deep(.el-breadcrumb__inner) {
  color: #606266;
}

:deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: #303133;
  font-weight: 600;
}

:deep(.el-breadcrumb__icon) {
  font-size: 16px;
}
</style>
