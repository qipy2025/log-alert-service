# 设备管理功能实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为设备日志AI告警推送系统添加设备管理功能，允许用户通过 Web 界面管理（添加、编辑、删除）监控设备的配置

**架构：** 在现有 Flask + Vue 3 架构上扩展，后端添加 4 个 API 端点，前端添加设备管理页面和表单对话框

**技术栈：**
- 后端：Python Flask, SQLAlchemy, MySQL
- 前端：Vue 3 + TypeScript + Element Plus
- 测试：pytest (后端)

---

## 文件结构

### 将创建的文件：
- `log-alert-service/src/db/device_config.py` - 扩展 DeviceConfig 类（添加 update 方法）
- `log-alert-service/src/device_manager.py` - 扩展 DeviceManager 类（添加 update_device 方法）
- `log-alert-service/tests/unit/test_device_management_api.py` - API 端点测试
- `log-alert-service/frontend/src/views/DeviceManagement.vue` - 设备管理页面
- `log-alert-service/frontend/src/components/DeviceFormDialog.vue` - 设备表单对话框
- `log-alert-service/frontend/src/composables/useDeviceManagement.ts` - 设备管理逻辑

### 将修改的文件：
- `log-alert-service/src/web/routes.py` - 添加 4 个 API 端点
- `log-alert-service/frontend/src/types/index.ts` - 添加设备配置类型定义
- `log-alert-service/frontend/src/components/MainContent.vue` - 替换设备管理占位符

---

## 任务 1：扩展 DeviceConfig 数据访问类

**文件：**
- 修改：`log-alert-service/src/db/device_config.py:107-111`
- 测试：`log-alert-service/tests/unit/test_device_config_db.py`

### 步骤 1：编写失败的测试

打开 `log-alert-service/tests/unit/test_device_config_db.py`，在文件末尾添加：

```python
def test_update_device_config(session):
    """测试更新设备配置"""
    from datetime import datetime

    # 创建测试设备
    DeviceConfig.create(
        device_name="test_update_device",
        log_path="test\\path\\",
        auto_notify=False,
        polling_interval=2,
        encoding="utf-8-sig",
        enabled=True
    )

    # 更新设备配置
    result = DeviceConfig.update(
        device_name="test_update_device",
        log_path="new\\path\\",
        enabled=False
    )

    assert result is True

    # 验证更新结果
    updated = DeviceConfig.get_by_name("test_update_device")
    assert updated["log_path"] == "new\\path\\"
    assert updated["enabled"] is False
    # 其他字段应保持不变
    assert updated["auto_notify"] is False
    assert updated["polling_interval"] == 2
```

### 步骤 2：运行测试验证失败

```bash
cd log-alert-service
pytest tests/unit/test_device_config_db.py::test_update_device_config -v
```

预期输出：`FAILED`，报错 `AttributeError: type object 'DeviceConfig' has no attribute 'update'`

### 步骤 3：实现 DeviceConfig.update 方法

打开 `log-alert-service/src/db/device_config.py`，在 `exists` 方法之前添加：

```python
@staticmethod
def update(device_name: str, log_path: str = None, auto_notify: bool = None,
           polling_interval: int = None, encoding: str = None, enabled: bool = None) -> bool:
    """更新设备配置

    Args:
        device_name: 设备名称
        log_path: 新的日志路径（可选）
        auto_notify: 新的自动通知设置（可选）
        polling_interval: 新的轮询间隔（可选）
        encoding: 新的编码（可选）
        enabled: 新的启用状态（可选）

    Returns:
        是否更新成功
    """
    session = get_db_session()
    try:
        # 构建更新字段字典
        update_fields = {}
        if log_path is not None:
            update_fields['log_path'] = log_path
        if auto_notify is not None:
            update_fields['auto_notify'] = auto_notify
        if polling_interval is not None:
            update_fields['polling_interval'] = polling_interval
        if encoding is not None:
            update_fields['encoding'] = encoding
        if enabled is not None:
            update_fields['enabled'] = enabled

        if not update_fields:
            return False

        # 构建 SET 子句
        set_clause = ', '.join(f"{field} = :{field}" for field in update_fields.keys())
        update_fields['name'] = device_name

        result = session.execute(
            text(f"UPDATE device_config SET {set_clause} WHERE device_name = :name"),
            update_fields
        )
        session.commit()
        return result.rowcount > 0
    except Exception as e:
        session.rollback()
        logger.error(f"更新设备配置失败: {e}")
        raise
    finally:
        session.close()
```

