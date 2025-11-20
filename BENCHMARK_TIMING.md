# Benchmark时间统计实现指南

## 📋 概述

本文档详细说明如何在项目的关键运行节点添加时间统计功能，包括：
- 运行时间（已用时间）
- 预计剩余时间
- 预计总时间
- 各阶段耗时统计

## 🎯 需要统计的关键节点

### 1. Hash提取阶段（extractor_jks_hash.py）
```
关键节点：
├─ 文件扫描开始/结束
├─ 单个文件hash提取开始/结束
└─ 批量提取完成
```

### 2. GPU破解阶段（cracker_hashcat_gpu.py）
```
关键节点：
├─ Hashcat启动
├─ 破解进度更新（实时）
├─ 单个hash破解成功
└─ 破解任务完成/超时
```

### 3. 证书信息提取阶段（analyzer_crack_result.py）
```
关键节点：
├─ 批量提取开始
├─ 单个证书处理开始/结束
├─ 多进程并行统计
└─ 所有证书提取完成
```

### 4. 完整批量破解流程（cli_batch_crack.py）
```
关键节点：
├─ 流程启动
├─ Hash提取阶段
├─ GPU破解阶段
├─ 结果分析阶段
├─ 报告生成阶段
└─ 流程完成
```

## 🛠️ 实现方案

### 方案1: 使用Python内置time模块（简单场景）

#### 基础计时器类
```python
import time
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import timedelta

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


class BenchmarkTimer:
    """Benchmark计时器"""

    def __init__(self, task_name: str, total_items: int = 0):
        self.task_name = task_name
        self.stats = TimingStats(
            start_time=time.time(),
            total_items=total_items
        )
        self.checkpoints: Dict[str, float] = {}

    def start(self):
        """开始计时"""
        self.stats.start_time = time.time()
        console.print(f"[cyan]⏱️  {self.task_name} 开始...[/cyan]")
        console.print(f"[dim]开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
        if self.stats.total_items > 0:
            console.print(f"[dim]总任务数: {self.stats.total_items}[/dim]")
        console.print()

    def checkpoint(self, name: str):
        """记录检查点"""
        self.checkpoints[name] = time.time()

    def update_progress(self, completed: int):
        """更新进度"""
        self.stats.completed_items = completed

    def print_progress(self):
        """打印当前进度统计"""
        if self.stats.total_items == 0:
            return

        progress_pct = (self.stats.completed_items / self.stats.total_items) * 100

        console.print(f"[yellow]📊 进度统计:[/yellow]")
        console.print(f"  进度: {self.stats.completed_items}/{self.stats.total_items} ({progress_pct:.1f}%)")
        console.print(f"  已用时间: {self.stats.elapsed_formatted}")
        console.print(f"  预计剩余: {self.stats.remaining_formatted}")
        console.print(f"  预计总时间: {self.stats.eta_formatted}")
        console.print(f"  处理速度: {self.stats.speed:.2f} items/秒")
        console.print()

    def end(self) -> TimingStats:
        """结束计时并返回统计"""
        self.stats.end_time = time.time()
        console.print(f"[green]✅ {self.task_name} 完成![/green]")
        console.print(f"[dim]结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
        console.print(f"[yellow]总耗时: {self.stats.elapsed_formatted}[/yellow]")

        if self.stats.total_items > 0:
            console.print(f"[dim]完成数量: {self.stats.completed_items}/{self.stats.total_items}[/dim]")
            console.print(f"[dim]平均速度: {self.stats.speed:.2f} items/秒[/dim]")

        console.print()
        return self.stats
```

