# 设备管理和通知控制系统设计文档

**创建日期**: 2026-07-10
**版本**: 1.0
**状态**: 待实现

## 1. 概述

### 1.1 背景
当前设备监控系统存在以下问题：
- 告警通知过于频繁，导致用户信息过载
- 设备配置硬编码在 YAML 文件中，缺乏动态管理能力
- 无法灵活控制通知发送策略

### 1.2 目标
构建完整的设备管理和通知控制系统，实现：
- 设备的动态增删管理，支持独立配置
- 通知发送的手动控制和设备级自动发送策略
- 用户友好的管理界面

### 1.3 范围
**包含**：
- 设备管理模块（新增、删除、查看）
- 通知控制模块（手动发送、自动发送设置）
- 前端界面改造（设备管理对话框、告警列表增强）
- 后端API设计
- 数据库设计

**不包含**：
- 设备配置的修改功能（监听目录不支持修改）
- 用户权限系统
- 设备分组管理

## 2. 系统架构

### 2.1 架构分层

```
┌─────────────────────────────────────────┐
│           前端界面层                      │
│  ┌──────────────┐  ┌──────────────┐    │
│  │ 设备管理对话框 │  │ 告警列表增强  │    │
│  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────┘
                    ↕ HTTP/WebSocket
┌─────────────────────────────────────────┐
│           API 路由层                      │
│  ┌──────────────┐  ┌──────────────┐    │
│  │ 设备管理API   │  │ 通知控制API   │    │
│  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│           业务逻辑层                      │
│  ┌──────────────┐  ┌──────────────┐    │
│  │ 设备管理器   │  │ 通知发送器   │    │
│  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│           数据持久层                      │
│  ┌──────────────┐  ┌──────────────┐    │
│  │ 设备配置表   │  │ 告警记录表   │    │
│  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────┘
```

### 2.2 核心变更点
1. 设备配置从静态 YAML 文件迁移到动态数据库表
2. 告警通知从"自动发送"改为"可控发送"
3. 新增设备管理界面和通知控制界面
4. 新增设备管理器和通知控制器业务逻辑

## 3. 数据库设计

### 3.1 设备配置表

```sql
CREATE TABLE device_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_name VARCHAR(100) UNIQUE NOT NULL,
    log_path VARCHAR(500) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    auto_notify BOOLEAN DEFAULT FALSE,
    polling_interval INT DEFAULT 2,
    encoding VARCHAR(20) DEFAULT 'utf-8-sig',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(50) DEFAULT 'system',

    INDEX idx_device_name (device_name),
    INDEX idx_enabled (enabled)
);
```

**字段说明**：
- `device_name`: 设备名称，唯一标识
- `log_path`: 监听日志目录路径
- `enabled`: 设备是否启用监控
- `auto_notify`: 是否自动发送通知（新增字段）
- `polling_interval`: 文件轮询间隔（秒）
- `encoding`: 日志文件编码

### 3.2 告警记录表变更

```sql
ALTER TABLE alarm_record ADD COLUMN notified BOOLEAN DEFAULT FALSE;
ALTER TABLE alarm_record ADD INDEX idx_notified (notified);
```

**新增字段**：
- `notified`: 标记通知是否已发送

### 3.3 数据迁移策略

启动时检查并迁移配置：
1. 检查 `device_config` 表是否存在记录
2. 如果表为空，从 `config.yaml` 导入现有设备配置
3. 后续设备管理完全通过数据库操作

## 4. API设计

### 4.1 设备管理API

#### 4.1.1 新增设备

```
POST /api/devices
Content-Type: application/json

Request Body:
{
  "device_name": "打螺丝设备",
  "log_path": "打螺丝设备\\上位机日志\\",
  "auto_notify": false,
  "polling_interval": 2,
  "encoding": "utf-8-sig"
}

Response (201 Created):
{
  "success": true,
  "device": {
    "id": 1,
    "device_name": "打螺丝设备",
    "enabled": true,
    "auto_notify": false,
    "created_at": "2026-07-10T11:30:00"
  }
}

Error Response (400 Bad Request):
{
  "error": "DEVICE_EXISTS",
  "message": "设备名称已存在",
  "details": {
    "field": "device_name",
    "value": "打螺丝设备"
  }
}
```

#### 4.1.2 删除设备