### 步骤 4：运行测试验证通过

```bash
cd log-alert-service
pytest tests/unit/test_device_config_db.py::test_update_device_config -v
```

预期输出：`PASSED`

### 步骤 5：Commit

```bash
cd log-alert-service
git add src/db/device_config.py tests/unit/test_device_config_db.py
git commit -m "feat: add DeviceConfig.update method for updating device configurations"
```

---

## 任务 2：扩展 DeviceManager 业务逻辑类

**文件：**
- 修改：`log-alert-service/src/device_manager.py:170`（在文件末尾添加）
- 测试：`log-alert-service/tests/unit/test_device_manager.py`

### 步骤 1：编写失败的测试

打开 `log-alert-service/tests/unit/test_device_manager.py`，在文件末尾添加：

```python
def test_update_device(device_manager):
    """测试更新设备配置"""
    # 创建测试设备
    device_manager.add_device({
        "device_name": "test_update",
        "log_path": "old\\path\\",
        "enabled": True
    })

    # 更新设备
    updated = device_manager.update_device("test_update", {
        "log_path": "new\\path\\",
        "enabled": False
    })

    assert updated["log_path"] == "new\\path\\"
    assert updated["enabled"] is False
    assert updated["device_name"] == "test_update"

def test_update_device_not_exists(device_manager):
    """测试更新不存在的设备"""
    with pytest.raises(ValueError, match="设备不存在"):
        device_manager.update_device("nonexistent", {
            "log_path": "new\\path\\"
        })

def test_update_device_invalid_name(device_manager):
    """测试更新设备时名称无效"""
    device_manager.add_device({
        "device_name": "test_device",
        "log_path": "test\\path\\",
        "enabled": True
    })

    with pytest.raises(ValueError, match="设备名称格式无效"):
        device_manager.update_device("test_device", {
            "device_name": "无效名称!@#"
        })

def test_update_device_duplicate_name(device_manager):
    """测试更新设备时名称重复"""
    device_manager.add_device({
        "device_name": "device1",
        "log_path": "path1\\",
        "enabled": True
    })
    device_manager.add_device({
        "device_name": "device2",
        "log_path": "path2\\",
        "enabled": True
    })

    with pytest.raises(ValueError, match="设备名称已存在"):
        device_manager.update_device("device1", {
            "device_name": "device2"
        })
```

### 步骤 2：运行测试验证失败

```bash
cd log-alert-service
pytest tests/unit/test_device_manager.py::test_update_device -v
```

预期输出：`FAILED`，报错 `AttributeError: 'DeviceManager' object has no attribute 'update_device'`

### 步骤 3：实现 DeviceManager.update_device 方法

打开 `log-alert-service/src/device_manager.py`，在文件末尾（最后一个方法之后）添加：

