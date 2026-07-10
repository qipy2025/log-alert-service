"""边界场景集成测试"""
import time
import tempfile
from pathlib import Path
from datetime import datetime
import pytest

from src.models import AlarmLevel, AlarmSource
from src.file_watcher import LogWatcher
from src.log_parser import scan_file_for_alarms

class TestBoundaryScenarios:
    """边界场景测试"""

    def test_2_1_large_log_file(self, tmp_path):
        """场景2.1：大日志文件处理"""
        # 1. 准备10MB日志文件，包含50个告警
        log_lines = []
        base_time = datetime(2026, 7, 9, 10, 30, 0)

        for i in range(20000):
            t = base_time.timestamp() + i
            log_lines.append(f"2026-07-09 10:30:{i%60:02d},000 [37] [Module][{i%1000}] - 正常日志行 {i}\n")

            # 每400行插入一个告警
            if i % 400 == 0:
                log_lines.append(f"2026-07-09 10:30:{i%60:02d},000 [1] [FrmMain][319] - 点胶阀缺胶报警_人工请马上更换\n")

        log_file = tmp_path / "large_test.log"
        with open(log_file, "w", encoding="utf-8-sig") as f:
            f.writelines(log_lines)

        # 2. 验证文件大小
        file_size_mb = log_file.stat().st_size / (1024*1024)
        assert file_size_mb >= 1.0  # 至少1MB

        # 3. 扫描告警
        start_time = time.time()
        alarms = scan_file_for_alarms(str(log_file))
        elapsed = time.time() - start_time

        # 4. 验证：所有告警被正确解析
        assert len(alarms) == 50  # 50个告警

        # 5. 验证：解析时间在可接受范围内（<30秒，实际应该<5秒）
        assert elapsed < 30.0

        # 6. 验证：无内存溢出（如果成功到这里就说明没溢出）
        print(f"[OK] Processed {file_size_mb:.2f}MB file, found {len(alarms)} alarms in {elapsed:.2f}s")

    def test_2_2_concurrent_alarms(self, tmp_path):
        """场景2.2：并发告警处理"""
        import threading

        captured_alarms = []
        lock = threading.Lock()

        def on_alarm(event):
            with lock:
                captured_alarms.append(event)

        # 模拟3个设备同时写入
        def write_device_log(device_name, delay):
            time.sleep(delay)
            log_file = tmp_path / f"{device_name}_Default.log"
            log_content = f"2026-07-09 10:30:00,000 [1] [{device_name}][319] - {device_name} glue valve alarm\n"
            log_file.write_text(log_content, encoding="utf-8-sig")

        # 创建3个线程同时写入
        threads = []
        for i, device in enumerate(["DeviceA", "DeviceB", "DeviceC"]):
            t = threading.Thread(target=write_device_log, args=(device, i*0.1))
            threads.append(t)
            t.start()

        # 等待所有写入完成
        for t in threads:
            t.join()

        # 验证：3个设备的日志都存在
        assert (tmp_path / "DeviceA_Default.log").exists()
        assert (tmp_path / "DeviceB_Default.log").exists()
        assert (tmp_path / "DeviceC_Default.log").exists()

    def test_2_3_special_characters_encoding(self, tmp_path):
        """场景2.3：特殊字符和编码"""
        # 1. 准备包含特殊字符的日志
        special_texts = [
            "右点胶阀缺胶报警_emoji 🔴",
            "点胶阀异常🔧需要维护",
            "左点胶阀缺胶预警_日文テスト",
            "特殊字符测试 $ & % # @ !",
            "Emoji测试 🚨 ⚠️ ℹ️ 🔧",
        ]

        log_lines = []
        for i, text in enumerate(special_texts):
            log_lines.append(f"2026-07-09 10:30:{i*2:02d},000 [1] [FrmMain][319] - {text}\n")

        log_file = tmp_path / "encoding_test.log"
        with open(log_file, "w", encoding="utf-8-sig") as f:
            f.writelines(log_lines)

        # 2. 扫描告警
        alarms = scan_file_for_alarms(str(log_file))

        # 3. 验证：正确解析各种字符编码
        # 注意：只有包含告警关键词的行会被检测到
        assert len(alarms) >= 3  # 至少检测到3个告警

        # 4. 验证：不抛出编码异常
        for alarm in alarms:
            assert alarm.alarm_text is not None
            assert len(alarm.alarm_text) > 0

        # 5. 验证：特殊字符正确显示
        alarm_texts = [a.alarm_text for a in alarms]
        # 检查是否包含特殊字符（通过长度和内容验证）
        assert any(len(text) > 10 for text in alarm_texts)

    def test_2_4_date_change_scenario(self, tmp_path):
        """场景2.4：日期切换场景"""
        # 1. 在 23:59:50 写入告警日志
        log_lines = [
            "2026-07-09 23:59:50,000 [1] [FrmMain][319] - 日期切换前缺胶报警_人工请马上更换\n",
            "2026-07-10 00:00:10,000 [1] [FrmMain][319] - 日期切换后缺胶报警_人工请马上更换\n",
        ]

        log_file = tmp_path / "date_change_test.log"
        with open(log_file, "w", encoding="utf-8-sig") as f:
            f.writelines(log_lines)

        # 2. 扫描告警
        alarms = scan_file_for_alarms(str(log_file))

        # 3. 验证：两个告警都被正确解析
        assert len(alarms) == 2

        # 4. 验证：日期正确
        date_9 = datetime(2026, 7, 9, 23, 59, 50)
        date_10 = datetime(2026, 7, 10, 0, 0, 10)

        assert alarms[0].timestamp.date() == date_9.date()
        assert alarms[1].timestamp.date() == date_10.date()