```
DELETE /api/devices/{device_name}

Response (200 OK):
{
  "success": true,
  "message": "设备已删除，历史告警记录已保留"
}

Error Response (404 Not Found):
{
  "error": "DEVICE_NOT_FOUND",
  "message": "设备不存在",
  "details": {
    "device_name": "不存在的设备"
  }
}
```

#### 4.1.3 获取设备列表

```
GET /api/devices

Response (200 OK):
{
  "devices": [
    {
      "device_name": "点胶设备",
      "log_path": "点胶设备\\上位机日志\\",
      "enabled": true,
      "auto_notify": false,
      "status": "RUNNING",
      "today_alarm_count": 5
    }
  ]
}
```

### 4.2 通知控制API

#### 4.2.1 手动发送通知

```
POST /api/alarms/{alarm_id}/notify

Response (200 OK):
{
  "success": true,
  "message": "通知已发送到飞书",
  "sent_at": "2026-07-10T11:35:00"
}

Error Response (400 Bad Request):
{
  "error": "ALREADY_SENT",
  "message": "该告警通知已发送，不能重复发送",
  "details": {
    "alarm_id": 123,
    "sent_at": "2026-07-10T10:00:00"
  }
}
```

#### 4.2.2 设置自动发送

```
PUT /api/devices/{device_name}/auto-notify

Request Body:
{
  "auto_notify": true
}

Response (200 OK):
{
  "success": true,
  "message": "自动发送设置已更新",
  "device_name": "点胶设备",
  "auto_notify": true
}
```

#### 4.2.3 批量发送通知

```
POST /api/alarms/notify/batch

Request Body:
{
  "alarm_ids": [1, 2, 3]
}

Response (200 OK):
{
  "success": true,
  "sent_count": 3,
  "failed_count": 0,
  "results": [
    {"alarm_id": 1, "success": true},
    {"alarm_id": 2, "success": true},
    {"alarm_id": 3, "success": true}
  ]
}
```

## 5. 前端界面设计

### 5.1 主页改造

在主页右上角添加"管理设备"按钮：
- 位置：与现有的刷新按钮并列
- 样式：Element Plus 主要按钮（`type="primary"`）
- 点击事件：打开设备管理对话框

### 5.2 设备管理对话框

#### 5.2.1 对话框结构

```vue
<el-dialog title="设备管理" v-model="dialogVisible" width="80%">
  <!-- 顶部工具栏 -->
  <div class="toolbar">
    <el-button type="primary" @click="showAddDeviceForm">
      添加设备
    </el-button>
  </div>

  <!-- 设备列表表格 -->
  <el-table :data="devices" stripe>
    <el-table-column prop="device_name" label="设备名称" />
    <el-table-column prop="log_path" label="监听目录" />
    <el-table-column prop="enabled" label="状态">
      <template #default="{ row }">
        <el-tag :type="row.enabled ? 'success' : 'info'">
          {{ row.enabled ? '启用' : '禁用' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="auto_notify" label="自动发送">
      <template #default="{ row }">
        <el-switch v-model="row.auto_notify" @change="updateAutoNotify(row)" />
      </template>
    </el-table-column>
    <el-table-column label="操作" width="150">
      <template #default="{ row }">
        <el-button type="danger" size="small" @click="confirmDelete(row)">
          删除
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</el-dialog>
```

#### 5.2.2 新增设备表单

```vue
<el-dialog title="添加设备" v-model="addFormVisible" width="500px">
  <el-form :model="addForm" :rules="formRules" ref="addFormRef">
    <el-form-item label="设备名称" prop="device_name">
      <el-input v-model="addForm.device_name" placeholder="请输入设备名称" />
    </el-form-item>

    <el-form-item label="监听目录" prop="log_path">
      <el-input v-model="addForm.log_path" placeholder="例如：设备名\\上位机日志\\" />
    </el-form-item>

    <el-form-item label="自动发送通知">
      <el-switch v-model="addForm.auto_notify" />
      <span class="tip">关闭后需要手动发送通知</span>
    </el-form-item>

    <el-form-item label="轮询间隔（秒）">
      <el-input-number v-model="addForm.polling_interval" :min="1" :max="60" />
    </el-form-item>

    <el-form-item label="文件编码">
      <el-select v-model="addForm.encoding">
        <el-option label="UTF-8" value="utf-8" />
        <el-option label="UTF-8 with BOM" value="utf-8-sig" />
        <el-option label="GBK" value="gbk" />
      </el-select>
    </el-form-item>
  </el-form>

  <template #footer>
    <el-button @click="addFormVisible = false">取消</el-button>
    <el-button type="primary" @click="submitAddDevice" :loading="loading">
      确定
    </el-button>
  </template>
</el-dialog>
```