```python
def update_device(self, device_name: str, config: dict) -> dict:
    """更新设备配置

    Args:
        device_name: 当前设备名称
        config: {
            "device_name": str (optional),  # 新的设备名称
            "log_path": str (optional),
            "enabled": bool (optional)
        }

    Returns:
        更新后的设备配置

    Raises:
        ValueError: 设备不存在或输入验证失败
    """
    # 检查设备是否存在
    if not DeviceConfig.exists(device_name):
        raise ValueError(f"设备不存在: {device_name}")

    # 获取可选参数
    new_device_name = config.get("device_name")
    new_log_path = config.get("log_path")
    new_enabled = config.get("enabled")

    # 如果要修改设备名称，需要验证新名称
    if new_device_name is not None:
        self.validate_device_name(new_device_name)
        # 检查新名称是否已被其他设备使用
        if new_device_name != device_name and DeviceConfig.exists(new_device_name):
            raise ValueError(f"设备名称已存在: {new_device_name}")

    # 如果要修改日志路径，需要验证
    if new_log_path is not None:
        self.validate_log_path(new_log_path)

    # 处理设备名称修改（需要特殊处理）
    if new_device_name is not None and new_device_name != device_name:
        # 1. 获取旧配置
        old_device = DeviceConfig.get_by_name(device_name)
        # 2. 创建新设备
        DeviceConfig.create(
            device_name=new_device_name,
            log_path=new_log_path or old_device["log_path"],
            auto_notify=old_device["auto_notify"],
            polling_interval=old_device["polling_interval"],
            encoding=old_device["encoding"],
            enabled=new_enabled if new_enabled is not None else old_device["enabled"]
        )
        # 3. 删除旧设备
        DeviceConfig.delete(device_name)
        # 4. 返回新设备配置
        return DeviceConfig.get_by_name(new_device_name)
    else:
        # 只更新其他字段
        result = DeviceConfig.update(
            device_name=device_name,
            log_path=new_log_path,
            enabled=new_enabled
        )
        if result:
            return DeviceConfig.get_by_name(device_name)
        else:
            raise ValueError(f"更新设备失败: {device_name}")
```

### 步骤 4：运行测试验证通过

```bash
cd log-alert-service
pytest tests/unit/test_device_manager.py::test_update_device -v
pytest tests/unit/test_device_manager.py::test_update_device_not_exists -v
pytest tests/unit/test_device_manager.py::test_update_device_invalid_name -v
pytest tests/unit/test_device_manager.py::test_update_device_duplicate_name -v
```

预期输出：全部 `PASSED`

### 步骤 5：Commit

```bash
cd log-alert-service
git add src/device_manager.py tests/unit/test_device_manager.py
git commit -m "feat: add DeviceManager.update_device method for updating device configurations"
```

---

## 任务 3：添加后端 API 端点

**文件：**
- 修改：`log-alert-service/src/web/routes.py`（在文件末尾添加）
- 测试：`log-alert-service/tests/unit/test_device_management_api.py`

### 步骤 1：创建测试文件

创建 `log-alert-service/tests/unit/test_device_management_api.py`：

