#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GPU性能实时监控器

使用nvidia-smi查询GPU温度/功耗/显存/利用率，
检测hashcat进程状态和potfile更新时间，
通过rich Live实时刷新监控界面，记录JSON日志，
提供温度/功耗/显存超限警告。

Architecture:
    nvidia-smi查询 → 数据解析 → rich布局 → Live刷新 → JSON日志

    GPUMonitor (gpu_monitor.py:26)
        ├─ __init__() (L27): 初始化阈值（温度80/85°C，功耗300W，显存90%）
        ├─ get_gpu_info() (L50): nvidia-smi查询6个指标（name, temp, power, memory, util）
        ├─ check_hashcat_status() (L87): tasklist检查hashcat.exe进程 + potfile时间戳
        ├─ log_sample() (L112): 记录JSON样本到gpu_performance.log，保留最近1000个
        ├─ create_monitor_table() (L138): 创建实时监控Table（当前值/状态/历史最高）
        ├─ create_status_panel() (L175): 创建状态Panel（hashcat运行/potfile更新/监控时间）
        ├─ create_performance_bars() (L196): 创建性能条形图Bar（温度/功耗/利用率/显存）
        ├─ check_warnings() (L225): 检查3级警告（温度≥80/85°C，功耗≥300W，显存≥90%）
        ├─ create_layout() (L242): 组合Layout（header/main/footer，left/right分区）
        ├─ start_monitoring() (L295): 主循环，Live刷新interval秒
        └─ show_summary() (L334): 显示监控总结Table（时长/采样/最高温度/功耗/显存）

Features:
    - nvidia-smi实时查询：6个指标（name, temp, power, memory, util）(gpu_monitor.py:53-56)
    - 3级温度警告：80°C警告，85°C危险 (gpu_monitor.py:44-45, 148-156)
    - hashcat进程检测：tasklist + potfile时间戳 (gpu_monitor.py:91-102)
    - rich Live刷新：1 FPS实时更新Layout (gpu_monitor.py:305)
    - JSON日志记录：追加写入gpu_performance.log (gpu_monitor.py:135-136)
    - 样本数限制：保留最近1000个样本 (gpu_monitor.py:131-132)
    - 性能条形图：Bar组件显示4个指标 (gpu_monitor.py:196-223)
    - 监控总结：统计最高温度/功耗/显存 (gpu_monitor.py:334-373)

Args (交互式输入):
    监控间隔（秒）(int): rich.prompt.IntPrompt交互式输入，默认5秒

        示例：
        python gpu_monitor.py
        # 提示：监控间隔（秒）[5]: 10  # 输入10秒间隔
        # 或直接按Enter使用默认5秒

Returns (输出):
    batch_crack_output/gpu_performance.log: JSON日志（每行一个样本）
        格式: {"timestamp": "ISO8601", "temperature": float, "power_draw": float,
               "memory_percent": float, "utilization": float, "hashcat_running": bool}

    终端显示（rich Live Layout）:
        - Header Panel: 标题 + 当前时间
        - Left Table: 实时监控表（5行：温度/功耗/显存/利用率/显存MB）
        - Right Status Panel: hashcat状态 + potfile更新 + 监控时间 + 样本数
        - Right Bars Table: 性能条形图（4行Bar）
        - Footer Panel: 警告列表或"所有指标正常"
        - 退出时Summary Table: 监控时长/采样次数/最高值/健康建议

Requirements:
    - nvidia-smi (NVIDIA GPU驱动，查询GPU信息)
    - rich (终端UI: Console, Live, Table, Panel, Layout, Bar, IntPrompt)
    - tasklist (Windows命令，检查hashcat.exe进程)
    - Python标准库: subprocess, json, time, datetime, threading, pathlib

