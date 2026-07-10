<template>
  <div id="app" :class="{ 'sidebar-collapsed': isCollapsed }">
    <sidebar v-model="currentPage" />

    <div class="main-wrapper" :class="{ 'collapsed': isCollapsed }">
      <div class="top-bar">
        <div class="bar-left">
          <el-button
            @click="toggleSidebar"
            :icon="isCollapsed ? DArrowRight : DArrowLeft"
            circle
            size="small"
        />
          <h1 class="page-title">{{ pageTitle }}</h1>
        </div>
        <div class="bar-right">
          <el-tag :type="connected ? 'success' : 'info'" size="small" effect="plain">
            WebSocket: {{ connected ? '已连接' : '未连接' }}
          </el-tag>
        </div>
      </div>

      <main-content :current-page="currentPage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { DArrowLeft, DArrowRight } from '@element-plus/icons-vue'
import Sidebar from './components/Sidebar.vue'
import MainContent from './components/MainContent.vue'
import { useWebSocket } from './composables/useWebSocket'

const { connected } = useWebSocket()
const currentPage = ref('monitoring')
const isCollapsed = ref(false)

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    monitoring: '设备监控',
    notification: '通知配置',
    devices: '设备管理',
    history: '历史数据'
  }
  return titles[currentPage.value] || '设备监控'
})

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}
</script>

<style scoped>
#app {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  display: flex;
}

.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 200px;
  transition: margin-left 0.3s ease;
  min-width: 0;
}

.main-wrapper.collapsed {
  margin-left: 64px;
}

.top-bar {
  height: 64px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  position: sticky;
  top: 0;
  z-index: 100;
}

.bar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #2c3e50;
}

.bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .main-wrapper {
    margin-left: 64px !important;
  }

  .top-bar {
    padding: 0 16px;
  }

  .page-title {
    font-size: 18px;
  }

  .bar-left {
    gap: 8px;
  }
}
</style>