```python
"""测试设备管理 API"""
import pytest
import json
from unittest.mock import patch, MagicMock


@pytest.fixture
def app():
    """创建测试应用"""
    from src.web.app import create_app
    app = create_app(testing=True)
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


class TestDeviceManagementAPI:
    """测试设备管理 API 接口"""

    @patch('src.web.routes.DeviceManager')
    def test_get_devices_config_success(self, mock_dm_class, client):
        """测试成功获取设备配置列表"""
        mock_dm = MagicMock()
        mock_dm.get_all_devices.return_value = [
            {
                "device_name": "设备1",
                "log_path": "path1\\",
                "auto_notify": False,
                "polling_interval": 2,
                "encoding": "utf-8-sig",
                "enabled": True
            }
        ]
        mock_dm_class.return_value = mock_dm

        response = client.get('/api/devices/config')

        assert response.status_code == 200
        data = response.get_json()
        assert 'devices' in data
        assert len(data['devices']) == 1
        assert data['devices'][0]['device_name'] == "设备1"

    @patch('src.web.routes.DeviceManager')
    def test_add_device_success(self, mock_dm_class, client):
        """测试成功添加设备"""
        mock_dm = MagicMock()
        mock_dm.add_device.return_value = {
            "device_name": "新设备",
            "log_path": "new\\path\\",
            "auto_notify": False,
            "polling_interval": 2,
            "encoding": "utf-8-sig",
            "enabled": True
        }
        mock_dm_class.return_value = mock_dm

        response = client.post('/api/devices',
                              data=json.dumps({
                                  'device_name': '新设备',
                                  'log_path': 'new\\path\\',
                                  'enabled': True
                              }),
                              content_type='application/json')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['device']['device_name'] == "新设备"

    def test_add_device_missing_fields(self, client):
        """测试添加设备缺少必填字段"""
        response = client.post('/api/devices',
                              data=json.dumps({'device_name': '设备1'}),
                              content_type='application/json')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    @patch('src.web.routes.DeviceManager')
    def test_add_device_duplicate(self, mock_dm_class, client):
        """测试添加重复设备"""
        mock_dm = MagicMock()
        mock_dm.add_device.side_effect = ValueError("设备名称已存在: 新设备")
        mock_dm_class.return_value = mock_dm

        response = client.post('/api/devices',
                              data=json.dumps({
                                  'device_name': '新设备',
                                  'log_path': 'new\\path\\',
                                  'enabled': True
                              }),
                              content_type='application/json')

        assert response.status_code == 409
        data = response.get_json()
        assert '设备名称已存在' in data['error']

    @patch('src.web.routes.DeviceManager')
    def test_update_device_success(self, mock_dm_class, client):
        """测试成功更新设备"""
        mock_dm = MagicMock()
        mock_dm.update_device.return_value = {
            "device_name": "更新后",
            "log_path": "new\\path\\",
            "enabled": False
        }
        mock_dm_class.return_value = mock_dm

        response = client.put('/api/devices/旧名称',
                             data=json.dumps({
                                 'device_name': '更新后',
                                 'log_path': 'new\\path\\',
                                 'enabled': False
                             }),
                             content_type='application/json')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    @patch('src.web.routes.DeviceManager')
    def test_update_device_not_found(self, mock_dm_class, client):
        """测试更新不存在的设备"""
        mock_dm = MagicMock()
        mock_dm.update_device.side_effect = ValueError("设备不存在: 不存在")
        mock_dm_class.return_value = mock_dm

        response = client.put('/api/devices/不存在',
                             data=json.dumps({'enabled': False}),
                             content_type='application/json')

        assert response.status_code == 404

    @patch('src.web.routes.DeviceManager')
    def test_delete_device_success(self, mock_dm_class, client):
        """测试成功删除设备"""
        mock_dm = MagicMock()
        mock_dm.delete_device.return_value = True
        mock_dm_class.return_value = mock_dm

        response = client.delete('/api/devices/测试设备')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    @patch('src.web.routes.DeviceManager')
    def test_delete_device_not_found(self, mock_dm_class, client):
        """测试删除不存在的设备"""
        mock_dm = MagicMock()
        mock_dm.delete_device.side_effect = ValueError("设备不存在: 不存在")
        mock_dm_class.return_value = mock_dm

        response = client.delete('/api/devices/不存在')

        assert response.status_code == 404

    @patch('src.web.routes.DeviceManager')
    def test_delete_device_running(self, mock_dm_class, client):
        """测试删除正在运行的设备"""
        mock_dm = MagicMock()
        mock_dm.delete_device.side_effect = RuntimeError("设备正在运行，无法删除")
        mock_dm_class.return_value = mock_dm

        response = client.delete('/api/devices/运行中')

        assert response.status_code == 409
```

### 步骤 2：运行测试验证失败

```bash
cd log-alert-service
pytest tests/unit/test_device_management_api.py -v
```

预期输出：`FAILED`，报错 `404 NOT FOUND`（API 端点不存在）

### 步骤 3：实现 API 端点

打开 `log-alert-service/src/web/routes.py`，在文件末尾（最后一个路由之后）添加：