#### 使用示例：Hash提取
```python
# 在 extractor_jks_hash.py 中使用
def extract_hashes(keystore_dir: Path, mask: str) -> Path:
    """批量提取hash"""

    # 1. 扫描文件
    keystore_files = list(keystore_dir.rglob("*.jks")) + \
                     list(keystore_dir.rglob("*.keystore"))

    # 2. 创建计时器
    timer = BenchmarkTimer("JKS Hash批量提取", total_items=len(keystore_files))
    timer.start()

    # 3. 处理文件
    extracted_hashes = []
    for idx, keystore_file in enumerate(keystore_files, 1):
        # 提取单个文件的hash
        hash_result = extract_single_hash(keystore_file)
        if hash_result:
            extracted_hashes.append(hash_result)

        # 更新进度
        timer.update_progress(idx)

        # 每10个文件打印一次进度
        if idx % 10 == 0 or idx == len(keystore_files):
            timer.print_progress()

    # 4. 结束计时
    stats = timer.end()

    # 5. 保存统计到文件
    save_benchmark_stats("hash_extraction", stats)

    return output_hash_file
```

#### 使用示例：GPU破解
```python
# 在 cracker_hashcat_gpu.py 中使用
def crack_with_timing(self, hash_file: Path, mask: str) -> Dict:
    """GPU破解并统计时间"""

    timer = BenchmarkTimer("Hashcat GPU破解")
    timer.start()

    # 启动Hashcat进程
    process = self.start_hashcat(hash_file, mask)
    timer.checkpoint("hashcat_started")

    # 实时监控进度
    cracked_count = 0
    total_hashes = count_hashes(hash_file)
    timer.stats.total_items = total_hashes

    while process.poll() is None:
        # 读取Hashcat输出
        status = self.parse_hashcat_status()

        if status:
            cracked_count = status.get('recovered', 0)
            timer.update_progress(cracked_count)

            # 显示实时进度
            console.print(f"[cyan]破解进度: {cracked_count}/{total_hashes}[/cyan]")
            console.print(f"[dim]已用: {timer.stats.elapsed_formatted} | "
                         f"预计剩余: {timer.stats.remaining_formatted}[/dim]")

        time.sleep(2)  # 每2秒更新一次

    # 结束计时
    stats = timer.end()

    # 返回结果和统计
    return {
        'cracked_passwords': self.parse_cracked_results(),
        'benchmark_stats': stats
    }
```

#### 使用示例：证书信息提取（多进程）
```python
# 在 analyzer_crack_result.py 中使用
def extract_certificates_parallel(cracked_results: List[Dict]) -> List[Dict]:
    """并行提取证书信息"""

    timer = BenchmarkTimer("证书信息批量提取（多进程）", total_items=len(cracked_results))
    timer.start()

    # 使用多进程池
    from multiprocessing import Pool, cpu_count, Manager

    num_processes = cpu_count() - 1
    console.print(f"[cyan]使用 {num_processes} 个进程并行处理[/cyan]")

    # 共享进度计数器
    manager = Manager()
    progress_counter = manager.Value('i', 0)

    with Pool(processes=num_processes) as pool:
        # 启动异步任务
        async_results = []
        for item in cracked_results:
            async_result = pool.apply_async(
                extract_single_certificate,
                args=(item,),
                callback=lambda x: update_progress(progress_counter, timer)
            )
            async_results.append(async_result)

        # 等待所有任务完成，定期打印进度
        while progress_counter.value < len(cracked_results):
            timer.update_progress(progress_counter.value)
            timer.print_progress()
            time.sleep(1)

        # 收集结果
        results = [ar.get() for ar in async_results]

    # 结束计时
    stats = timer.end()

    # 打印多进程性能对比
    console.print(f"[green]多进程加速效果:[/green]")
    console.print(f"  单进程预估: {timer.stats.elapsed_seconds * num_processes:.1f}秒")
    console.print(f"  多进程实际: {timer.stats.elapsed_seconds:.1f}秒")
    console.print(f"  性能提升: {num_processes:.1f}x")

    return results


def update_progress(counter, timer):
    """进度回调函数"""
    with counter.get_lock():
        counter.value += 1
```

