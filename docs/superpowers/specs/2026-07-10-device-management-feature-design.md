# 设备管理功能设计文档

**日期**: 2026-07-10
**项目**: 设备日志AI告警推送系统
**目标**: 为现有监控服务添加设备管理功能
**方案**: 方案 A - 最小实现

## 1. 概述

为现有的设备日志AI告警推送系统添加设备管理功能，允许用户通过 Web 界面管理（添加、编辑、删除）监控设备的配置。

**目标用户**: 系统管理员

**核心功能**:
1. 查看设备配置列表
2. 添加新设备
3. 编辑现有设备配置
4. 删除设备

**可编辑字段**:
- 设备名称 (`device_name`)
- 日志路径 (`log_path`)
- 是否启用 (`enabled`)

## 2. 架构设计

### 2.1 整体架构

在现有系统基础上添加设备管理功能，最小化改动，复用现有架构：

```
┌─────────────────────────────────────────────────────┐
│              现有系统（保持不变）                    │
│  ┌──────────────────────────────────────────────┐  │
│  │   DeviceManager（业务逻辑）                   │  │
│  │   - add_device()                             │  │
│  │   - delete_device()                           │  │
│  │   - get_all_devices()                         │  │
│  └──────────────────────────────────────────────┘  │
│            ▲                    ▲                   │
│            │                    │                   │
│  ┌─────────┴────────┐  ┌────────┴─────────────┐   │
│  │  新增 API 端点    │  │   新增前端页面        │   │
│  │  routes.py        │  │  DeviceManagement.vue│   │
│  └──────────────────┘  └───────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**改动范围**:
- 后端：在 `routes.py` 中添加 4 个新的 API 端点
- 前端：添加 1 个新的页面组件和相关的 composables
- 导航：在现有导航栏中添加"设备管理"菜单项

### 2.2 技术栈

**后端**:
- Python Flask
- 现有的 DeviceManager 和 DeviceConfig 类
- MySQL（设备配置存储）

**前端**:
- Vue 3 + TypeScript
- Element Plus（UI组件库）
- Vue Router（路由管理）

## 3. 后端 API 设计

### 3.1 获取设备配置列表

```
GET /api/devices/config

Response:
{
  "devices": [
    {
      "device_name": "点胶设备",
      "log_path": "点胶设备\\上位机日志\\",
      "enabled": true,
      "auto_notify": false,
      "polling_interval": 2,
      "encoding": "utf-8-sig",
      "created_at": "2026-07-10T10:00:00Z"
    }
  ]
}
```

### 3.2 添加新设备

```
POST /api/devices
Content-Type: application/json

Body:
{
  "device_name": "新设备",
  "log_path": "新设备\\日志\\",
  "enabled": true
}

Response (201):
{
  "success": true,
  "device": {
    "device_name": "新设备",
    "log_path": "新设备\\日志\\",
    "enabled": true,
    "auto_notify": false,
    "polling_interval": 2,
    "encoding": "utf-8-sig",
    "created_at": "2026-07-10T10:05:00Z"
  }
}

Error Response (409):
{
  "error": "设备名称已存在: 新设备"
}
```

### 3.3 更新设备配置

```
PUT /api/devices/{device_name}
Content-Type: application/json

Body:
{
  "device_name": "更新后的名称",
  "log_path": "新路径\\",
  "enabled": false
}

Response (200):
{
  "success": true,
  "device": {
    "device_name": "更新后的名称",
    "log_path": "新路径\\",
    "enabled": false,
    ...
  }
}

Error Response (404):
{
  "error": "设备不存在: 设备名称"
}
```

### 3.4 删除设备

```
DELETE /api/devices/{device_name}

Response (200):
{
  "success": true,
  "message": "设备已删除"
}

Error Response (404):
{
  "error": "设备不存在: 设备名称"
}

Error Response (409):
{
  "error": "设备正在运行，无法删除: 设备名称"
}
```

## 4. 前端设计

### 4.1 页面组件结构

```
frontend/src/
├── views/
│   └── DeviceManagement.vue          # 设备管理页面（新增）
├── components/
│   ├── DeviceFormDialog.vue         # 设备表单对话框（新增）
│   └── (现有组件保持不变)
├── composables/
│   ├── useDeviceManagement.ts       # 设备管理逻辑（新增）
│   └── (现有 composables 保持不变)
└── types/
    └── index.ts                      # 添加设备配置类型定义