### 5.3 告警列表增强

在现有 `AlarmList.vue` 的操作列添加"发送通知"按钮：

```vue
<el-table-column label="操作" width="120">
  <template #default="{ row }">
    <el-button
      v-if="!row.notified"
      type="primary"
      size="small"
      @click="sendNotification(row)"
    >
      发送通知
    </el-button>
    <el-tag v-else type="success">已发送</el-tag>

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
```

## 6. 业务逻辑设计

### 6.1 设备管理器 (src/device_manager.py)

**核心职责**：设备的生命周期管理

**主要方法**：

```python
class DeviceManager:
    def add_device(self, config: dict) -> dict:
        """新增设备

        Args:
            config: {
                "device_name": str,
                "log_path": str,
                "auto_notify": bool,
                "polling_interval": int,
                "encoding": str
            }

        Returns:
            新创建的设备信息

        Raises:
            ValueError: 设备名称已存在
            ValueError: 路径格式无效
        """
        # 1. 验证设备名称唯一性
        # 2. 验证路径格式
        # 3. 写入数据库
        # 4. 更新内存缓存
        # 5. 记录操作日志

    def delete_device(self, device_name: str) -> bool:
        """删除设备

        Args:
            device_name: 设备名称

        Returns:
            是否删除成功

        Raises:
            ValueError: 设备不存在
            RuntimeError: 设备正在运行，无法删除
        """
        # 1. 检查设备是否存在
        # 2. 如果正在运行，先停止监控
        # 3. 从数据库删除（保留告警记录）
        # 4. 记录操作日志

    def get_all_devices(self) -> list:
        """获取所有设备配置"""

    def update_device_config(self, device_name: str, updates: dict) -> dict:
        """更新设备配置"""
```

### 6.2 通知控制器 (src/notification_controller.py)

**核心职责**：通知发送的控制和执行

**主要方法**：

```python
class NotificationController:
    def send_alarm_notification(self, alarm_id: int) -> dict:
        """手动发送单个告警通知

        Args:
            alarm_id: 告警记录ID

        Returns:
            发送结果

        Raises:
            ValueError: 告警不存在
            ValueError: 通知已发送
            RuntimeError: 飞书API调用失败
        """
        # 1. 从数据库获取告警记录
        # 2. 检查是否已发送
        # 3. 获取AI分析结果
        # 4. 调用飞书通知器
        # 5. 标记为已发送
        # 6. 记录操作日志

    def set_auto_notify(self, device_name: str, enabled: bool) -> bool:
        """设置设备的自动发送开关"""
        # 1. 更新设备配置
        # 2. 重新加载设备监控（如果正在运行）
        # 3. 记录操作日志

    def batch_send_notifications(self, alarm_ids: list[int]) -> dict:
        """批量发送通知

        Returns:
            {
                "sent_count": int,
                "failed_count": int,
                "results": list
            }
        """
```

### 6.3 告警处理流程变更

**现有流程** (main.py `_on_alarm` 方法)：
```
1. 去重检查
2. 收集上下文
3. AI分析
4. 存储告警到数据库
5. WebSocket实时推送
6. 自动发送飞书通知 ❌
```

**新流程**：
```
1. 去重检查
2. 收集上下文
3. AI分析
4. 存储告警到数据库
5. WebSocket实时推送
6. 检查设备的 auto_notify 设置
   - 如果为 true → 自动发送飞书通知 ✓
   - 如果为 false → 不发送，等待用户手动触发
```

**实现代码**：
```python
def _on_alarm(self, event):
    """告警回调"""
    # ... 前面的处理逻辑 ...

    # 检查是否自动发送通知
    device = self.device_manager.get_device(event.module_name)
    if device.get('auto_notify', False):
        # 自动发送
        success = self.notifier.send_alarm(event, analysis)
        if success:
            logger.info(f"告警自动推送成功: {event.alarm_text}")
    else:
        # 不自动发送，等待用户手动触发
        logger.debug(f"告警未自动推送，等待手动发送: {event.alarm_text}")
```

## 7. 错误处理和验证

### 7.1 输入验证规则