```python
# ==================== 设备管理 API ====================

@api_bp.route('/devices/config', methods=['GET'])
def get_devices_config():
    """获取设备配置列表"""
    from src.device_manager import DeviceManager

    try:
        device_manager = DeviceManager()
        devices = device_manager.get_all_devices()
        return jsonify({'devices': devices})
    except Exception as e:
        logger.error(f"获取设备配置失败: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/devices', methods=['POST'])
def add_device():
    """添加新设备"""
    from src.device_manager import DeviceManager

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # 验证必填字段
        required_fields = ['device_name', 'log_path']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        device_name = data['device_name']
        log_path = data['log_path']
        enabled = data.get('enabled', True)

        # 添加设备
        device_manager = DeviceManager()
        device = device_manager.add_device({
            'device_name': device_name,
            'log_path': log_path,
            'enabled': enabled
        })

        return jsonify({
            'success': True,
            'device': device
        }), 201

    except ValueError as e:
        # 业务逻辑错误（如设备名称已存在）
        return jsonify({'error': str(e)}), 409
    except Exception as e:
        logger.error(f"添加设备失败: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/devices/<device_name>', methods=['PUT'])
def update_device(device_name):
    """更新设备配置"""
    from src.device_manager import DeviceManager

    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        device_manager = DeviceManager()
        device = device_manager.update_device(device_name, data)

        return jsonify({
            'success': True,
            'device': device
        })

    except ValueError as e:
        # 业务逻辑错误（如设备不存在）
        error_msg = str(e)
        if '设备不存在' in error_msg:
            return jsonify({'error': error_msg}), 404
        else:
            return jsonify({'error': error_msg}), 400
    except Exception as e:
        logger.error(f"更新设备失败: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/devices/<device_name>', methods=['DELETE'])
def delete_device():
    """删除设备"""
    from src.device_manager import DeviceManager

    try:
        device_manager = DeviceManager()
        device_manager.delete_device(device_name)

        return jsonify({
            'success': True,
            'message': '设备已删除'
        })

    except ValueError as e:
        # 设备不存在
        return jsonify({'error': str(e)}), 404
    except RuntimeError as e:
        # 设备正在运行
        return jsonify({'error': str(e)}), 409
    except Exception as e:
        logger.error(f"删除设备失败: {e}")
        return jsonify({'error': str(e)}), 500
```

### 步骤 4：运行测试验证通过

```bash
cd log-alert-service
pytest tests/unit/test_device_management_api.py -v
```

预期输出：全部 `PASSED`

### 步骤 5：修复 delete_device 路由参数

打开 `log-alert-service/src/web/routes.py`，找到 `delete_device` 函数定义，修改为：

```python
@api_bp.route('/devices/<device_name>', methods=['DELETE'])
def delete_device(device_name):  # 确保参数名正确
    """删除设备"""
    from src.device_manager import DeviceManager

    try:
        device_manager = DeviceManager()
        device_manager.delete_device(device_name)

        return jsonify({
            'success': True,
            'message': '设备已删除'
        })

    except ValueError as e:
        # 设备不存在
        return jsonify({'error': str(e)}), 404
    except RuntimeError as e:
        # 设备正在运行
        return jsonify({'error': str(e)}), 409
    except Exception as e:
        logger.error(f"删除设备失败: {e}")
        return jsonify({'error': str(e)}), 500
```

### 步骤 6：重新运行测试验证

```bash
cd log-alert-service
pytest tests/unit/test_device_management_api.py -v
```

预期输出：全部 `PASSED`

### 步骤 7：Commit

```bash
cd log-alert-service
git add src/web/routes.py tests/unit/test_device_management_api.py
git commit -m "feat: add device management API endpoints (GET /api/devices/config, POST /api/devices, PUT /api/devices/<name>, DELETE /api/devices/<name>)"
```

---

## 任务 4：扩展前端类型定义

**文件：**
- 修改：`log-alert-service/frontend/src/types/index.ts`

### 步骤 1：添加类型定义

打开 `log-alert-service/frontend/src/types/index.ts`，在文件末尾添加：