Technical Notes:
    nvidia-smi查询命令:
        参数: --query-gpu=name,temperature.gpu,power.draw,memory.used,memory.total,utilization.gpu
        格式: --format=csv,noheader,nounits (gpu_monitor.py:53-56)
        超时: 5秒 (gpu_monitor.py:59)
        解析: 按逗号分割6个字段 (gpu_monitor.py:62-78)

    温度警告阈值:
        80°C: 警告状态"⚠️ 警告"，黄色 (gpu_monitor.py:44, 151-153)
        85°C: 危险状态"🔥 危险"，红色 (gpu_monitor.py:45, 148-150)
        <80°C: 正常状态"✅ 正常"，绿色 (gpu_monitor.py:154-156)

    hashcat进程检测:
        tasklist命令: /FI "IMAGENAME eq hashcat.exe" /FO CSV (gpu_monitor.py:92)
        进程判断: 'hashcat.exe' in stdout (gpu_monitor.py:96)
        potfile时间戳: stat().st_mtime转datetime (gpu_monitor.py:102)

    样本管理:
        记录字段: timestamp, temperature, power_draw, memory_percent, utilization, hashcat_running (gpu_monitor.py:114-121)
        限制数量: 保留最近1000个样本 (gpu_monitor.py:131-132)
        日志格式: JSON Lines（每行一个JSON对象）(gpu_monitor.py:136)

    rich Live刷新:
        刷新率: 1 FPS (gpu_monitor.py:305)
        更新间隔: 用户指定interval秒 (gpu_monitor.py:324)
        布局结构: 3行Layout（header/main/footer），main分左右2列 (gpu_monitor.py:247-257)

    性能条形图范围:
        温度: 0-90°C (gpu_monitor.py:204)
        功耗: 0-350W (gpu_monitor.py:209)
        利用率: 0-100% (gpu_monitor.py:213)
        显存: 0-100% (gpu_monitor.py:216)

Workflow:
    1. 初始化GPUMonitor，设置阈值（温度80/85°C，功耗300W，显存90%）
    2. 使用nvidia-smi测试GPU可用性
    3. rich.prompt.IntPrompt交互式输入监控间隔（默认5秒）
    4. 启动rich Live刷新（1 FPS）
    5. 主监控循环：
       - nvidia-smi查询6个GPU指标
       - tasklist检查hashcat.exe进程状态
       - 读取potfile最后修改时间
       - 记录JSON样本到gpu_performance.log
       - 创建Layout（Table/Panel/Bar组件）
       - Live.update()刷新显示
       - sleep(interval)等待下次查询
    6. Ctrl+C中断或异常退出
    7. 显示监控总结Table（时长/采样/最高值）
    8. 显示健康建议（温度/功耗评估）

