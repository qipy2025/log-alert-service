<template>
  <div class="notification-config">
    <div class="config-header">
      <div class="header-content">
        <h3>通知配置</h3>
        <p class="subtitle">管理飞书告警通知的开关和级别过滤</p>
      </div>
      <el-button @click="loadConfig" :loading="loading" size="default" :icon="Refresh">
        刷新
      </el-button>
    </div>

    <el-card shadow="hover" class="config-card">
      <el-form :model="config" label-width="140px" class="config-form">
        <el-form-item label="总开关">
          <div class="switch-container">
            <el-switch
              v-model="config.enabled"
              @change="handleEnabledChange"
              :loading="updating"
              size="large"
              active-text="启用"
              inactive-text="禁用"
              :active-value="true"
              :inactive-value="false"
              style="--el-switch-on-color: #67f233; --el-switch-off-color: #dcdfe6;"
            />
            <div class="switch-description">
              <el-tag :type="config.enabled ? 'success' : 'info'" size="small" style="margin-left: 12px;">
                {{ config.enabled ? '已启用' : '已禁用' }}
              </el-tag>
            </div>
          </div>
          <div class="help-text">
            {{ config.enabled ? '通知已启用，将根据告警级别设置发送通知' : '通知已禁用，不会发送任何告警通知' }}
          </div>
        </el-form-item>

        <el-divider />

        <el-form-item label="告警级别">
          <div class="levels-container">
            <el-checkbox-group
              v-model="config.allowed_levels"
              :disabled="!config.enabled"
              @change="handleLevelsChange"
              class="levels-checkbox"
            >
              <el-checkbox value="CRITICAL" border class="level-checkbox critical">
                <div class="checkbox-content">
                  <el-tag type="danger" effect="dark">CRITICAL</el-tag>
                  <span>严重告警</span>
                  <el-icon style="margin-left: 4px;"><Warning /></el-icon>
                </div>
              </el-checkbox>
              <el-checkbox value="WARNING" border class="level-checkbox warning">
                <div class="checkbox-content">
                  <el-tag type="warning" effect="dark">WARNING</el-tag>
                  <span>警告告警</span>
                  <el-icon style="margin-left: 4px;"><InfoFilled /></el-icon>
                </div>
              </el-checkbox>
              <el-checkbox value="INFO" border class="level-checkbox info">
                <div class="checkbox-content">
                  <el-tag type="primary" effect="dark">INFO</el-tag>
                  <span>信息告警</span>
                  <el-icon style="margin-left: 4px;"><Document /></el-icon>
                </div>
              </el-checkbox>
            </el-checkbox-group>
          </div>
          <div class="help-text levels-help">
            {{ allowedLevelsText }}
          </div>
        </el-form-item>

        <el-divider />

        <el-form-item>
          <div class="action-buttons">
            <el-button
              type="primary"
              @click="saveConfig"
              :loading="updating"
              :disabled="!hasChanges"
              size="large"
              :icon="SuccessFilled"
            >
              保存配置
            </el-button>
            <el-button
              @click="loadConfig"
              :disabled="updating"
              size="large"
              :icon="RefreshLeft"
            >
              重置
            </el-button>
          </div>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="hover" class="info-card">
      <template #header>
        <div class="info-header">
          <el-icon><InfoFilled /></el-icon>
          <span>配置说明</span>
        </div>
      </template>
      <div class="info-content">
        <div class="info-item">
          <strong>总开关：</strong>
          <span>控制是否启用飞书通知功能。禁用时不会发送任何告警通知。</span>
        </div>
        <div class="info-item">
          <strong>告警级别：</strong>
          <span>选择需要发送通知的告警级别。只有选中的级别才会触发通知。</span>
        </div>
        <div class="info-item">
          <strong>级别说明：</strong>
          <div class="level-examples">
            <div class="level-example">
              <el-tag type="danger" size="small">CRITICAL</el-tag>
              <span>严重告警，需要立即处理</span>
            </div>
            <div class="level-example">
              <el-tag type="warning" size="small">WARNING</el-tag>
              <span>警告告警，需要关注</span>
            </div>
            <div class="level-example">
              <el-tag type="primary" size="small">INFO</el-tag>
              <span>信息告警，一般通知</span>
            </div>
          </div>
        </div>
        <el-alert
          title="💡 提示"
          type="info"
          :closable="false"
          show-icon
        >
          配置变更会实时保存，并通过WebSocket广播到所有连接的客户端。多个客户端可以同时管理配置，更改会自动同步。
        </el-alert>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, SuccessFilled, RefreshLeft, InfoFilled, Warning, Document } from '@element-plus/icons-vue'