```typescript
// 设备配置类型（用于设备管理）
export interface DeviceConfig {
  device_name: string        // 设备名称
  log_path: string          // 日志路径
  auto_notify: boolean      // 是否自动通知（只读）
  polling_interval: number  // 轮询间隔（只读）
  encoding: string         // 编码（只读）
  enabled: boolean          // 是否启用
  created_at?: string       // 创建时间（可选）
}

// 设备表单数据类型（用于添加/编辑）
export interface DeviceFormData {
  device_name: string
  log_path: string
  enabled: boolean
}

// API 响应类型
export interface DevicesResponse {
  devices: DeviceConfig[]
}

export interface DeviceOperationResponse {
  success: boolean
  device?: DeviceConfig
  message?: string
}

export interface ApiError {
  error: string
}
```

### 步骤 2：Commit

```bash
cd log-alert-service
git add frontend/src/types/index.ts
git commit -m "feat: add DeviceConfig and DeviceFormData types for device management"
```

---

## 任务 5：创建设备管理 Composable

**文件：**
- 创建：`log-alert-service/frontend/src/composables/useDeviceManagement.ts`

### 步骤 1：创建 composable 文件

创建 `log-alert-service/frontend/src/composables/useDeviceManagement.ts`：

```typescript
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import type { DeviceConfig, DeviceFormData } from '../types'

const API_BASE = '/api'

export function useDeviceManagement() {
  const devices = ref<DeviceConfig[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 获取设备配置列表
  const fetchDevices = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await axios.get<{devices: DeviceConfig[]}>(`${API_BASE}/devices/config`)
      devices.value = response.data.devices
    } catch (e: any) {
      error.value = e.message
      ElMessage.error('获取设备列表失败')
      console.error('获取设备列表失败:', e)
    } finally {
      loading.value = false
    }
  }

  // 添加设备
  const addDevice = async (formData: DeviceFormData): Promise<boolean> => {
    loading.value = true
    try {
      const response = await axios.post<{success: boolean; device: DeviceConfig}>(
        `${API_BASE}/devices`,
        formData
      )

      if (response.data.success) {
        ElMessage.success('设备已添加')
        await fetchDevices() // 刷新列表
        return true
      }
      return false
    } catch (e: any) {
      handleApiError(e)
      return false
    } finally {
      loading.value = false
    }
  }

  // 更新设备
  const updateDevice = async (deviceName: string, formData: DeviceFormData): Promise<boolean> => {
    loading.value = true
    try {
      const response = await axios.put<{success: boolean; device: DeviceConfig}>(
        `${API_BASE}/devices/${encodeURIComponent(deviceName)}`,
        formData
      )

      if (response.data.success) {
        ElMessage.success('设备已更新')
        await fetchDevices() // 刷新列表
        return true
      }
      return false
    } catch (e: any) {
      handleApiError(e)
      return false
    } finally {
      loading.value = false
    }
  }

  // 删除设备
  const deleteDevice = async (device: DeviceConfig): Promise<boolean> => {
    return new Promise((resolve) => {
      ElMessageBox.confirm(
        `确定要删除设备"${device.device_name}"吗？历史告警记录将被保留。`,
        '删除确认',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(async () => {
        loading.value = true
        try {
          const response = await axios.delete<{success: boolean; message: string}>(
            `${API_BASE}/devices/${encodeURIComponent(device.device_name)}`
          )

          if (response.data.success) {
            ElMessage.success('设备已删除')
            await fetchDevices() // 刷新列表
            resolve(true)
          } else {
            resolve(false)
          }
        } catch (e: any) {
          handleApiError(e)
          resolve(false)
        } finally {
          loading.value = false
        }
      }).catch(() => {
        // 用户取消删除
        resolve(false)
      })
    })
  }

  // API 错误处理
  const handleApiError = (error: any) => {
    if (error.response) {
      const status = error.response.status
      const data = error.response.data

      if (status === 409) {
        ElMessage.error(data.error || '设备名称已存在')
      } else if (status === 404) {
        ElMessage.error(data.error || '设备不存在')
      } else if (status === 400) {
        ElMessage.error(data.error || '请求参数错误')
      } else {
        ElMessage.error('操作失败，请稍后重试')
      }
    } else {
      ElMessage.error('网络错误，请检查连接')
    }
  }

  return {
    devices,
    loading,
    error,
    fetchDevices,
    addDevice,
    updateDevice,
    deleteDevice
  }
}
```