#### 使用示例：完整批量破解流程
```python
# 在 cli_batch_crack.py 中使用
def main():
    """完整批量破解流程"""

    # 总流程计时器
    main_timer = BenchmarkTimer("批量破解完整流程")
    main_timer.start()

    # 阶段1: Hash提取
    console.rule("[cyan]阶段1: Hash提取[/cyan]")
    phase1_timer = BenchmarkTimer("Hash提取阶段")
    phase1_timer.start()
    hash_file = extract_hashes(cert_dir, mask)
    phase1_stats = phase1_timer.end()

    # 阶段2: GPU破解
    console.rule("[cyan]阶段2: GPU破解[/cyan]")
    phase2_timer = BenchmarkTimer("GPU破解阶段")
    phase2_timer.start()
    crack_results = crack_with_gpu(hash_file, mask)
    phase2_stats = phase2_timer.end()

    # 阶段3: 证书提取
    console.rule("[cyan]阶段3: 证书信息提取[/cyan]")
    phase3_timer = BenchmarkTimer("证书提取阶段")
    phase3_timer.start()
    cert_info = extract_certificates_parallel(crack_results)
    phase3_stats = phase3_timer.end()

    # 阶段4: 报告生成
    console.rule("[cyan]阶段4: 报告生成[/cyan]")
    phase4_timer = BenchmarkTimer("报告生成阶段")
    phase4_timer.start()
    generate_reports(cert_info, output_dir)
    phase4_stats = phase4_timer.end()

    # 总结
    main_stats = main_timer.end()

    # 打印详细统计报告
    print_benchmark_summary({
        'total': main_stats,
        'phase1_hash_extraction': phase1_stats,
        'phase2_gpu_cracking': phase2_stats,
        'phase3_cert_extraction': phase3_stats,
        'phase4_report_generation': phase4_stats
    })
```

### 方案2: 使用Rich Progress Bar（高级场景）

#### Rich进度条集成
```python
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
    TransferSpeedColumn
)
from rich.console import Console

console = Console()


class RichBenchmarkTimer:
    """使用Rich进度条的高级计时器"""

    def __init__(self, task_name: str, total_items: int = 0):
        self.task_name = task_name
        self.total_items = total_items
        self.start_time = None
        self.end_time = None
        self.progress = None
        self.task_id = None

    def __enter__(self):
        """上下文管理器入口"""
        self.start_time = time.time()

        # 创建Rich进度条
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            TextColumn("•"),
            TransferSpeedColumn(),
            console=console
        )

        self.progress.start()
        self.task_id = self.progress.add_task(
            self.task_name,
            total=self.total_items
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.end_time = time.time()
        self.progress.stop()

        elapsed = self.end_time - self.start_time
        console.print(f"\n[green]✅ {self.task_name} 完成![/green]")
        console.print(f"[yellow]总耗时: {timedelta(seconds=int(elapsed))}[/yellow]\n")

    def update(self, advance: int = 1):
        """更新进度"""
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, advance=advance)

    def set_description(self, description: str):
        """更新任务描述"""
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, description=description)


# 使用示例
def extract_hashes_with_rich(keystore_files: List[Path]) -> List[str]:
    """使用Rich进度条的Hash提取"""

    hashes = []

    with RichBenchmarkTimer("提取JKS Hash", total_items=len(keystore_files)) as timer:
        for keystore_file in keystore_files:
            # 更新当前处理文件
            timer.set_description(f"处理: {keystore_file.name}")

            # 提取hash
            hash_result = extract_single_hash(keystore_file)
            if hash_result:
                hashes.append(hash_result)

            # 更新进度
            timer.update(1)

    return hashes
```

### 方案3: 综合统计报告生成

