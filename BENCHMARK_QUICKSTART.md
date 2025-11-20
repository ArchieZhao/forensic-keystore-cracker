# Benchmark功能快速开始指南

## 🚀 立即使用

### 方式1：直接运行完整流程（推荐）

运行批量破解CLI工具，自动记录所有阶段的时间统计：

```bash
python cli_batch_crack.py
```

完成后会自动生成：
- `batch_crack_output/benchmarks/benchmark_stats.json` - JSON统计数据
- `batch_crack_output/benchmarks/benchmark_report_*.xlsx` - Excel详细报告
- 终端显示完整的性能摘要

### 方式2：单独运行各阶段

#### Hash提取（带时间统计）
```bash
python extractor_jks_hash.py
```

输出示例：
```
✅ Hash提取完成
⚡ 提取性能: 1.08 文件/秒
⏱️  平均单文件耗时: 0.93秒
```

#### GPU破解（带时间统计）
```bash
python cracker_hashcat_gpu.py hash.txt
```

每10个hash会显示：
```
📊 进度统计:
  进度: 20/70 (28.6%)
  已用时间: 0:00:15
  预计剩余: 0:00:37
  预计总时间: 0:00:52
  处理速度: 1.33 items/秒
```

#### 结果分析（带时间统计）
```bash
python analyzer_crack_result.py
```

输出多进程性能统计：
```
⚡ 证书提取性能（多进程）:
  工作进程数: 15
  提取速度: 1.18 证书/秒
  单证书平均耗时: 0.85秒
  串行预估耗时: 63.8秒
  实际耗时: 38.1秒
  性能提升: 15.0x (理论) / 12.8x (实际)
```

## 📊 查看Benchmark报告

### 终端查看
运行 `cli_batch_crack.py` 后，终端会自动显示完整的性能摘要。

### Excel查看
打开 `batch_crack_output/benchmarks/benchmark_report_*.xlsx`，包含：
- **详细统计** - 每个阶段的完整数据
- **汇总统计** - 总体性能
- **各阶段占比** - 耗时占比分析

### JSON查看
```bash
cat batch_crack_output/benchmarks/benchmark_stats.json
```

或使用Python解析：
```python
import json
with open('batch_crack_output/benchmarks/benchmark_stats.json') as f:
    data = json.load(f)
    for record in data:
        print(f"{record['stage']}: {record['elapsed_formatted']}")
```

## 🔧 在自己的代码中使用

### 基础示例
```python
from benchmark_timer import BenchmarkTimer

# 创建计时器
timer = BenchmarkTimer("我的任务", total_items=100)
timer.start()

# 执行任务
for i in range(100):
    # 你的代码
    do_something(i)

    # 更新进度
    timer.update_progress(i + 1)

    # 每10个显示一次进度
    if (i + 1) % 10 == 0:
        timer.print_progress()

# 结束并显示统计
stats = timer.end()
```

### 使用上下文管理器（更简洁）
```python
from benchmark_timer import timer

with timer("我的任务", total_items=100) as t:
    for i in range(100):
        do_something(i)
        t.update_progress(i + 1)
```

### 添加检查点
```python
timer = BenchmarkTimer("多阶段任务")
timer.start()

# 阶段1
process_phase1()
timer.checkpoint("阶段1完成")

# 阶段2
process_phase2()
timer.checkpoint("阶段2完成")

# 阶段3
process_phase3()
timer.checkpoint("阶段3完成")

# 自动显示所有检查点统计
stats = timer.end()
```

### 生成报告
```python
from pathlib import Path
from benchmark_timer import BenchmarkReporter

# 创建报告器
reporter = BenchmarkReporter(Path("my_benchmarks"))

# 保存各阶段统计
reporter.save_stats("阶段1", phase1_stats, {
    'files_processed': 70,
    'success_count': 68
})

reporter.save_stats("阶段2", phase2_stats, {
    'hashes_cracked': 45
})

# 生成最终报告
reporter.generate_summary_report()
```

## 📈 典型输出示例

### 完整流程输出
```
═══════════════════════════════════════
        Benchmark 统计摘要
═══════════════════════════════════════

📊 阶段1-Hash提取
  ⏱️  耗时: 0:01:05
  📦 处理数: 70/70
  ⚡ 速度: 1.08 items/秒
  📋 files: 70
  📋 success: 68

📊 阶段2-GPU破解
  ⏱️  耗时: 0:05:20
  📦 处理数: 45/70
  ⚡ 速度: 0.14 items/秒
  📋 hashes: 68
  📋 cracked: 45

📊 阶段3-结果分析
  ⏱️  耗时: 0:00:38
  📦 处理数: 45/45
  ⚡ 速度: 1.18 items/秒
  📋 certificates: 45

📈 总计
  ⏱️  总耗时: 0:07:05
  📦 总处理数: 185
  ⚡ 平均速度: 0.76 items/秒

✅ Benchmark报告已生成: batch_crack_output/benchmarks/benchmark_report_20251120_143625.xlsx
```