**设备名称验证**：
- 不允许空值
- 正则表达式：`^[一-龥a-zA-Z0-9_]{1,50}$`
  - 允许：中文、字母、数字、下划线
  - 长度：1-50字符
- 唯一性检查：不能与现有设备重名

**监听目录验证**：
- 不允许空值
- 路径格式验证：
  - Windows: `^[a-zA-Z]:\\[^<>:"|?*]*`
  - Linux: `^/[^<>:"|?*]*`
- 可选的路径存在性检查

**告警ID验证**：
- 必须是正整数
- 必须存在于数据库中
- 不能重复发送（检查 `notified` 字段）

### 7.2 错误响应格式

```json
{
  "error": "ERROR_CODE",
  "message": "用户友好的错误描述",
  "details": {
    "field": "具体字段",
    "value": "违规值",
    "constraint": "约束条件"
  }
}
```

### 7.3 错误码定义

| 错误码 | HTTP状态码 | 描述 |
|--------|-----------|------|
| `DEVICE_EXISTS` | 400 | 设备名称已存在 |
| `DEVICE_NOT_FOUND` | 404 | 设备不存在 |
| `INVALID_PATH` | 400 | 监听目录路径无效 |
| `ALARM_NOT_FOUND` | 404 | 告警记录不存在 |
| `ALREADY_SENT` | 400 | 通知已发送，不能重复发送 |
| `DELETE_FAILED` | 400 | 删除设备失败 |
| `INVALID_DEVICE_NAME` | 400 | 设备名称格式无效 |

### 7.4 业务逻辑错误处理

**删除设备时的处理**：
```python
def delete_device(device_name: str):
    # 检查设备状态
    status = get_device_status(device_name)
    if status.get('status') == 'RUNNING':
        # 先停止监控
        stop_device_monitoring(device_name)

    # 删除设备
    try:
        delete_from_database(device_name)
    except Exception as e:
        logger.error(f"删除设备失败: {e}")
        raise RuntimeError(f"删除设备失败: {str(e)}")

    # 记录操作日志
    log_operation('DELETE_DEVICE', device_name)
```

**通知发送失败处理**：
```python
def send_alarm_notification(alarm_id: int):
    try:
        # 发送飞书通知
        result = notifier.send(alarm_data)
        mark_as_notified(alarm_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"发送通知失败: {e}")
        # 不影响告警记录本身
        return {"success": False, "error": str(e)}
```

## 8. 测试策略

### 8.1 单元测试

**设备管理器测试**：
```python
def test_add_device_success():
    """测试成功添加设备"""
    manager = DeviceManager()
    result = manager.add_device({
        "device_name": "测试设备",
        "log_path": "测试路径\\",
        "auto_notify": False
    })
    assert result["device_name"] == "测试设备"

def test_add_device_duplicate():
    """测试添加重复设备"""
    manager = DeviceManager()
    manager.add_device({"device_name": "设备1", "log_path": "路径\\"})
    with pytest.raises(ValueError, match="设备名称已存在"):
        manager.add_device({"device_name": "设备1", "log_path": "路径2\\"})

def test_delete_device():
    """测试删除设备"""
    manager = DeviceManager()
    manager.add_device({"device_name": "设备1", "log_path": "路径\\"})
    result = manager.delete_device("设备1")
    assert result is True

def test_invalid_path_format():
    """测试无效路径格式"""
    manager = DeviceManager()
    with pytest.raises(ValueError, match="路径格式无效"):
        manager.add_device({"device_name": "设备", "log_path": "invalid<>path"})
```

**通知控制器测试**：
```python
def test_send_notification_success():
    """测试成功发送通知"""
    controller = NotificationController()
    result = controller.send_alarm_notification(alarm_id=1)
    assert result["success"] is True

def test_send_notification_already_sent():
    """测试重复发送"""
    controller = NotificationController()
    controller.send_alarm_notification(alarm_id=1)
    with pytest.raises(ValueError, match="通知已发送"):
        controller.send_alarm_notification(alarm_id=1)

def test_batch_send():
    """测试批量发送"""
    controller = NotificationController()
    result = controller.batch_send_notifications([1, 2, 3])
    assert result["sent_count"] == 3
```

### 8.2 集成测试