#### Benchmark统计保存和报告
```python
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import pandas as pd


class BenchmarkReporter:
    """Benchmark统计报告生成器"""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.stats_history: List[Dict] = []

    def save_stats(self, stage_name: str, stats: TimingStats, metadata: Dict = None):
        """保存单个阶段的统计数据"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'stage': stage_name,
            'elapsed_seconds': stats.elapsed_seconds,
            'elapsed_formatted': stats.elapsed_formatted,
            'total_items': stats.total_items,
            'completed_items': stats.completed_items,
            'speed': stats.speed,
            'metadata': metadata or {}
        }

        self.stats_history.append(record)

        # 保存到JSON
        json_file = self.output_dir / "benchmark_stats.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats_history, f, indent=2, ensure_ascii=False)

    def generate_summary_report(self, output_file: str = None):
        """生成汇总报告"""
        if not self.stats_history:
            console.print("[yellow]没有统计数据[/yellow]")
            return

        # 创建DataFrame
        df = pd.DataFrame(self.stats_history)

        # 生成Excel报告
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"benchmark_report_{timestamp}.xlsx"

        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Sheet 1: 详细统计
            df.to_excel(writer, sheet_name='详细统计', index=False)

            # Sheet 2: 汇总统计
            summary = pd.DataFrame([{
                '总阶段数': len(df),
                '总耗时（秒）': df['elapsed_seconds'].sum(),
                '总耗时（格式化）': str(timedelta(seconds=int(df['elapsed_seconds'].sum()))),
                '总处理项目数': df['total_items'].sum(),
                '平均处理速度': df['speed'].mean(),
            }])
            summary.to_excel(writer, sheet_name='汇总统计', index=False)

            # Sheet 3: 各阶段占比
            stage_stats = df.groupby('stage').agg({
                'elapsed_seconds': 'sum',
                'total_items': 'sum',
                'speed': 'mean'
            }).reset_index()
            stage_stats['耗时占比%'] = (stage_stats['elapsed_seconds'] / df['elapsed_seconds'].sum() * 100).round(2)
            stage_stats.to_excel(writer, sheet_name='各阶段占比', index=False)

        console.print(f"[green]✅ Benchmark报告已生成: {output_file}[/green]")

        # 打印终端摘要
        self.print_terminal_summary()

    def print_terminal_summary(self):
        """在终端打印摘要"""
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]        Benchmark 统计摘要[/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

        df = pd.DataFrame(self.stats_history)

        # 各阶段统计
        for stage in df['stage'].unique():
            stage_data = df[df['stage'] == stage].iloc[0]
            console.print(f"[yellow]📊 {stage}[/yellow]")
            console.print(f"  ⏱️  耗时: {stage_data['elapsed_formatted']}")
            console.print(f"  📦 处理数: {stage_data['completed_items']}/{stage_data['total_items']}")
            console.print(f"  ⚡ 速度: {stage_data['speed']:.2f} items/秒")
            console.print()

        # 总计
        total_time = df['elapsed_seconds'].sum()
        total_items = df['total_items'].sum()

        console.print("[bold green]📈 总计[/bold green]")
        console.print(f"  ⏱️  总耗时: {timedelta(seconds=int(total_time))}")
        console.print(f"  📦 总处理数: {total_items}")
        console.print(f"  ⚡ 平均速度: {df['speed'].mean():.2f} items/秒")
        console.print()
```

## 📊 完整使用示例

### 在cli_batch_crack.py中集成完整Benchmark