Author: Forensic Keystore Cracker Project
Version: 1.0.0
License: 仅用于授权的数字取证和安全研究
"""

import os
import sys
import time
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.bar import Bar
import threading

console = Console()

class GPUMonitor:
    def __init__(self):
        self.monitoring = False
        self.log_file = Path("batch_crack_output/gpu_performance.log")
        self.log_file.parent.mkdir(exist_ok=True)
        
        # 监控数据
        self.monitor_data = {
            'start_time': None,
            'samples': [],
            'max_temp': 0,
            'max_power': 0,
            'max_memory': 0,
            'total_samples': 0
        }
        
        # 警告阈值
        self.thresholds = {
            'temp_warning': 80,    # 温度警告阈值 (°C)
            'temp_critical': 85,   # 温度危险阈值 (°C)
            'power_warning': 300,  # 功耗警告阈值 (W)
            'memory_warning': 90   # 显存使用警告阈值 (%)
        }
    
    def get_gpu_info(self) -> Optional[Dict]:
        """获取GPU信息"""
        try:
            cmd = [
                'nvidia-smi',
                '--query-gpu=name,temperature.gpu,power.draw,memory.used,memory.total,utilization.gpu',
                '--format=csv,noheader,nounits'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                line = result.stdout.strip()
                parts = [part.strip() for part in line.split(',')]
                
                if len(parts) >= 6:
                    memory_used = float(parts[3]) if parts[3] != '[N/A]' else 0
                    memory_total = float(parts[4]) if parts[4] != '[N/A]' else 1
                    memory_percent = (memory_used / memory_total) * 100 if memory_total > 0 else 0
                    
                    return {
                        'name': parts[0],
                        'temperature': float(parts[1]) if parts[1] != '[N/A]' else 0,
                        'power_draw': float(parts[2]) if parts[2] != '[N/A]' else 0,
                        'memory_used': memory_used,
                        'memory_total': memory_total,
                        'memory_percent': memory_percent,
                        'utilization': float(parts[5]) if parts[5] != '[N/A]' else 0,
                        'timestamp': datetime.now()
                    }
            
            return None
            
        except Exception as e:
            console.print(f"[red]获取GPU信息失败: {e}[/red]")
            return None
    
    def check_hashcat_status(self) -> Dict:
        """检查hashcat进程状态"""
        try:
            # 检查是否有hashcat进程运行
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq hashcat.exe', '/FO', 'CSV'],
                capture_output=True, text=True, timeout=5
            )
            
            hashcat_running = 'hashcat.exe' in result.stdout
            
            # 检查potfile最后修改时间
            potfile = Path("batch_crack_output/batch_results.potfile")
            last_update = None
            if potfile.exists():
                last_update = datetime.fromtimestamp(potfile.stat().st_mtime)
            
            return {
                'running': hashcat_running,
                'last_potfile_update': last_update
            }
            
        except Exception:
            return {'running': False, 'last_potfile_update': None}
    
    def log_sample(self, gpu_info: Dict, hashcat_info: Dict):
        """记录监控样本"""
        sample = {
            'timestamp': gpu_info['timestamp'].isoformat(),
            'temperature': gpu_info['temperature'],
            'power_draw': gpu_info['power_draw'],
            'memory_percent': gpu_info['memory_percent'],
            'utilization': gpu_info['utilization'],
            'hashcat_running': hashcat_info['running']
        }
        
        # 更新统计
        self.monitor_data['samples'].append(sample)
        self.monitor_data['total_samples'] += 1
        self.monitor_data['max_temp'] = max(self.monitor_data['max_temp'], gpu_info['temperature'])
        self.monitor_data['max_power'] = max(self.monitor_data['max_power'], gpu_info['power_draw'])
        self.monitor_data['max_memory'] = max(self.monitor_data['max_memory'], gpu_info['memory_percent'])
        
        # 只保留最近1000个样本
        if len(self.monitor_data['samples']) > 1000:
            self.monitor_data['samples'] = self.monitor_data['samples'][-1000:]
        
        # 写入日志文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(sample) + '\n')
    
    def create_monitor_table(self, gpu_info: Dict, hashcat_info: Dict) -> Table:
        """创建监控数据表格"""
        table = Table(title="🖥️ RTX 3080 实时监控", border_style="green")
        table.add_column("指标", style="cyan", width=15)
        table.add_column("当前值", style="white", width=15)
        table.add_column("状态", style="yellow", width=10)
        table.add_column("历史最高", style="blue", width=15)
        
        # 温度状态
        temp = gpu_info['temperature']
        if temp >= self.thresholds['temp_critical']:
            temp_status = "🔥 危险"
            temp_style = "red"
        elif temp >= self.thresholds['temp_warning']:
            temp_status = "⚠️ 警告"
            temp_style = "yellow"
        else:
            temp_status = "✅ 正常"
            temp_style = "green"
        
        # 功耗状态
        power = gpu_info['power_draw']
        power_status = "⚠️ 高" if power >= self.thresholds['power_warning'] else "✅ 正常"
        
        # 显存状态
        memory = gpu_info['memory_percent']
        memory_status = "⚠️ 高" if memory >= self.thresholds['memory_warning'] else "✅ 正常"
        
        # 添加行
        table.add_row("GPU温度", f"{temp:.1f}°C", temp_status, f"{self.monitor_data['max_temp']:.1f}°C")
        table.add_row("功耗", f"{power:.1f}W", power_status, f"{self.monitor_data['max_power']:.1f}W")
        table.add_row("显存使用", f"{memory:.1f}%", memory_status, f"{self.monitor_data['max_memory']:.1f}%")
        table.add_row("GPU利用率", f"{gpu_info['utilization']:.1f}%", "📊", "-")
        table.add_row("显存", f"{gpu_info['memory_used']:.0f}MB", "💾", f"{gpu_info['memory_total']:.0f}MB")
        
        return table
    
    def create_status_panel(self, hashcat_info: Dict) -> Panel:
        """创建状态面板"""
        if hashcat_info['running']:
            status_text = "[green]🚀 Hashcat正在运行[/green]"
        else:
            status_text = "[red]⏹️ Hashcat未运行[/red]"
        
        if hashcat_info['last_potfile_update']:
            time_since = datetime.now() - hashcat_info['last_potfile_update']
            status_text += f"\n[cyan]📝 最后更新: {time_since.total_seconds()/60:.1f}分钟前[/cyan]"
        
        if self.monitor_data['start_time']:
            running_time = datetime.now() - self.monitor_data['start_time']
            hours = int(running_time.total_seconds() / 3600)
            minutes = int((running_time.total_seconds() % 3600) / 60)
            status_text += f"\n[yellow]⏱️ 监控时间: {hours}小时{minutes}分钟[/yellow]"
        
        status_text += f"\n[blue]📊 样本数: {self.monitor_data['total_samples']}[/blue]"
        
        return Panel(status_text, title="任务状态", border_style="blue")
    
    def create_performance_bars(self, gpu_info: Dict) -> Table:
        """创建性能条形图"""
        table = Table(title="📊 性能指标", show_header=False, border_style="yellow")
        table.add_column("指标", width=12)
        table.add_column("进度条", width=30)
        table.add_column("值", width=10)
        
        # 温度条 (0-90°C)
        temp_percent = min(gpu_info['temperature'] / 90 * 100, 100)
        temp_bar = Bar(size=20, begin=0, end=100, width=20)
        temp_color = "red" if temp_percent > 80 else "yellow" if temp_percent > 60 else "green"
        
        # 功耗条 (0-350W)
        power_percent = min(gpu_info['power_draw'] / 350 * 100, 100)
        power_bar = Bar(size=20, begin=0, end=100, width=20)
        
        # 利用率条
        util_bar = Bar(size=20, begin=0, end=100, width=20)
        
        # 显存条
        memory_bar = Bar(size=20, begin=0, end=100, width=20)
        
        table.add_row("温度", f"[{temp_color}]{temp_bar}[/{temp_color}]", f"{gpu_info['temperature']:.1f}°C")
        table.add_row("功耗", f"[blue]{power_bar}[/blue]", f"{gpu_info['power_draw']:.1f}W")
        table.add_row("GPU利用率", f"[green]{util_bar}[/green]", f"{gpu_info['utilization']:.1f}%")
        table.add_row("显存", f"[cyan]{memory_bar}[/cyan]", f"{gpu_info['memory_percent']:.1f}%")
        
        return table
    
    def check_warnings(self, gpu_info: Dict) -> List[str]:
        """检查警告条件"""
        warnings = []
        
        if gpu_info['temperature'] >= self.thresholds['temp_critical']:
            warnings.append(f"🔥 GPU温度危险: {gpu_info['temperature']:.1f}°C")
        elif gpu_info['temperature'] >= self.thresholds['temp_warning']:
            warnings.append(f"⚠️ GPU温度偏高: {gpu_info['temperature']:.1f}°C")
        
        if gpu_info['power_draw'] >= self.thresholds['power_warning']:
            warnings.append(f"⚠️ 功耗偏高: {gpu_info['power_draw']:.1f}W")
        
        if gpu_info['memory_percent'] >= self.thresholds['memory_warning']:
            warnings.append(f"⚠️ 显存使用偏高: {gpu_info['memory_percent']:.1f}%")
        
        return warnings
    
    def create_layout(self, gpu_info: Dict, hashcat_info: Dict) -> Layout:
        """创建监控布局"""
        layout = Layout()
        
        # 主要分区
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=5)
        )
        
        # 主要内容分区
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        # 标题
        layout["header"].update(Panel.fit(
            "[bold cyan]🖥️ RTX 3080 GPU监控器[/bold cyan] | "
            f"[yellow]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/yellow]",
            border_style="cyan"
        ))
        
        # 左侧: 监控表格
        layout["left"].update(self.create_monitor_table(gpu_info, hashcat_info))
        
        # 右侧分割
        layout["right"].split_column(
            Layout(name="status"),
            Layout(name="bars")
        )
        
        # 状态面板
        layout["right"]["status"].update(self.create_status_panel(hashcat_info))
        
        # 性能条形图
        layout["right"]["bars"].update(self.create_performance_bars(gpu_info))
        
        # 底部警告
        warnings = self.check_warnings(gpu_info)
        if warnings:
            warning_text = "\n".join(warnings)
            layout["footer"].update(Panel(warning_text, title="⚠️ 警告", border_style="red"))
        else:
            layout["footer"].update(Panel(
                "[green]✅ 所有指标正常[/green]\n"
                "[cyan]💡 按 Ctrl+C 退出监控[/cyan]",
                title="状态", border_style="green"
            ))
        
        return layout
    
    def start_monitoring(self, interval: int = 5):
        """开始监控"""
        self.monitoring = True
        self.monitor_data['start_time'] = datetime.now()
        
        console.print("[cyan]🚀 开始GPU监控...[/cyan]")
        console.print(f"[yellow]📝 日志文件: {self.log_file}[/yellow]")
        console.print(f"[yellow]⏱️ 监控间隔: {interval}秒[/yellow]")
        
        try:
            with Live(console=console, refresh_per_second=1) as live:
                while self.monitoring:
                    # 获取GPU信息
                    gpu_info = self.get_gpu_info()
                    if gpu_info is None:
                        console.print("[red]❌ 无法获取GPU信息[/red]")
                        break
                    
                    # 获取hashcat状态
                    hashcat_info = self.check_hashcat_status()
                    
                    # 记录日志
                    self.log_sample(gpu_info, hashcat_info)
                    
                    # 更新显示
                    layout = self.create_layout(gpu_info, hashcat_info)
                    live.update(layout)
                    
                    # 等待间隔
                    time.sleep(interval)
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]⏹️ 用户停止监控[/yellow]")
        except Exception as e:
            console.print(f"\n[red]❌ 监控出错: {e}[/red]")
        finally:
            self.monitoring = False
            self.show_summary()
    
    def show_summary(self):
        """显示监控总结"""
        if self.monitor_data['total_samples'] == 0:
            console.print("[yellow]⚠️ 没有监控数据[/yellow]")
            return
        
        # 计算统计信息
        if self.monitor_data['start_time']:
            total_time = datetime.now() - self.monitor_data['start_time']
            hours = total_time.total_seconds() / 3600
        else:
            hours = 0
        
        # 创建总结表
        summary_table = Table(title="📈 监控总结", border_style="green")
        summary_table.add_column("项目", style="cyan")
        summary_table.add_column("值", style="white")
        
        summary_table.add_row("监控时长", f"{hours:.2f}小时")
        summary_table.add_row("采样次数", str(self.monitor_data['total_samples']))
        summary_table.add_row("最高温度", f"{self.monitor_data['max_temp']:.1f}°C")
        summary_table.add_row("最高功耗", f"{self.monitor_data['max_power']:.1f}W")
        summary_table.add_row("最高显存", f"{self.monitor_data['max_memory']:.1f}%")
        summary_table.add_row("日志文件", str(self.log_file))
        
        console.print(summary_table)
        
        # 健康建议
        console.print("\n[bold yellow]💡 监控建议:[/bold yellow]")
        if self.monitor_data['max_temp'] > 85:
            console.print("[red]- 温度过高，建议检查散热[/red]")
        elif self.monitor_data['max_temp'] > 80:
            console.print("[yellow]- 温度偏高，注意通风[/yellow]")
        else:
            console.print("[green]- 温度正常[/green]")
        
        if self.monitor_data['max_power'] > 300:
            console.print("[yellow]- 功耗较高，属于高性能工作状态[/yellow]")
        else:
            console.print("[green]- 功耗正常[/green]")

def main():
    console.print("=" * 60)
    console.print("[bold cyan]🖥️ RTX 3080 GPU监控器[/bold cyan]")
    console.print("[yellow]专为长时间批量破解任务设计[/yellow]")
    console.print("=" * 60)
    
    monitor = GPUMonitor()
    
    # 检查是否能获取GPU信息
    gpu_info = monitor.get_gpu_info()
    if gpu_info is None:
        console.print("[red]❌ 无法获取GPU信息，请检查NVIDIA驱动[/red]")
        return 1
    
    console.print(f"[green]✅ 检测到GPU: {gpu_info['name']}[/green]")
    
    try:
        # 获取监控间隔
        from rich.prompt import IntPrompt
        interval = IntPrompt.ask("监控间隔（秒）", default=5, show_default=True)
        
        # 开始监控
        monitor.start_monitoring(interval)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️ 用户退出[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ 程序出错: {e}[/red]")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main()) 