**API端到端测试**：
```python
def test_device_management_flow():
    """测试完整的设备管理流程"""
    # 1. 新增设备
    response = client.post('/api/devices', json={
        "device_name": "集成测试设备",
        "log_path": "测试路径\\"
    })
    assert response.status_code == 201

    # 2. 查看设备列表
    response = client.get('/api/devices')
    assert "集成测试设备" in [d["device_name"] for d in response.json["devices"]]

    # 3. 删除设备
    response = client.delete('/api/devices/集成测试设备')
    assert response.status_code == 200

    # 4. 验证删除
    response = client.get('/api/devices')
    assert "集成测试设备" not in [d["device_name"] for d in response.json["devices"]]
```

### 8.3 前端测试

**组件测试**：
```javascript
describe('DeviceManagementDialog', () => {
  it('should validate device name', async () => {
    const wrapper = mount(DeviceManagementDialog)
    await wrapper.vm.addForm.device_name = 'invalid@name'
    await wrapper.vm.submitAddDevice()
    expect(wrapper.vm.formErrors.device_name).toBeTruthy()
  })

  it('should confirm before delete', async () => {
    const wrapper = mount(DeviceManagementDialog)
    await wrapper.vm.confirmDelete({device_name: '测试设备'})
    expect(wrapper.vm.deleteConfirmVisible).toBe(true)
  })
})
```

### 8.4 手动测试场景

**场景1：添加新设备**
1. 用户点击"管理设备"按钮
2. 点击"添加设备"
3. 填写设备信息：名称"打螺丝设备"，路径"打螺丝设备\\日志\\"
4. 点击确定
5. 验证设备出现在列表中
6. 验证设备开始监控日志

**场景2：手动发送通知**
1. 系统检测到新告警
2. 告警出现在前端列表，显示"发送通知"按钮
3. 用户点击"发送通知"
4. 验证飞书收到通知
5. 验证按钮变为"已发送"

**场景3：设置自动发送**
1. 用户打开设备管理对话框
2. 找到"点胶设备"
3. 打开"自动发送"开关
4. 后续告警自动推送到飞书
5. 关闭开关后，告警需要手动发送

**场景4：删除设备**
1. 用户点击设备的"删除"按钮
2. 确认对话框显示"保留历史告警记录"
3. 用户确认删除
4. 验证设备从列表消失
5. 验证历史告警记录仍然可查

## 9. 实现优先级

### 9.1 第一阶段：核心功能（必须）
- [ ] 数据库设计和迁移
- [ ] 设备管理器实现
- [ ] 通知控制器实现
- [ ] 后端API开发
- [ ] 前端设备管理对话框
- [ ] 告警列表添加发送按钮

### 9.2 第二阶段：界面优化（重要）
- [ ] 表单验证和错误提示
- [ ] 删除确认对话框
- [ ] 自动发送开关实时生效
- [ ] 通知发送状态显示

### 9.3 第三阶段：高级功能（可选）
- [ ] 批量发送通知
- [ ] 通知发送历史记录
- [ ] 设备配置导出/导入

## 10. 风险和挑战

### 10.1 技术风险
- **数据迁移风险**：YAML到数据库的迁移可能失败
  - 缓解措施：充分的测试和备份
- **并发问题**：多个用户同时管理设备
  - 缓解措施：添加乐观锁或悲观锁

### 10.2 用户体验风险
- **学习曲线**：用户可能不熟悉手动发送通知的流程
  - 缓解措施：提供清晰的用户指引和提示
- **操作复杂度**：设备管理界面可能过于复杂
  - 缓解措施：保持界面简洁，分步骤引导

### 10.3 业务风险
- **通知遗漏**：重要告警可能被遗忘手动发送
  - 缓解措施：保留自动发送选项，提供告警提醒

## 11. 后续扩展可能性

- 设备分组管理
- 用户权限系统
- 通知模板自定义
- 设备性能监控
- 移动端适配

## 12. 验收标准

### 12.1 功能验收
- [ ] 用户可以成功添加新设备
- [ ] 用户可以成功删除设备（保留历史记录）
- [ ] 用户可以手动发送通知
- [ ] 用户可以设置设备级别的自动发送
- [ ] 系统在删除设备时正确保留历史告警

### 12.2 性能验收
- [ ] 设备管理API响应时间 < 200ms
- [ ] 通知发送成功率 > 95%
- [ ] 前端界面响应时间 < 100ms

### 12.3 稳定性验收
- [ ] 所有错误都有友好的错误提示
- [ ] 数据库操作失败不影响系统运行
- [ ] 飞书API调用失败可以重试

---

**文档版本历史**：
- v1.0 (2026-07-10): 初始设计文档
