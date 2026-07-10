-- 创建通知配置表
CREATE TABLE IF NOT EXISTS notification_config (
  id INT PRIMARY KEY AUTO_INCREMENT,
  enabled BOOLEAN DEFAULT FALSE COMMENT '总开关，默认关闭',
  allowed_levels JSON COMMENT '允许的告警级别，如 ["CRITICAL", "WARNING"]',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_id (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通知配置表';

-- 创建索引以提升查询性能
CREATE INDEX idx_enabled ON notification_config(enabled);

-- 插入默认配置：禁用通知，空级别列表
-- 使用 IGNORE 确保幂等性，如果已存在则跳过
INSERT IGNORE INTO notification_config (id, enabled, allowed_levels)
VALUES (1, FALSE, '[]');
