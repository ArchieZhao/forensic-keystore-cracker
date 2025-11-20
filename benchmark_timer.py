"""
benchmark_timer.py - Benchmark时间统计模块

提供简单易用的时间统计功能，用于性能分析和进度跟踪。
使用Python内置time模块实现，无需额外依赖。
"""

import time
import json
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from datetime import timedelta, datetime
from pathlib import Path
from rich.console import Console

console = Console()


@dataclass
class TimingStats:
    """时间统计数据类"""
    start_time: float
    end_time: Optional[float] = None
    total_items: int = 0
    completed_items: int = 0

    @property
    def elapsed_seconds(self) -> float:
        """已用时间（秒）"""
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    @property
    def elapsed_formatted(self) -> str:
        """已用时间（格式化）"""
        return str(timedelta(seconds=int(self.elapsed_seconds)))

    @property
    def avg_time_per_item(self) -> float:
        """单项平均耗时（秒）"""
        if self.completed_items == 0:
            return 0.0
        return self.elapsed_seconds / self.completed_items

    @property
    def remaining_seconds(self) -> float:
        """预计剩余时间（秒）"""
        if self.completed_items == 0 or self.total_items == 0:
            return 0.0
        remaining_items = self.total_items - self.completed_items
        return self.avg_time_per_item * remaining_items

    @property
    def remaining_formatted(self) -> str:
        """预计剩余时间（格式化）"""
        if self.completed_items == 0:
            return "计算中..."
        return str(timedelta(seconds=int(self.remaining_seconds)))

    @property
    def eta_formatted(self) -> str:
        """预计总时间（格式化）"""
        if self.completed_items == 0:
            return "计算中..."
        total_seconds = self.elapsed_seconds + self.remaining_seconds
        return str(timedelta(seconds=int(total_seconds)))

    @property
    def speed(self) -> float:
        """处理速度（items/秒）"""
        if self.elapsed_seconds == 0:
            return 0.0
        return self.completed_items / self.elapsed_seconds

    @property
    def progress_percentage(self) -> float:
        """完成百分比"""
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100

    def to_dict(self) -> Dict:
        """转换为字典（包含计算属性）"""
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'elapsed_seconds': self.elapsed_seconds,
            'elapsed_formatted': self.elapsed_formatted,
            'remaining_seconds': self.remaining_seconds,
            'remaining_formatted': self.remaining_formatted,
            'eta_formatted': self.eta_formatted,
            'speed': self.speed,
            'progress_percentage': self.progress_percentage
        }


