<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <div class="logo-section">
        <el-icon class="logo-icon" :size="24"><Monitor /></el-icon>
        <span class="logo-text">监控平台</span>
      </div>
    </div>

    <el-menu
      :default-active="activeMenu"
      class="sidebar-menu"
      @select="handleSelect"
      :collapse="isCollapsed"
      :collapse-transition="false"
    >
      <el-menu-item index="monitoring">
        <template #title>
          <el-icon><Monitor /></el-icon>
          <span>设备监控</span>
        </template>
      </el-menu-item>

      <el-menu-item index="notification">
        <template #title>
          <el-icon><Bell /></el-icon>
          <span>通知配置</span>
        </template>
      </el-menu-item>

      <el-menu-item index="devices">
        <template #title>
          <el-icon><Setting /></el-icon>
          <span>设备管理</span>
        </template>
      </el-menu-item>

      <el-menu-item index="history">
        <template #title>
          <el-icon><DataLine /></el-icon>
          <span>历史数据</span>
        </template>
      </el-menu-item>
    </el-menu>

    <div class="sidebar-footer">
      <el-tooltip
        :content="isCollapsed ? '展开导航' : '收起导航'"
        placement="right"
      >
        <el-button
          @click="toggleCollapse"
          :icon="isCollapsed ? DArrowRight : DArrowLeft"
          circle
          size="small"
        />
      </el-tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  Monitor,
  Bell,
  Setting,
  DataLine,
  DArrowLeft,
  DArrowRight
} from '@element-plus/icons-vue'

interface Props {
  modelValue?: string
}

interface Emits {
  (e: 'update:modelValue', value: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const activeMenu = ref(props.modelValue || 'monitoring')
const isCollapsed = ref(false)

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    activeMenu.value = newVal
  }
})

const handleSelect = (index: string) => {
  activeMenu.value = index
  emit('update:modelValue', index)
}

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}
</script>

<style scoped>
.sidebar {
  height: 100vh;
  background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 12px rgba(0, 0, 0, 0.15);
  position: fixed;
  left: 0;
  top: 0;
  z-index: 1000;
  transition: width 0.3s ease;
}

.sidebar-header {
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.2);
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
  color: white;
}

.logo-icon {
  color: #409eff;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

.sidebar-menu {
  flex: 1;
  border: none;
  background: transparent;
  padding: 16px 8px;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 200px;
}

:deep(.el-menu-item) {
  color: #b8c7ce;
  margin-bottom: 4px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

:deep(.el-menu-item:hover) {
  background: rgba(64, 158, 255, 0.1);
  color: #409eff;
}

:deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, #409eff 0%, #3a8ee6 100%);
  color: white;
}

:deep(.el-menu-item .el-icon) {
  font-size: 18px;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: center;
  background: rgba(0, 0, 0, 0.2);
}

/* 折叠状态 */
.sidebar:has(.el-menu--collapse) {
  width: 64px !important;
}

:deep(.el-menu--collapse) {
  width: 64px;
}

:deep(.el-menu--collapse .el-menu-item) {
  padding: 0 20px;
  justify-content: center;
}

:deep(.el-menu--collapse .el-menu-item span) {
  display: none;
}

:deep(.el-menu--collapse .logo-text) {
  display: none;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    width: 64px !important;
  }

  .sidebar-menu {
    width: 64px;
  }

  .logo-text {
    display: none;
  }

  :deep(.el-menu-item span) {
    display: none;
  }

  :deep(.el-menu-item) {
    padding: 0 20px;
    justify-content: center;
  }
}
</style>
