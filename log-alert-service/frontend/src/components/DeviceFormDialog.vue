<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑设备' : '添加设备'"
    width="500px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="100px"
    >
      <el-form-item label="设备名称" prop="device_name">
        <el-input
          v-model="formData.device_name"
          placeholder="请输入设备名称"
          :disabled="isEdit"
        />
      </el-form-item>

      <el-form-item label="日志路径" prop="log_path">
        <el-input
          v-model="formData.log_path"
          placeholder="例如：设备名\日志\\"
        />
      </el-form-item>

      <el-form-item label="状态" prop="enabled">
        <el-radio-group v-model="formData.enabled">
          <el-radio :label="true">启用</el-radio>
          <el-radio :label="false">禁用</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">
        确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { DeviceFormData, DeviceConfig } from '../types'

interface Props {
  modelValue: boolean
  device?: DeviceConfig
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'submit', data: DeviceFormData): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const formRef = ref<FormInstance>()
const loading = ref(false)

const dialogVisible = ref(props.modelValue)
const isEdit = ref(false)

// 表单数据
const formData = reactive<DeviceFormData>({
  device_name: '',
  log_path: '',
  enabled: true
})

// 表单验证规则
const formRules: FormRules<DeviceFormData> = {
  device_name: [
    { required: true, message: '请输入设备名称', trigger: 'blur' },
    { min: 1, max: 50, message: '长度在 1 到 50 个字符', trigger: 'blur' },
    {
      pattern: /^[一-龥a-zA-Z0-9_]+$/,
      message: '只允许中文、字母、数字、下划线',
      trigger: 'blur'
    }
  ],
  log_path: [
    { required: true, message: '请输入日志路径', trigger: 'blur' }
  ]
}

// 监听 modelValue 变化
watch(() => props.modelValue, (newVal) => {
  dialogVisible.value = newVal
})

// 监听对话框显示状态
watch(dialogVisible, (newVal) => {
  emit('update:modelValue', newVal)
  if (!newVal) {
    // 对话框关闭时重置表单
    resetForm()
  }
})

// 监听传入的设备数据（编辑模式）
watch(() => props.device, (newDevice) => {
  if (newDevice) {
    isEdit.value = true
    formData.device_name = newDevice.device_name
    formData.log_path = newDevice.log_path
    formData.enabled = newDevice.enabled
  } else {
    isEdit.value = false
  }
}, { immediate: true })

// 重置表单
const resetForm = () => {
  formData.device_name = ''
  formData.log_path = ''
  formData.enabled = true
  formRef.value?.resetFields()
}

// 关闭对话框
const handleClose = () => {
  dialogVisible.value = false
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    emit('submit', { ...formData })
  } catch (error) {
    console.error('表单验证失败:', error)
  }
}
</script>

<style scoped>
.el-dialog {
  border-radius: 8px;
}

.el-form {
  padding: 0 20px;
}
</style>