### 步骤 2：Commit

```bash
cd log-alert-service
git add frontend/src/composables/useDeviceManagement.ts
git commit -m "feat: add useDeviceManagement composable for device management logic"
```

---

## 任务 6：创建设备表单对话框组件

**文件：**
- 创建：`log-alert-service/frontend/src/components/DeviceFormDialog.vue`

### 步骤 1：创建表单对话框组件

创建 `log-alert-service/frontend/src/components/DeviceFormDialog.vue`：

```vue
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
          placeholder="例如：设备名\\日志\\"
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
```

### 步骤 2：Commit

```bash
cd log-alert-service
git add frontend/src/components/DeviceFormDialog.vue
git commit -m "feat: add DeviceFormDialog component for device add/edit form"
```

---

## 任务 7：创建设备管理页面组件

**文件：**
- 创建：`log-alert-service/frontend/src/views/DeviceManagement.vue`
- 修改：`log-alert-service/frontend/src/components/MainContent.vue:38-51`

### 步骤 1：创建设备管理页面

创建 `log-alert-service/frontend/src/views/DeviceManagement.vue`：

```vue
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
```

### 步骤 2：更新 MainContent 组件

打开 `log-alert-service/frontend/src/components/MainContent.vue`，找到设备管理页面部分（第 38-51 行），替换为：

```vue
<!-- 设备管理页面 -->
<div v-show="currentPage === 'devices'" class="page-view">
  <device-management />
</div>
```

然后在 `<script setup>` 部分的 import 语句中添加：

```typescript
import DeviceManagement from '../views/DeviceManagement.vue'
```

### 步骤 3：运行测试验证前端编译

```bash
cd log-alert-service/frontend
npm run build
```

预期输出：编译成功，没有错误

### 步骤 4：Commit

```bash
cd log-alert-service
git add frontend/src/views/DeviceManagement.vue frontend/src/components/MainContent.vue
git commit -m "feat: add DeviceManagement page and integrate into MainContent"
```

---

## 任务 8：集成测试

**文件：**
- 测试：手动测试

### 步骤 1：启动服务

```bash
cd log-alert-service
python main.py --web
```

### 步骤 2：打开浏览器测试

在浏览器中打开 `http://localhost:5000`

### 步骤 3：测试添加设备

1. 点击侧边栏的"设备管理"菜单
2. 点击"添加设备"按钮
3. 填写表单：
   - 设备名称：`测试设备`
   - 日志路径：`测试设备\日志\`
   - 状态：启用
4. 点击"确定"
5. 验证设备出现在列表中

### 步骤 4：测试编辑设备

1. 点击刚创建设备的"编辑"按钮
2. 修改设备名称为：`测试设备更新`
3. 修改日志路径为：`新路径\日志\`
4. 点击"确定"
5. 验证设备信息已更新

### 步骤 5：测试表单验证

1. 点击"添加设备"
2. 设备名称留空，点击"确定"
3. 验证显示"请输入设备名称"错误提示
4. 输入无效设备名称（如：`test@#$`），点击"确定"
5. 验证显示"只允许中文、字母、数字、下划线"错误提示

### 步骤 6：测试删除设备

1. 点击设备的"删除"按钮
2. 在确认对话框中点击"确定"
3. 验证设备已被删除
4. 验证显示"设备已删除"成功提示

### 步骤 7：测试重复设备名

1. 添加一个名为"重复测试"的设备
2. 再次添加同名的设备
3. 验证显示"设备名称已存在"错误提示

### 步骤 8：API 测试

使用 Postman 或 curl 测试 API 端点：

```bash
# 获取设备列表
curl http://localhost:5000/api/devices/config

# 添加设备
curl -X POST http://localhost:5000/api/devices \
  -H "Content-Type: application/json" \
  -d '{"device_name":"API测试","log_path":"api\\path\\","enabled":true}'

# 更新设备
curl -X PUT http://localhost:5000/api/devices/API测试 \
  -H "Content-Type: application/json" \
  -d '{"device_name":"API测试更新","log_path":"new\\path\\","enabled":false}'

# 删除设备
curl -X DELETE http://localhost:5000/api/devices/API测试更新
```

