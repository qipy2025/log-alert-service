<template>
  <div class="device-management">
    <div class="page-header">
      <h2>设备管理</h2>
      <el-button type="primary" :icon="Plus" @click="handleAdd">
        添加设备
      </el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="devices"
      stripe
      style="width: 100%"
    >
      <el-table-column prop="device_name" label="设备名称" width="200" />
      <el-table-column prop="log_path" label="日志路径" show-overflow-tooltip />
      <el-table-column prop="enabled" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
            {{ row.enabled ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center">
        <template #default="{ row }">
          <el-button
            type="primary"
            link
            :icon="Edit"
            @click="handleEdit(row)"
          >
            编辑
          </el-button>
          <el-button
            type="danger"
            link
            :icon="Delete"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态提示 -->
    <el-empty
      v-if="!loading && devices.length === 0"
      description="暂无设备，请点击右上角添加设备"
      :image-size="120"
    />

    <!-- 设备表单对话框 -->
    <device-form-dialog
      v-model="dialogVisible"
      :device="currentDevice"
      @submit="handleSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import DeviceFormDialog from '../components/DeviceFormDialog.vue'
import { useDeviceManagement } from '../composables/useDeviceManagement'
import type { DeviceConfig, DeviceFormData } from '../types'

const { devices, loading, fetchDevices, addDevice, updateDevice, deleteDevice } = useDeviceManagement()

const dialogVisible = ref(false)
const currentDevice = ref<DeviceConfig>()

// 加载设备列表
onMounted(() => {
  fetchDevices()
})

// 添加设备
const handleAdd = () => {
  currentDevice.value = undefined
  dialogVisible.value = true
}

// 编辑设备
const handleEdit = (device: DeviceConfig) => {
  currentDevice.value = device
  dialogVisible.value = true
}

// 删除设备
const handleDelete = async (device: DeviceConfig) => {
  await deleteDevice(device)
}

// 提交表单
const handleSubmit = async (formData: DeviceFormData) => {
  let success = false

  if (currentDevice.value) {
    // 编辑模式
    success = await updateDevice(currentDevice.value.device_name, formData)
  } else {
    // 添加模式
    success = await addDevice(formData)
  }

  if (success) {
    dialogVisible.value = false
  }
}
</script>

<style scoped>
.device-management {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
}

.el-table {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.el-empty {
  margin-top: 60px;
}
</style>