```python
def main():
    """完整批量破解流程 with Benchmark"""

    # 初始化Benchmark报告器
    reporter = BenchmarkReporter(output_dir / "benchmarks")

    # 总流程计时
    total_timer = BenchmarkTimer("完整批量破解流程")
    total_timer.start()

    try:
        # ═══════════════════════════════════════
        # 阶段1: Hash提取
        # ═══════════════════════════════════════
        console.rule("[bold cyan]阶段1: Hash提取[/bold cyan]")

        keystore_files = scan_keystore_files(cert_dir)

        with RichBenchmarkTimer("提取JKS Hash", total_items=len(keystore_files)) as hash_timer:
            hash_file = extract_hashes(keystore_files, hash_timer)

        # 保存阶段1统计
        phase1_stats = TimingStats(
            start_time=hash_timer.start_time,
            end_time=hash_timer.end_time,
            total_items=len(keystore_files),
            completed_items=len(keystore_files)
        )
        reporter.save_stats("Hash提取", phase1_stats, {
            'files_scanned': len(keystore_files),
            'hashes_extracted': count_hashes(hash_file)
        })

        # ═══════════════════════════════════════
        # 阶段2: GPU破解
        # ═══════════════════════════════════════
        console.rule("[bold cyan]阶段2: GPU破解[/bold cyan]")

        phase2_timer = BenchmarkTimer("Hashcat GPU破解")
        phase2_timer.start()

        crack_results = crack_with_hashcat(hash_file, mask)

        phase2_stats = phase2_timer.end()
        reporter.save_stats("GPU破解", phase2_stats, {
            'total_hashes': len(crack_results['all']),
            'cracked_count': len(crack_results['cracked']),
            'crack_rate': f"{len(crack_results['cracked'])/len(crack_results['all'])*100:.1f}%"
        })

        # ═══════════════════════════════════════
        # 阶段3: 证书信息提取（多进程）
        # ═══════════════════════════════════════
        console.rule("[bold cyan]阶段3: 证书信息提取[/bold cyan]")

        phase3_timer = BenchmarkTimer("证书信息提取（多进程）", total_items=len(crack_results['cracked']))
        phase3_timer.start()

        cert_info = extract_certificates_parallel(crack_results['cracked'], phase3_timer)

        phase3_stats = phase3_timer.end()
        reporter.save_stats("证书提取", phase3_stats, {
            'certificates_extracted': len(cert_info),
            'parallel_processes': cpu_count() - 1
        })

        # ═══════════════════════════════════════
        # 阶段4: 报告生成
        # ═══════════════════════════════════════
        console.rule("[bold cyan]阶段4: 报告生成[/bold cyan]")

        phase4_timer = BenchmarkTimer("报告生成")
        phase4_timer.start()

        report_files = generate_reports(cert_info, crack_results, output_dir)

        phase4_stats = phase4_timer.end()
        reporter.save_stats("报告生成", phase4_stats, {
            'reports_generated': len(report_files)
        })

    finally:
        # 总计
        total_stats = total_timer.end()
        reporter.save_stats("总计", total_stats)

        # 生成最终Benchmark报告
        reporter.generate_summary_report()


if __name__ == "__main__":
    main()
```

## 📈 预期输出示例

### 终端输出
```
═══════════════════════════════════════════════════════════
                    阶段1: Hash提取
═══════════════════════════════════════════════════════════

⏱️  JKS Hash批量提取 开始...
开始时间: 2025-11-20 14:30:00
总任务数: 70

⠋ 提取JKS Hash ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 20/70 • 0:00:15 • 0:00:37 • 1.3 it/s

📊 进度统计:
  进度: 20/70 (28.6%)
  已用时间: 0:00:15
  预计剩余: 0:00:37
  预计总时间: 0:00:52
  处理速度: 1.33 items/秒

✅ JKS Hash批量提取 完成!
结束时间: 2025-11-20 14:31:05
总耗时: 0:01:05
完成数量: 70/70
平均速度: 1.08 items/秒

═══════════════════════════════════════════════════════════
                    阶段2: GPU破解
═══════════════════════════════════════════════════════════

⏱️  Hashcat GPU破解 开始...
开始时间: 2025-11-20 14:31:05

破解进度: 45/70
已用: 0:03:20 | 预计剩余: 0:01:50

✅ Hashcat GPU破解 完成!
结束时间: 2025-11-20 14:36:25
总耗时: 0:05:20

═══════════════════════════════════════════════════════════
        Benchmark 统计摘要
═══════════════════════════════════════════════════════════

📊 Hash提取
  ⏱️  耗时: 0:01:05
  📦 处理数: 70/70
  ⚡ 速度: 1.08 items/秒

📊 GPU破解
  ⏱️  耗时: 0:05:20
  📦 处理数: 45/70
  ⚡ 速度: 0.14 items/秒

📊 证书提取
  ⏱️  耗时: 0:00:38
  📦 处理数: 45/45
  ⚡ 速度: 1.18 items/秒

📊 报告生成
  ⏱️  耗时: 0:00:02
  📦 处理数: 2/2
  ⚡ 速度: 1.00 items/秒

📈 总计
  ⏱️  总耗时: 0:07:05
  📦 总处理数: 162
  ⚡ 平均速度: 0.76 items/秒

✅ Benchmark报告已生成: batch_crack_output/benchmarks/benchmark_report_20251120_143625.xlsx
```