## ⚡ 性能优化建议

### 1. 避免频繁输出
```python
# 不推荐：每次都打印
for i in range(1000):
    timer.update_progress(i + 1)
    timer.print_progress()  # 太频繁！

# 推荐：每N个打印一次
for i in range(1000):
    timer.update_progress(i + 1)
    if (i + 1) % 100 == 0:
        timer.print_progress()  # 每100个打印
```

### 2. 配合progress bar使用
```python
from rich.progress import Progress

timer = BenchmarkTimer("任务", total_items=100, verbose=False)  # 关闭详细输出
timer.start()

with Progress() as progress:
    task = progress.add_task("处理中...", total=100)
    for i in range(100):
        do_work(i)
        timer.update_progress(i + 1)
        progress.update(task, advance=1)

stats = timer.end()  # 仍然显示最终统计
```

### 3. 仅在需要时使用
```python
# 对于非常快的操作，可以不使用timer
if task_is_long_running:
    with timer("长任务", total_items=n) as t:
        for i in range(n):
            slow_operation(i)
            t.update_progress(i + 1)
else:
    # 直接执行
    for i in range(n):
        fast_operation(i)
```

## 🐛 故障排查

### 问题1：时间不准确
```python
# 确保在循环外创建timer
timer = BenchmarkTimer("任务", total_items=100)  # ✅ 正确
timer.start()

for i in range(100):
    # timer = BenchmarkTimer(...)  # ❌ 错误：每次都创建新的
    do_work(i)
```

### 问题2：进度不显示
```python
# 必须设置total_items才能显示进度
timer = BenchmarkTimer("任务", total_items=100)  # ✅ 有total_items
timer.start()

for i in range(100):
    do_work(i)
    timer.update_progress(i + 1)  # 必须调用
```

### 问题3：Excel报告未生成
确保安装了依赖：
```bash
pip install openpyxl pandas
```

如果没有安装，会跳过Excel生成但仍然生成JSON报告。

## 📚 更多资源

- [BENCHMARK_TIMING.md](BENCHMARK_TIMING.md) - 完整实现指南
- [BENCHMARK_IMPLEMENTATION_SUMMARY.md](BENCHMARK_IMPLEMENTATION_SUMMARY.md) - 实现总结
- [benchmark_timer.py](benchmark_timer.py) - 源代码（包含完整注释）
- [test_benchmark_simple.py](test_benchmark_simple.py) - 功能测试示例

## 🎯 常见用例

### 用例1：测试不同算法性能
```python
algorithms = ['algo1', 'algo2', 'algo3']
reporter = BenchmarkReporter(Path("algo_comparison"))

for algo_name in algorithms:
    timer = BenchmarkTimer(f"测试{algo_name}", total_items=1000)
    timer.start()

    for i in range(1000):
        run_algorithm(algo_name, i)
        timer.update_progress(i + 1)

    stats = timer.end()
    reporter.save_stats(algo_name, stats)

reporter.generate_summary_report()
# 对比各算法性能
```

### 用例2：监控批量任务
```python
files = get_file_list()
timer = BenchmarkTimer("批量处理文件", total_items=len(files))
timer.start()

for i, file in enumerate(files):
    process_file(file)
    timer.update_progress(i + 1)

    # 每10%打印一次
    if (i + 1) % (len(files) // 10) == 0:
        timer.print_progress()

timer.end()
```

### 用例3：多阶段流程追踪
```python
timer = BenchmarkTimer("数据处理流程")
timer.start()

# 阶段1
timer.checkpoint("开始数据加载")
data = load_data()
timer.checkpoint("数据加载完成")

# 阶段2
timer.checkpoint("开始数据清洗")
clean_data = clean(data)
timer.checkpoint("数据清洗完成")

# 阶段3
timer.checkpoint("开始数据分析")
results = analyze(clean_data)
timer.checkpoint("数据分析完成")

# 显示各阶段耗时
stats = timer.end()
```

## 💡 最佳实践

1. **总是使用有意义的任务名称**
   ```python
   timer = BenchmarkTimer("Hash提取")  # ✅ 清晰
   timer = BenchmarkTimer("Task1")      # ❌ 含糊
   ```

2. **为长时间任务提供total_items**
   ```python
   timer = BenchmarkTimer("任务", total_items=len(items))  # ✅
   ```

3. **定期更新进度但不要太频繁**
   ```python
   if i % 10 == 0:  # 每10个更新一次
       timer.update_progress(i)
   ```

4. **使用元数据记录上下文信息**
   ```python
   reporter.save_stats("阶段1", stats, {
       'file_count': 70,
       'success_rate': '97.1%',
       'gpu_model': 'RTX 3080'
   })
   ```

5. **在finally块中确保timer.end()被调用**
   ```python
   timer = BenchmarkTimer("任务")
   timer.start()
   try:
       do_work()
   finally:
       timer.end()  # 确保总是结束
   ```

开始使用Benchmark功能，追踪和优化你的代码性能吧！🚀