```

### 4.2 设备管理页面布局

```
┌──────────────────────────────────────────────────────┐
│  设备管理                              [+ 添加设备]   │
├──────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────┐ │
│  │ │ 设备名称  │ 日志路径          │ 状态 │ 操作 │ │
│  │ ├────────────────────────────────────────────┤ │
│  │ │ 点胶设备  │ 点胶设备\日志...   │ ●启用 │ ✏️ 🗑️│ │
│  │ │ 设备2    │ 设备2\日志...      │ ○禁用 │ ✏️ 🗑️│ │
│  │ └────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### 4.3 表单对话框

```
┌─────────────────────────────────────┐
│  添加设备               [X]          │
├─────────────────────────────────────┤
│  设备名称: [________________]  *必填 │
│  日志路径: [________________]  *必填 │
│  状态:     [● 启用  ○ 禁用]          │
│                                      │
│           [取消]  [确定]             │
└─────────────────────────────────────┘
```

### 4.4 主要交互流程

1. **查看设备列表**：页面加载时自动调用 `GET /api/devices/config` 获取设备列表
2. **添加设备**：点击"添加设备"按钮 → 打开表单对话框 → 填写信息 → 提交 → `POST /api/devices` → 刷新列表
3. **编辑设备**：点击编辑图标 → 打开表单对话框（预填现有数据） → 修改 → 提交 → `PUT /api/devices/{name}` → 刷新列表
4. **删除设备**：点击删除图标 → 确认对话框 → 确认 → `DELETE /api/devices/{name}` → 刷新列表

## 5. 数据模型设计

### 5.1 TypeScript 类型定义

```typescript
// frontend/src/types/index.ts
export interface DeviceConfig {
  device_name: string        // 设备名称
  log_path: string          // 日志路径
  auto_notify: boolean      // 是否自动通知（只读）
  polling_interval: number  // 轮询间隔（只读）
  encoding: string         // 编码（只读）
  enabled: boolean          // 是否启用
  created_at?: string       // 创建时间
}

export interface DeviceFormData {
  device_name: string
  log_path: string
  enabled: boolean
}
```

### 5.2 API 响应格式

```typescript
// 获取设备列表响应
interface DevicesResponse {
  devices: DeviceConfig[]
}

// 添加/更新设备响应
interface DeviceOperationResponse {
  success: boolean
  device?: DeviceConfig
  message?: string
}
```

### 5.3 表单验证规则

```typescript
const validationRules = {
  device_name: [
    { required: true, message: '请输入设备名称', trigger: 'blur' },
    { min: 1, max: 50, message: '长度在 1 到 50 个字符', trigger: 'blur' },
    { pattern: /^[一-龥a-zA-Z0-9_]+$/, message: '只允许中文、字母、数字、下划线', trigger: 'blur' }
  ],
  log_path: [
    { required: true, message: '请输入日志路径', trigger: 'blur' }
  ]
}
```

## 6. 错误处理和用户反馈

### 6.1 API 错误处理

```typescript
// useDeviceManagement.ts 中的错误处理
const handleApiError = (error: any) => {
  if (error.response?.status === 409) {
    ElMessage.error('设备名称已存在')
  } else if (error.response?.status === 404) {
    ElMessage.error('设备不存在')
  } else if (error.response?.status === 400) {
    ElMessage.error(error.response.data.error || '请求参数错误')
  } else {
    ElMessage.error('操作失败，请稍后重试')
  }
}
```

### 6.2 表单验证反馈

- **实时验证**：用户输入时立即显示验证错误
- **提交验证**：点击确定时验证所有必填字段
- **错误提示**：使用 Element Plus 的表单验证提示

### 6.3 操作反馈

- **成功提示**：操作成功后显示 `ElMessage.success('设备已添加')`
- **失败提示**：操作失败后显示具体的错误信息
- **加载状态**：API 调用期间按钮显示 loading 状态

### 6.4 删除确认

```typescript
const handleDelete = (device: DeviceConfig) => {
  ElMessageBox.confirm(
    `确定要删除设备"${device.device_name}"吗？历史告警记录将被保留。`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    deleteDevice(device.device_name)
  })
}
```

## 7. 测试计划

### 7.1 后端单元测试