### Excel报告结构

#### Sheet 1: 详细统计
| timestamp | stage | elapsed_seconds | elapsed_formatted | total_items | completed_items | speed | metadata |
|-----------|-------|-----------------|-------------------|-------------|-----------------|-------|----------|
| 2025-11-20T14:31:05 | Hash提取 | 65.23 | 0:01:05 | 70 | 70 | 1.08 | {"files_scanned": 70, ...} |
| 2025-11-20T14:36:25 | GPU破解 | 320.45 | 0:05:20 | 70 | 45 | 0.14 | {"cracked_count": 45, ...} |
| ... | ... | ... | ... | ... | ... | ... | ... |

#### Sheet 2: 汇总统计
| 总阶段数 | 总耗时（秒） | 总耗时（格式化） | 总处理项目数 | 平均处理速度 |
|---------|-------------|-----------------|-------------|-------------|
| 5 | 425.50 | 0:07:05 | 162 | 0.76 |

#### Sheet 3: 各阶段占比
| stage | elapsed_seconds | total_items | speed | 耗时占比% |
|-------|-----------------|-------------|-------|----------|
| Hash提取 | 65.23 | 70 | 1.08 | 15.3% |
| GPU破解 | 320.45 | 70 | 0.14 | 75.3% |
| 证书提取 | 38.12 | 45 | 1.18 | 9.0% |
| 报告生成 | 1.70 | 2 | 1.00 | 0.4% |

## 🔧 配置选项

### 环境变量配置
```bash
# 启用详细Benchmark
export ENABLE_BENCHMARK=true

# Benchmark输出目录
export BENCHMARK_OUTPUT_DIR="./benchmarks"

# 进度更新频率（秒）
export PROGRESS_UPDATE_INTERVAL=2
```

### 代码配置
```python
# config.py
BENCHMARK_CONFIG = {
    'enabled': True,
    'output_dir': Path('./benchmarks'),
    'save_json': True,
    'save_excel': True,
    'print_terminal_summary': True,
    'progress_update_interval': 2,  # 秒
    'detailed_timing': True,  # 记录每个文件的处理时间
}
```

## 🎯 性能优化建议

### 减少时间统计开销
```python
# 方案1: 批量更新进度（减少锁竞争）
batch_size = 10
for i, item in enumerate(items):
    process_item(item)
    if i % batch_size == 0:
        timer.update_progress(i)

# 方案2: 异步统计（不阻塞主线程）
from threading import Thread

def async_update_stats(timer, completed):
    Thread(target=timer.update_progress, args=(completed,), daemon=True).start()
```

## 📝 最佳实践

1. **分层计时**: 为整体流程和各个子阶段分别计时
2. **实时反馈**: 每隔2-5秒更新一次进度显示
3. **保存历史**: 将每次运行的Benchmark保存到JSON/Excel
4. **对比分析**: 保留多次运行记录，便于性能对比
5. **元数据记录**: 记录环境信息（CPU、GPU型号、系统版本等）

## 🚀 下一步

### 集成到现有代码
1. 在`extractor_jks_hash.py`中添加Hash提取计时
2. 在`cracker_hashcat_gpu.py`中添加GPU破解实时进度
3. 在`analyzer_crack_result.py`中添加多进程并行统计
4. 在`cli_batch_crack.py`中集成完整Benchmark报告

### 扩展功能
- [ ] GPU性能监控（温度、利用率、内存）
- [ ] 网络统计（如果涉及远程资源）
- [ ] 内存使用统计
- [ ] 自动生成性能对比图表
- [ ] Benchmark历史趋势分析

## 📚 参考资源

- [Rich库文档](https://rich.readthedocs.io/)
- [Python time模块](https://docs.python.org/3/library/time.html)
- [Python multiprocessing性能监控](https://docs.python.org/3/library/multiprocessing.html)