### 步骤 9：停止服务

在终端按 `Ctrl+C` 停止服务

### 步骤 10：Commit（如有必要）

如果集成测试过程中发现需要修复的问题，修复后提交：

```bash
cd log-alert-service
git add .
git commit -m "fix: address issues found during integration testing"
```

---

## 任务 9：文档更新

**文件：**
- 修改：`log-alert-service/SERVICE_GUIDE.md`

### 步骤 1：更新服务指南

打开 `log-alert-service/SERVICE_GUIDE.md`，在适当位置添加：

```markdown
## 设备管理

### 功能说明

设备管理功能允许管理员通过 Web 界面管理监控设备的配置。

### 使用方法

1. 在侧边栏点击"设备管理"菜单
2. 点击"添加设备"按钮创建新设备
3. 填写设备信息：
   - **设备名称**：1-50个字符，只允许中文、字母、数字、下划线
   - **日志路径**：日志文件所在路径
   - **状态**：启用或禁用设备监控
4. 点击"确定"保存设备配置

### 设备操作

- **编辑**：点击"编辑"按钮修改设备配置
- **删除**：点击"删除"按钮移除设备（历史告警记录将保留）

### 注意事项

- 设备名称必须唯一
- 删除正在运行的设备前需要先停止监控
- 设备名称不可为特殊字符或包含空格
```

### 步骤 2：Commit

```bash
cd log-alert-service
git add SERVICE_GUIDE.md
git commit -m "docs: add device management feature documentation to SERVICE_GUIDE"
```

---

## 任务 10：最终验证

### 步骤 1：运行所有测试

```bash
cd log-alert-service
pytest tests/unit/test_device_management_api.py -v
pytest tests/unit/test_device_manager.py -v
pytest tests/unit/test_device_config_db.py -v
```

预期输出：所有测试 `PASSED`

### 步骤 2：检查功能完整性

对照设计文档的验收标准：

- [ ] 可以查看设备配置列表
- [ ] 可以添加新设备
- [ ] 可以编辑现有设备配置
- [ ] 可以删除设备
- [ ] 表单验证正确工作
- [ ] 错误提示清晰明确

### 步骤 3：检查代码质量

```bash
cd log-alert-service
# 检查 Python 代码风格（如果有安装 pylint）
# pylint src/device_manager.py src/web/routes.py

# 检查前端代码
cd frontend
npm run type-check  # 如果配置了 TypeScript 检查
```

### 步骤 4：最终 Commit

```bash
cd log-alert-service
git status
```

确认所有更改都已提交，如有未提交的文件：

```bash
git add .
git commit -m "chore: final cleanup and verification for device management feature"
```

---

## 实施完成检查清单

### 后端
- [ ] DeviceConfig.update 方法已实现
- [ ] DeviceManager.update_device 方法已实现
- [ ] 4 个 API 端点已添加（GET /api/devices/config, POST /api/devices, PUT /api/devices/<name>, DELETE /api/devices/<name>）
- [ ] 所有单元测试通过
- [ ] API 错误处理完整

### 前端
- [ ] DeviceConfig 和 DeviceFormData 类型已定义
- [ ] useDeviceManagement composable 已实现
- [ ] DeviceFormDialog 组件已实现
- [ ] DeviceManagement 页面已实现
- [ ] MainContent 已集成设备管理页面
- [ ] 前端编译无错误

### 集成
- [ ] 手动测试所有功能正常
- [ ] API 端点测试通过
- [ ] 文档已更新
- [ ] 所有代码已提交

---

**实现计划版本：** 1.0
**创建日期：** 2026-07-10
**预计工作量：** 10 个任务，约 2-4 小时
**依赖：** 设计文档 v1.0