```python
# tests/unit/test_device_management_api.py
def test_get_devices_config():
    """测试获取设备配置列表"""
    response = client.get('/api/devices/config')
    assert response.status_code == 200
    data = response.get_json()
    assert 'devices' in data

def test_add_device():
    """测试添加设备"""
    response = client.post('/api/devices', json={
        'device_name': 'test_device',
        'log_path': 'test\\path',
        'enabled': True
    })
    assert response.status_code == 200

def test_add_duplicate_device():
    """测试添加重复设备"""
    # 第一次添加
    client.post('/api/devices', json={
        'device_name': 'duplicate',
        'log_path': 'path',
        'enabled': True
    })
    # 第二次添加应该失败
    response = client.post('/api/devices', json={
        'device_name': 'duplicate',
        'log_path': 'path',
        'enabled': True
    })
    assert response.status_code == 409

def test_delete_device():
    """测试删除设备"""
    response = client.delete('/api/devices/test_device')
    assert response.status_code == 200
```

### 7.2 前端组件测试

```typescript
# tests/DeviceManagement.spec.ts (使用 Vitest)
describe('DeviceManagement', () => {
  it('renders device list', () => {
    // 测试设备列表渲染
  })

  it('opens add dialog', () => {
    // 测试打开添加对话框
  })

  it('validates form input', () => {
    // 测试表单验证
  })
})
```

### 7.3 集成测试流程

1. **添加设备流程**：打开页面 → 添加设备 → 验证列表更新 → 验证数据库记录
2. **编辑设备流程**：点击编辑 → 修改信息 → 提交 → 验证列表更新
3. **删除设备流程**：点击删除 → 确认 → 验证设备被删除 → 验证历史告警保留
4. **表单验证流程**：测试各种无效输入 → 验证错误提示

## 8. 实施步骤

### 8.1 后端实施步骤

1. **扩展 DeviceManager 类**：添加 `update_device()` 方法
2. **添加 API 端点**：在 `routes.py` 中添加 4 个新的 API 端点
3. **编写单元测试**：为新的 API 端点编写测试
4. **验证功能**：运行测试，确保所有功能正常

### 8.2 前端实施步骤

1. **创建页面组件**：创建 `DeviceManagement.vue` 页面
2. **创建表单组件**：创建 `DeviceFormDialog.vue` 对话框组件
3. **创建 composables**：创建 `useDeviceManagement.ts` 逻辑复用函数
4. **添加导航菜单**：在侧边栏中添加"设备管理"菜单项
5. **更新路由配置**：在 Vue Router 中添加设备管理路由

### 8.3 集成测试步骤

1. **启动服务**：使用 `python main.py --web` 启动服务
2. **手动测试**：通过浏览器测试所有功能
3. **API 测试**：使用 Postman 或 curl 测试 API 端点
4. **边界测试**：测试错误情况（重复设备名、无效路径等）

### 8.4 文档更新

- 更新 `SERVICE_GUIDE.md`：添加设备管理功能说明
- 更新 API 文档：记录新增的 API 端点

## 9. 风险和注意事项

### 9.1 技术风险

- **设备名称冲突**：添加设备时需要检查设备名称是否已存在
- **运行中的设备**：删除正在运行的设备需要先停止监控
- **历史数据保留**：删除设备时历史告警记录应保留

### 9.2 运维风险

- **误删除风险**：删除操作需要确认对话框
- **配置错误**：表单验证需要确保数据有效性
- **并发操作**：多个用户同时编辑同一设备可能导致冲突

### 9.3 扩展性考虑

- **批量操作**：未来可能需要支持批量启用/禁用/删除
- **设备分组**：未来可能需要支持设备分组管理
- **配置导入/导出**：未来可能需要支持配置的导入和导出

## 10. 验收标准

### 10.1 功能验收

- [ ] 可以查看设备配置列表
- [ ] 可以添加新设备
- [ ] 可以编辑现有设备配置
- [ ] 可以删除设备
- [ ] 表单验证正确工作
- [ ] 错误提示清晰明确

### 10.2 性能验收

- [ ] 设备列表加载时间 < 1秒
- [ ] 添加/编辑/删除操作响应时间 < 2秒
- [ ] 表单验证响应及时

### 10.3 用户体验验收

- [ ] 界面简洁明了
- [ ] 操作流程顺畅
- [ ] 错误提示友好
- [ ] 响应式设计适配不同屏幕

---

**文档版本**: 1.0
**状态**: 待审查
**下一步**: 创建实现计划