import { useNotificationConfig } from '../composables/useNotificationConfig'

const { loading, updating, fetchConfig, updateConfig } = useNotificationConfig()

// 本地编辑的配置副本
const localConfig = ref({
  enabled: false,
  allowed_levels: [] as string[]
})

// 当前显示的配置
const config = computed(() => localConfig.value)

// 检查是否有变更
const hasChanges = computed(() => {
  return JSON.stringify(localConfig.value) !== JSON.stringify(originalConfig.value)
})

// 原始配置副本
const originalConfig = ref({
  enabled: false,
  allowed_levels: [] as string[]
})

// 告警级别说明文本
const allowedLevelsText = computed(() => {
  if (!localConfig.value.enabled) {
    return '通知已禁用，告警级别设置无效'
  }

  const levels = localConfig.value.allowed_levels
  if (levels.length === 0) {
    return '未选择任何级别，所有告警都将被过滤'
  }

  return `已选择 ${levels.length} 个告警级别：${levels.join(', ')}`
})

const loadConfig = async () => {
  const result = await fetchConfig()
  if (result) {
    localConfig.value = { ...result }
    originalConfig.value = { ...result }
  }
}

const saveConfig = async () => {
  try {
    await updateConfig(localConfig.value)
    originalConfig.value = { ...localConfig.value }
    ElMessage.success('通知配置已更新')
  } catch (error: any) {
    ElMessage.error(`保存失败: ${error.message}`)
  }
}

const handleEnabledChange = (value: boolean) => {
  if (!value) {
    ElMessage.warning('通知已禁用，将不会发送任何告警通知')
  } else {
    ElMessage.success('通知已启用')
  }
}

const handleLevelsChange = (value: string[]) => {
  if (value.length === 0) {
    ElMessage.warning('未选择任何告警级别，所有告警都将被过滤')
  }
}

// 监听配置更新事件
window.addEventListener('notification_config_updated', ((event: CustomEvent) => {
  const newConfig = event.detail
  localConfig.value = { ...newConfig }
  originalConfig.value = { ...newConfig }
  ElMessage.info('通知配置已被其他客户端更新')
}) as EventListener)

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.notification-config {
  margin-bottom: 24px;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  padding: 0 4px;
}

.header-content {
  flex: 1;
}

.header-content h3 {
  margin: 0 0 4px 0;
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
}

.subtitle {
  margin: 0;
  font-size: 14px;
  color: #7f8c8d;
  font-weight: 400;
}

.config-card {
  margin-bottom: 20px;
  border-radius: 12px;
  border: 1px solid #e4e7ed;
}

.config-form {
  padding: 20px 0;
}

.switch-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.switch-description {
  display: flex;
  align-items: center;
}

.help-text {
  margin-top: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-left: 3px solid #67f233;
  border-radius: 4px;
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
}

.levels-container {
  width: 100%;
}

.levels-checkbox {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.level-checkbox {
  margin: 0 !important;
  border-radius: 8px;
  padding: 12px 16px;
  transition: all 0.3s ease;
}

.level-checkbox:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.level-checkbox.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.checkbox-content {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.checkbox-content span {
  font-size: 14px;
}

.levels-help {
  margin-top: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-left: 3px solid #409eff;
  border-radius: 4px;
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: flex-start;
}

.info-card {
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
}

.info-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #2c3e50;
}

.info-content {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
}

.info-item {
  margin-bottom: 16px;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-item strong {
  color: #2c3e50;
  font-weight: 600;
  margin-right: 8px;
}

.level-examples {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.level-example {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .config-header {
    flex-direction: column;
    gap: 12px;
  }

  .levels-checkbox {
    flex-direction: column;
  }

  .action-buttons {
    flex-direction: column;
    width: 100%;
  }

  .action-buttons button {
    width: 100%;
  }
}
</style>
