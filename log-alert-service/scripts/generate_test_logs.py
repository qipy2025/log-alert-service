#!/usr/bin/env python3
"""
生成测试日志文件
"""
import argparse
from pathlib import Path
from datetime import datetime, timedelta

def generate_normal_alarm_log(output_path):
    """生成正常告警日志（50行，3个告警）"""
    lines = []
    base_time = datetime(2026, 7, 9, 10, 30, 0)

    # 正常日志行
    for i in range(20):
        t = base_time + timedelta(seconds=i)
        lines.append(f"{t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} [  37] [DesaySV.Presentation.Core.GlueModule][233] - 轨迹数据{i}动作\n")

    # 3个告警
    for i in range(3):
        t = base_time + timedelta(seconds=20 + i*5)
        lines.append(f"{t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} [   1] [DesaySV.Presentation.Core.FrmMain][319] - 右点胶阀缺胶报警_人工请马上更换\n")
        lines.append(f"{t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} [   6] [DesaySV.Presentation.Core.FrmMain][1742] - 报警复位操作\n")

    # 继续正常日志
    for i in range(25):
        t = base_time + timedelta(seconds=35 + i)
        lines.append(f"{t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} [  37] [DesaySV.Presentation.Core.GlueModule][233] - 正常日志行{i}\n")

    output_path = Path(output_path) / "normal_alarms.log"
    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.writelines(lines)
    print(f"[OK] Generated normal alarm log: {output_path}")

def generate_large_log(output_path):
    """生成大文件日志（10MB+，1000个告警）"""
    lines = []
    base_time = datetime(2026, 7, 9, 10, 30, 0)

    # 生成大量日志
    for batch in range(100):  # 100 个批次
        for i in range(100):
            t = base_time + timedelta(seconds=batch*100 + i)
            lines.append(f"{t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} [  37] [GlueModule][{233+i%100}] - 正常日志行 {batch*100+i}\n")

        # 每批次插入10个告警
        for j in range(10):
            t = base_time + timedelta(seconds=batch*100 + 50 + j)
            lines.append(f"{t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} [   1] [FrmMain][319] - 批次{batch}告警{j+1}_人工请马上更换\n")

    output_path = Path(output_path) / "boundary_large.log"
    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.writelines(lines)

    file_size = output_path.stat().st_size / (1024*1024)
    print(f"[OK] Generated large log file: {output_path} ({file_size:.2f} MB)")

def generate_concurrent_log(output_path):
    """生成并发告警场景日志（模拟3个设备）"""
    lines = []
    base_time = datetime(2026, 7, 9, 10, 30, 0)

    # 3个设备同时写入告警
    for device in ["设备A", "设备B", "设备C"]:
        for i in range(5):
            t = base_time + timedelta(seconds=i)
            lines.append(f"{t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} [   1] [{device}][319] - {device}点胶阀缺胶报警_人工请马上更换\n")

    output_path = Path(output_path) / "boundary_concurrent.log"
    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.writelines(lines)
    print(f"[OK] Generated concurrent alarm log: {output_path}")

def generate_encoding_log(output_path):
    """生成特殊字符编码日志"""
    lines = []
    base_time = datetime(2026, 7, 9, 10, 30, 0)

    special_texts = [
        "🔴 右点胶阀缺胶报警_人工请马上更换",
        "点胶阀异常🔧需要维护",
        "左点胶阀缺胶预警_日文テスト",
        "特殊字符测试 $ & % # @ !",
        "Emoji测试 🚨 ⚠️ ℹ️ 🔧",
    ]

    for i, text in enumerate(special_texts):
        t = base_time + timedelta(seconds=i*5)
        lines.append(f"{t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} [   1] [FrmMain][319] - {text}\n")

    output_path = Path(output_path) / "boundary_encoding.log"
    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.writelines(lines)
    print(f"[OK] Generated special character log: {output_path}")

def generate_date_change_log(output_path):
    """生成日期切换场景日志（跨23:59:59）"""
    lines = []

    # 23:59:50 的告警
    t1 = datetime(2026, 7, 9, 23, 59, 50)
    lines.append(f"{t1.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} [   1] [FrmMain][319] - 日期切换前告警_人工请马上更换\n")

    # 00:00:10 的告警
    t2 = datetime(2026, 7, 10, 0, 0, 10)
    lines.append(f"{t2.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} [   1] [FrmMain][319] - 日期切换后告警_人工请马上更换\n")

    output_path = Path(output_path) / "boundary_date_change.log"
    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.writelines(lines)
    print(f"[OK] Generated date change log: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="生成测试日志文件")
    parser.add_argument("--output", "-o", required=True, help="输出目录")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    print("开始生成测试日志文件...")
    generate_normal_alarm_log(output_path)
    generate_large_log(output_path)
    generate_concurrent_log(output_path)
    generate_encoding_log(output_path)
    generate_date_change_log(output_path)

    print(f"\n[SUCCESS] All test logs generated to: {output_path}")

if __name__ == "__main__":
    main()