class BenchmarkTimer:
    """Benchmark计时器"""

    def __init__(self, task_name: str, total_items: int = 0, verbose: bool = True):
        """
        初始化计时器

        Args:
            task_name: 任务名称
            total_items: 总任务数量（用于进度计算）
            verbose: 是否显示详细输出
        """
        self.task_name = task_name
        self.verbose = verbose
        self.stats = TimingStats(
            start_time=time.time(),
            total_items=total_items
        )
        self.checkpoints: Dict[str, float] = {}
        self.checkpoint_order: List[str] = []

    def start(self):
        """开始计时"""
        self.stats.start_time = time.time()
        if self.verbose:
            console.print(f"[cyan]⏱️  {self.task_name} 开始...[/cyan]")
            console.print(f"[dim]开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
            if self.stats.total_items > 0:
                console.print(f"[dim]总任务数: {self.stats.total_items}[/dim]")
            console.print()

    def checkpoint(self, name: str):
        """
        记录检查点

        Args:
            name: 检查点名称
        """
        self.checkpoints[name] = time.time()
        if name not in self.checkpoint_order:
            self.checkpoint_order.append(name)

    def get_checkpoint_elapsed(self, name: str) -> float:
        """
        获取检查点相对于开始时间的耗时

        Args:
            name: 检查点名称

        Returns:
            耗时（秒）
        """
        if name not in self.checkpoints:
            return 0.0
        return self.checkpoints[name] - self.stats.start_time

    def get_checkpoint_interval(self, start_checkpoint: str, end_checkpoint: str) -> float:
        """
        获取两个检查点之间的时间间隔

        Args:
            start_checkpoint: 起始检查点名称
            end_checkpoint: 结束检查点名称

        Returns:
            时间间隔（秒）
        """
        if start_checkpoint not in self.checkpoints or end_checkpoint not in self.checkpoints:
            return 0.0
        return self.checkpoints[end_checkpoint] - self.checkpoints[start_checkpoint]

    def update_progress(self, completed: int):
        """
        更新进度

        Args:
            completed: 已完成数量
        """
        self.stats.completed_items = completed

    def print_progress(self):
        """打印当前进度统计"""
        if not self.verbose or self.stats.total_items == 0:
            return

        console.print(f"[yellow]📊 进度统计:[/yellow]")
        console.print(f"  进度: {self.stats.completed_items}/{self.stats.total_items} ({self.stats.progress_percentage:.1f}%)")
        console.print(f"  已用时间: {self.stats.elapsed_formatted}")
        console.print(f"  预计剩余: {self.stats.remaining_formatted}")
        console.print(f"  预计总时间: {self.stats.eta_formatted}")
        console.print(f"  处理速度: {self.stats.speed:.2f} items/秒")
        console.print()

    def print_checkpoints(self):
        """打印所有检查点统计"""
        if not self.verbose or not self.checkpoints:
            return

        console.print(f"[yellow]📍 检查点统计:[/yellow]")
        for i, checkpoint_name in enumerate(self.checkpoint_order):
            elapsed = self.get_checkpoint_elapsed(checkpoint_name)

            # 计算与上一个检查点的间隔
            if i > 0:
                prev_checkpoint = self.checkpoint_order[i - 1]
                interval = self.get_checkpoint_interval(prev_checkpoint, checkpoint_name)
                console.print(f"  {checkpoint_name}: {timedelta(seconds=int(elapsed))} "
                            f"[dim](+{timedelta(seconds=int(interval))})[/dim]")
            else:
                console.print(f"  {checkpoint_name}: {timedelta(seconds=int(elapsed))}")
        console.print()

    def end(self) -> TimingStats:
        """
        结束计时并返回统计

        Returns:
            时间统计数据
        """
        self.stats.end_time = time.time()

        if self.verbose:
            console.print(f"[green]✅ {self.task_name} 完成![/green]")
            console.print(f"[dim]结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
            console.print(f"[yellow]总耗时: {self.stats.elapsed_formatted}[/yellow]")

            if self.stats.total_items > 0:
                console.print(f"[dim]完成数量: {self.stats.completed_items}/{self.stats.total_items}[/dim]")
                console.print(f"[dim]平均速度: {self.stats.speed:.2f} items/秒[/dim]")
                if self.stats.completed_items > 0:
                    console.print(f"[dim]单项平均耗时: {self.stats.avg_time_per_item:.2f}秒[/dim]")

            # 打印检查点统计
            if self.checkpoints:
                console.print()
                self.print_checkpoints()

            console.print()

        return self.stats


class BenchmarkReporter:
    """Benchmark统计报告生成器"""

    def __init__(self, output_dir: Path):
        """
        初始化报告生成器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.stats_history: List[Dict] = []

    def save_stats(self, stage_name: str, stats: TimingStats, metadata: Dict = None):
        """
        保存单个阶段的统计数据

        Args:
            stage_name: 阶段名称
            stats: 时间统计数据
            metadata: 额外的元数据
        """
        record = {
            'timestamp': datetime.now().isoformat(),
            'stage': stage_name,
            **stats.to_dict(),
            'metadata': metadata or {}
        }

        self.stats_history.append(record)

        # 保存到JSON
        json_file = self.output_dir / "benchmark_stats.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats_history, f, indent=2, ensure_ascii=False)

    def generate_summary_report(self, output_file: str = None):
        """
        生成汇总报告

        Args:
            output_file: 输出文件路径（可选）
        """
        if not self.stats_history:
            console.print("[yellow]没有统计数据[/yellow]")
            return

        try:
            import pandas as pd
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment

            # 创建DataFrame
            df = pd.DataFrame(self.stats_history)

            # 生成Excel报告
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = self.output_dir / f"benchmark_report_{timestamp}.xlsx"

            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Sheet 1: 详细统计
                detail_df = df[['timestamp', 'stage', 'elapsed_seconds', 'elapsed_formatted',
                               'total_items', 'completed_items', 'speed', 'progress_percentage']].copy()
                detail_df.columns = ['时间戳', '阶段', '耗时(秒)', '耗时(格式化)',
                                     '总数', '完成数', '速度(items/s)', '进度(%)']
                detail_df.to_excel(writer, sheet_name='详细统计', index=False)

                # Sheet 2: 汇总统计
                total_elapsed = df['elapsed_seconds'].sum()
                summary = pd.DataFrame([{
                    '总阶段数': len(df),
                    '总耗时(秒)': total_elapsed,
                    '总耗时(格式化)': str(timedelta(seconds=int(total_elapsed))),
                    '总处理项目数': int(df['total_items'].sum()),
                    '平均处理速度': df['speed'].mean(),
                }])
                summary.to_excel(writer, sheet_name='汇总统计', index=False)

                # Sheet 3: 各阶段占比
                stage_stats = df.groupby('stage').agg({
                    'elapsed_seconds': 'sum',
                    'total_items': 'sum',
                    'speed': 'mean'
                }).reset_index()
                stage_stats.columns = ['阶段', '耗时(秒)', '总项目数', '平均速度']
                stage_stats['耗时占比(%)'] = (stage_stats['耗时(秒)'] / total_elapsed * 100).round(2)
                stage_stats.to_excel(writer, sheet_name='各阶段占比', index=False)

            console.print(f"[green]✅ Benchmark报告已生成: {output_file}[/green]")

        except ImportError:
            console.print("[yellow]警告: 未安装pandas或openpyxl，跳过Excel报告生成[/yellow]")
            console.print("[yellow]提示: 运行 'pip install pandas openpyxl' 安装依赖[/yellow]")

        # 打印终端摘要
        self.print_terminal_summary()

    def print_terminal_summary(self):
        """在终端打印摘要"""
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]        Benchmark 统计摘要[/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

        # 按阶段分组统计
        stages = {}
        for record in self.stats_history:
            stage = record['stage']
            if stage not in stages:
                stages[stage] = record

        # 打印各阶段统计
        for stage_name, stage_data in stages.items():
            console.print(f"[yellow]📊 {stage_name}[/yellow]")
            console.print(f"  ⏱️  耗时: {stage_data['elapsed_formatted']}")

            if stage_data['total_items'] > 0:
                console.print(f"  📦 处理数: {stage_data['completed_items']}/{stage_data['total_items']}")
                console.print(f"  ⚡ 速度: {stage_data['speed']:.2f} items/秒")

            # 打印元数据
            metadata = stage_data.get('metadata', {})
            if metadata:
                for key, value in metadata.items():
                    console.print(f"  📋 {key}: {value}")

            console.print()

        # 总计
        total_time = sum(record['elapsed_seconds'] for record in self.stats_history)
        total_items = sum(record['total_items'] for record in self.stats_history)
        avg_speed = sum(record['speed'] for record in self.stats_history) / len(self.stats_history)

        console.print("[bold green]📈 总计[/bold green]")
        console.print(f"  ⏱️  总耗时: {timedelta(seconds=int(total_time))}")
        console.print(f"  📦 总处理数: {total_items}")
        console.print(f"  ⚡ 平均速度: {avg_speed:.2f} items/秒")
        console.print()


# 简化的上下文管理器接口
class timer:
    """简化的计时器上下文管理器"""

    def __init__(self, task_name: str, total_items: int = 0, verbose: bool = True):
        """
        初始化计时器

        Args:
            task_name: 任务名称
            total_items: 总任务数
            verbose: 是否显示输出

        Example:
            with timer("处理文件", total_items=100) as t:
                for i in range(100):
                    process_file(i)
                    t.update_progress(i + 1)
        """
        self.benchmark = BenchmarkTimer(task_name, total_items, verbose)

    def __enter__(self):
        self.benchmark.start()
        return self.benchmark

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.benchmark.end()
        return False
