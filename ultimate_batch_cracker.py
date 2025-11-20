#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量JKS破解自动化流程编排器

整合batch_hash_extractor、hashcat GPU破解、batch_result_analyzer三步流程，
自动化完成：Hash提取 → GPU掩码攻击 → 证书信息提取 → Excel/JSON报告生成，
支持rich交互式确认、断点续传、实时进度显示、会话恢复。

Architecture:
    环境检查 → Hash提取 → GPU破解 → 结果分析 → 报告生成

    UltimateBatchCracker (ultimate_batch_cracker.py:20)
        ├─ __init__() (L21): 初始化certificate_dir、output_dir、关键文件路径
        ├─ show_banner() (L38): rich Panel显示启动横幅
        ├─ check_prerequisites() (L47): 检查6个前置条件（目录/工具/依赖）
        ├─ _check_java() (L69): subprocess.run(['java', '-version'])测试Java环境
        ├─ _check_gpu() (L76): subprocess.run(['nvidia-smi'])测试GPU状态
        ├─ _check_python_deps() (L88): 检查rich和openpyxl导入
        ├─ step1_extract_hashes() (L96): 调用BatchHashExtractor.run()提取hash
        ├─ step2_gpu_cracking() (L130): 构建hashcat命令并执行GPU破解（16个参数）
        ├─ step3_analyze_results() (L259): 调用BatchResultAnalyzer.analyze_and_report()
        ├─ show_final_summary() (L297): 显示3步状态 + 4个输出文件检查
        └─ run() (L352): 主流程编排，异常处理 + finally总结

Features:
    - 三步自动化流程：Hash提取 → GPU破解 → 结果分析 (ultimate_batch_cracker.py:96, 130, 259)
    - 6项环境检查：Certificate目录、JksPrivkPrepare.jar、Hashcat、Java、GPU、Python依赖 (ultimate_batch_cracker.py:51-58)
    - rich交互式确认：3次Confirm.ask（重新提取/重新破解/开始破解）(ultimate_batch_cracker.py:103, 142, 169)
    - hashcat参数优化：16个参数含RTX 3080优化（-O, -w 4, --markov-disable, --segment-size 32）(ultimate_batch_cracker.py:190-207)
    - 绝对路径处理：resolve()避免工作目录问题 (ultimate_batch_cracker.py:186-187)
    - 会话恢复支持：--session ultimate_batch_crack（可用--restore恢复）(ultimate_batch_cracker.py:204, 251)
    - 实时输出：subprocess.Popen实时打印hashcat进度 (ultimate_batch_cracker.py:227-232)
    - 步骤状态跟踪：3个布尔标志记录完成状态 (ultimate_batch_cracker.py:32-36)
    - 最终总结：3步状态表 + 4个输出文件检查（含glob通配符）(ultimate_batch_cracker.py:297-343)

Args (命令行):
    certificate_dir (str, optional): keystore文件根目录，默认'certificate'

        示例：
        python ultimate_batch_cracker.py                    # 使用默认certificate目录
        python ultimate_batch_cracker.py my_certificates    # 使用自定义目录
        python ultimate_batch_cracker.py ../certs           # 使用相对路径
        python ultimate_batch_cracker.py /path/to/certs     # 使用绝对路径

Returns (输出文件):
    batch_crack_output/all_keystores.hash: 批量hash文件（$jksprivk$格式）
    batch_crack_output/batch_results.potfile: Hashcat破解结果（格式：hash:password）
    batch_crack_output/batch_crack_results_YYYYMMDD_HHMMSS.json: JSON详细报告
    batch_crack_output/batch_crack_results_YYYYMMDD_HHMMSS.xlsx: Excel详细报告（2个工作表）

Requirements:
    - batch_hash_extractor.py (Hash提取器)
    - batch_result_analyzer.py (结果分析器)
    - hashcat-6.2.6/hashcat.exe (GPU破解引擎)
    - JKS-private-key-cracker-hashcat/JksPrivkPrepare.jar (Hash生成工具)
    - Java Runtime Environment (JRE 8+)
    - NVIDIA GPU + nvidia-smi (可选，GPU检查失败不阻塞)
    - rich (交互式UI)
    - openpyxl (Excel导出)

Technical Notes:
    三步流程编排:
        步骤1 - Hash提取 (ultimate_batch_cracker.py:96-128):
            调用: BatchHashExtractor(certificate_dir).run()
            检查: batch_hash_file.exists()确认成功
            交互: 已存在时Confirm.ask("是否重新提取hash?")
            输出: batch_crack_output/all_keystores.hash

        步骤2 - GPU破解 (ultimate_batch_cracker.py:130-257):
            调用: subprocess.Popen(hashcat_cmd, cwd=hashcat.parent)
            参数: 16个hashcat参数（-m 15500, -a 3, ?1?1?1?1?1?1等）
            交互: 已存在时Confirm.ask("是否重新开始破解?")，开始前Confirm.ask("确认开始GPU破解?")
            输出: batch_crack_output/batch_results.potfile

        步骤3 - 结果分析 (ultimate_batch_cracker.py:259-295):
            调用: BatchResultAnalyzer().analyze_and_report()
            检查: potfile_path.exists()确认有结果
            交互: 不存在时Confirm.ask("是否继续分析（可能没有结果）?")
            输出: batch_crack_results_YYYYMMDD_HHMMSS.json + .xlsx

    环境检查6项 (ultimate_batch_cracker.py:51-58):
        1. Certificate目录: self.certificate_dir.exists()
        2. JksPrivkPrepare.jar: Path("JKS-private-key-cracker-hashcat/JksPrivkPrepare.jar").exists()
        3. Hashcat: self.hashcat_path.exists()
        4. Java环境: subprocess.run(['java', '-version']).returncode == 0
        5. GPU状态: subprocess.run(['nvidia-smi']).returncode == 0（失败返回True继续）
        6. Python依赖: import rich; import openpyxl

    hashcat命令16个参数 (ultimate_batch_cracker.py:190-207):
        -m 15500: JKS私钥模式
        -a 3: 掩码攻击
        hash_file: 绝对路径（resolve()）
        -1 a-zA-Z0-9: 自定义字符集（62字符）
        ?1?1?1?1?1?1: 6位掩码
        --force: 强制运行
        -O: 优化内核
        -w 4: 最高工作负载
        --markov-disable: 禁用马尔可夫链
        --segment-size 32: 优化内存段
        --status: 显示状态
        --status-timer 60: 每分钟更新
        --session ultimate_batch_crack: 会话名（可用--restore恢复）
        --potfile-path: 绝对路径（resolve()）
        --outfile-format 1: 输出格式hash:password

    绝对路径处理 (ultimate_batch_cracker.py:186-187):
        abs_hash_file = self.batch_hash_file.resolve()
        abs_potfile = self.potfile_path.resolve()
        原因: hashcat在自己的工作目录执行，相对路径会失败

    工作目录设置 (ultimate_batch_cracker.py:218):
        cwd=str(self.hashcat_path.parent)
        原因: hashcat需要在hashcat-6.2.6目录执行以找到OpenCL等资源

    步骤状态跟踪 (ultimate_batch_cracker.py:32-36):
        self.steps = {
            'hash_extraction': False,  # 步骤1完成标志
            'gpu_cracking': False,     # 步骤2完成标志
            'result_analysis': False   # 步骤3完成标志
        }
        更新时机: 每步成功后设置为True（L116, L239, L283）
        用途: show_final_summary()显示完成状态表（L308-318）

    会话恢复机制 (ultimate_batch_cracker.py:204, 251):
        会话名: --session ultimate_batch_crack
        恢复命令: hashcat --session ultimate_batch_crack --restore
        中断处理: KeyboardInterrupt后提示用户可用--restore恢复（L251）
        状态保存: 中断时仍标记gpu_cracking=True允许进入步骤3（L253）

    输出文件检查 (ultimate_batch_cracker.py:322-343):
        4个文件: all_keystores.hash, batch_results.potfile,
                batch_crack_results_*.json, batch_crack_results_*.xlsx
        通配符处理: glob()查找最新文件max(files, key=st_mtime)（L332-334）

Workflow:
    1. 显示rich Panel启动横幅
    2. 检查6个前置条件（目录/工具/依赖）
    3. 步骤1 - Hash提取：
       - 检查all_keystores.hash是否存在
       - 若存在：Confirm.ask是否重新提取
       - 调用BatchHashExtractor(certificate_dir).run()
       - 验证batch_hash_file.exists()
    4. 步骤2 - GPU破解：
       - 检查batch_results.potfile是否存在
       - 若存在：Confirm.ask是否重新破解
       - 显示破解参数Table（8行）
       - 显示警告信息（66天预估时间）
       - Confirm.ask确认开始破解
       - 预创建空potfile（touch()）
       - resolve()生成绝对路径
       - 构建16个hashcat参数
       - subprocess.Popen(cwd=hashcat.parent)执行
       - 实时打印stdout
       - 检查return_code（0=成功，1=未找到密码，其他=错误）
    5. 步骤3 - 结果分析：
       - 检查potfile_path.exists()
       - 若不存在：Confirm.ask是否继续分析
       - 调用BatchResultAnalyzer().analyze_and_report()
       - 生成JSON和Excel报告
    6. finally显示最终总结：
       - 3步状态Table（✅完成/❌未完成）
       - 4个输出文件检查（glob通配符查找最新）
       - 4条重要提示

Author: Forensic Keystore Cracker Project
Version: 1.0.0
License: 仅用于授权的数字取证和安全研究
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm, Prompt

console = Console()

class UltimateBatchCracker:
    def __init__(self, certificate_dir="certificate"):
        self.certificate_dir = Path(certificate_dir)
        self.output_dir = Path("batch_crack_output")
        self.output_dir.mkdir(exist_ok=True)

        # 关键文件路径
        self.batch_hash_file = self.output_dir / "all_keystores.hash"
        self.potfile_path = self.output_dir / "batch_results.potfile"
        self.hashcat_path = Path("hashcat-6.2.6/hashcat.exe")

        # 步骤状态
        self.steps = {
            'hash_extraction': False,
            'gpu_cracking': False,
            'result_analysis': False
        }
    
    def show_banner(self):
        """显示启动横幅"""
        console.print(Panel.fit(
            "[bold cyan]🚀 终极批量JKS破解器[/bold cyan]\n"
            "[yellow]Windows 11 + i9-12900K + RTX 3080 专用版[/yellow]\n"
            "[green]解密 keystore × 6位字母数字密码[/green]",
            border_style="cyan"
        ))
    
    def check_prerequisites(self):
        """检查前置条件"""
        console.print("[cyan]🔍 系统环境检查...[/cyan]")

        checks = [
            (f"Certificate目录 ({self.certificate_dir})", self.certificate_dir.exists()),
            ("JksPrivkPrepare.jar", Path("JKS-private-key-cracker-hashcat/JksPrivkPrepare.jar").exists()),
            ("Hashcat", self.hashcat_path.exists()),
            ("Java环境", self._check_java()),
            ("GPU状态", self._check_gpu()),
            ("Python依赖", self._check_python_deps())
        ]
        
        all_good = True
        for name, status in checks:
            icon = "✅" if status else "❌"
            console.print(f"  {icon} {name}")
            if not status:
                all_good = False
        
        return all_good
    
    def _check_java(self):
        try:
            result = subprocess.run(['java', '-version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _check_gpu(self):
        try:
            result = subprocess.run(['nvidia-smi'], capture_output=True, timeout=5)
            if result.returncode == 0:
                # 如果nvidia-smi成功运行，就认为GPU可用（不强制要求RTX 3080）
                return True
            return False
        except:
            # 如果nvidia-smi不可用，发出警告但不阻止运行
            console.print("[yellow]  ⚠️ 无法检测GPU，但将继续运行（可能影响性能）[/yellow]")
            return True  # 改为True以允许继续执行
    
    def _check_python_deps(self):
        try:
            import rich
            import openpyxl
            return True
        except ImportError:
            return False
    
    def step1_extract_hashes(self):
        """步骤1: 批量提取hash"""
        console.print("\n" + "="*60)
        console.print("[bold yellow]步骤 1/3: 批量Hash提取[/bold yellow]")
        
        if self.batch_hash_file.exists():
            console.print(f"[green]✅ Hash文件已存在: {self.batch_hash_file}[/green]")
            if not Confirm.ask("是否重新提取hash?"):
                self.steps['hash_extraction'] = True
                return True
        
        console.print("[cyan]🔄 启动批量hash提取器...[/cyan]")
        
        try:
            # 调用批量hash提取器
            from batch_hash_extractor import BatchHashExtractor
            extractor = BatchHashExtractor(certificate_dir=str(self.certificate_dir))
            success = extractor.run()
            
            if success and self.batch_hash_file.exists():
                self.steps['hash_extraction'] = True
                console.print("[green]✅ Hash提取完成[/green]")
                return True
            else:
                console.print("[red]❌ Hash提取失败[/red]")
                return False
                
        except ImportError:
            console.print("[red]❌ 无法导入batch_hash_extractor模块[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Hash提取出错: {e}[/red]")
            return False
    
    def step2_gpu_cracking(self):
        """步骤2: GPU破解"""
        console.print("\n" + "="*60)
        console.print("[bold yellow]步骤 2/3: GPU批量破解[/bold yellow]")
        
        if not self.batch_hash_file.exists():
            console.print("[red]❌ Hash文件不存在，请先完成步骤1[/red]")
            return False
        
        # 检查是否已有破解结果
        if self.potfile_path.exists():
            console.print(f"[green]✅ 发现现有破解结果: {self.potfile_path}[/green]")
            if not Confirm.ask("是否重新开始破解?"):
                self.steps['gpu_cracking'] = True
                return True
        
        # 显示破解参数
        console.print("\n[cyan]🎯 破解参数配置:[/cyan]")
        params_table = Table(border_style="blue")
        params_table.add_column("参数", style="cyan")
        params_table.add_column("值", style="yellow")
        
        params_table.add_row("Hash文件", str(self.batch_hash_file))
        params_table.add_row("算法模式", "15500 (JKS私钥)")
        params_table.add_row("攻击模式", "掩码攻击 (-a 3)")
        params_table.add_row("字符集", "a-z,A-Z,0-9 (62字符)")
        params_table.add_row("掩码", "?1?1?1?1?1?1 (6位)")
        params_table.add_row("组合数", "62^6 = 56,800,235,584")
        params_table.add_row("预计时间", "约66天 (连续运行)")
        params_table.add_row("GPU优化", "RTX 3080专用参数")
        
        console.print(params_table)
        
        # 确认开始破解
        console.print("\n[red]⚠️ 重要警告:[/red]")
        console.print("[red]- 此过程预计需要约66天连续运行[/red]")
        console.print("[red]- 建议在稳定的环境中24/7运行[/red]")
        console.print("[red]- 可随时Ctrl+C中断，稍后用--restore恢复[/red]")
        
        if not Confirm.ask("\n🚀 确认开始GPU破解?"):
            console.print("[yellow]⏹️ 用户取消破解[/yellow]")
            return False
        
        # 确保输出目录存在
        self.potfile_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 🔧 修复：预创建空的potfile以避免hashcat路径问题
        if self.potfile_path.exists():
            console.print(f"[yellow]🗑️ 清理旧的破解结果...[/yellow]")
            self.potfile_path.unlink()
        
        # 创建空的potfile（hashcat期望文件存在）
        self.potfile_path.touch()
        console.print(f"[cyan]💡 结果将保存到: {self.potfile_path}[/cyan]")
        
        # 🔧 修复：使用绝对路径避免工作目录问题
        abs_hash_file = self.batch_hash_file.resolve()
        abs_potfile = self.potfile_path.resolve()
        
        # 构建hashcat命令
        cmd = [
            str(self.hashcat_path),
            "-m", "15500",                    # JKS私钥模式
            "-a", "3",                        # 掩码攻击
            str(abs_hash_file),               # 🔧 使用绝对路径
            "-1", "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",  # 自定义字符集
            "?1?1?1?1?1?1",                   # 6位掩码
            "--force",                        # 强制运行
            "-O",                            # 优化内核
            "-w", "4",                       # 最高工作负载
            "--markov-disable",              # 禁用马尔可夫链
            "--segment-size", "32",          # 优化内存段
            "--status",                      # 显示状态
            "--status-timer", "60",          # 每分钟更新状态
            "--session", "ultimate_batch_crack", # 会话名
            "--potfile-path", str(abs_potfile),  # 🔧 使用绝对路径
            "--outfile-format", "1"              # 输出格式：hash:password
        ]
        
        console.print("\n[cyan]执行命令:[/cyan]")
        console.print(" ".join(cmd))
        console.print("\n" + "="*60)
        console.print("[bold green]🚀 开始GPU破解... (Ctrl+C可安全中断)[/bold green]")
        
        try:
            # 在hashcat目录执行
            process = subprocess.Popen(
                cmd,
                cwd=str(self.hashcat_path.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 实时输出
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
            
            return_code = process.poll()
            console.print(f"\n破解完成，返回码: {return_code}")
            
            if return_code == 0:
                console.print("[green]🎉 密码破解成功！[/green]")
                self.steps['gpu_cracking'] = True
                return True
            elif return_code == 1:
                console.print("[yellow]⚠️ 破解完成但未找到密码[/yellow]")
                self.steps['gpu_cracking'] = True
                return True
            else:
                console.print("[red]❌ 破解过程出现错误[/red]")
                return False
                
        except KeyboardInterrupt:
            console.print("\n[yellow]⏹️ 用户中断破解[/yellow]")
            console.print("[cyan]💡 可以稍后使用 --restore 恢复会话[/cyan]")
            # 即使中断也认为这一步完成了（可以恢复）
            self.steps['gpu_cracking'] = True
            return True
        except Exception as e:
            console.print(f"[red]❌ 破解执行失败: {e}[/red]")
            return False
    
    def step3_analyze_results(self):
        """步骤3: 结果分析"""
        console.print("\n" + "="*60)
        console.print("[bold yellow]步骤 3/3: 结果分析与报告生成[/bold yellow]")
        
        if not self.potfile_path.exists():
            console.print("[yellow]⚠️ 未找到破解结果文件[/yellow]")
            console.print("[cyan]💡 这可能意味着:[/cyan]")
            console.print("[cyan]- 破解尚未完成[/cyan]")
            console.print("[cyan]- 所有密码都没有被找到[/cyan]")
            console.print("[cyan]- 破解过程出现了问题[/cyan]")
            
            if not Confirm.ask("是否继续分析（可能没有结果）?"):
                return False
        
        console.print("[cyan]🔍 启动结果分析器...[/cyan]")
        
        try:
            # 调用结果分析器
            from batch_result_analyzer import BatchResultAnalyzer
            analyzer = BatchResultAnalyzer()
            success = analyzer.analyze_and_report()
            
            if success:
                self.steps['result_analysis'] = True
                console.print("[green]✅ 结果分析完成[/green]")
                return True
            else:
                console.print("[red]❌ 结果分析失败[/red]")
                return False
                
        except ImportError:
            console.print("[red]❌ 无法导入batch_result_analyzer模块[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ 结果分析出错: {e}[/red]")
            return False
    
    def show_final_summary(self):
        """显示最终总结"""
        console.print("\n" + "="*60)
        console.print("[bold cyan]🎯 任务完成总结[/bold cyan]")
        
        # 显示步骤完成状态
        steps_table = Table(title="执行步骤状态", border_style="green")
        steps_table.add_column("步骤", style="cyan")
        steps_table.add_column("状态", style="yellow")
        steps_table.add_column("说明", style="white")
        
        step_info = [
            ("1. Hash提取", self.steps['hash_extraction'], "从70个keystore提取$jksprivk$格式hash"),
            ("2. GPU破解", self.steps['gpu_cracking'], "使用RTX 3080进行6位密码破解"),
            ("3. 结果分析", self.steps['result_analysis'], "生成包含MD5/SHA1的详细报告")
        ]
        
        for step, status, desc in step_info:
            status_icon = "✅ 完成" if status else "❌ 未完成"
            steps_table.add_row(step, status_icon, desc)
        
        console.print(steps_table)
        
        # 显示输出文件
        console.print("\n[bold green]📁 生成的文件:[/bold green]")
        files_to_check = [
            (self.batch_hash_file, "批量hash文件"),
            (self.potfile_path, "破解结果文件"),
            (self.output_dir / "batch_crack_results_*.json", "JSON详细报告"),
            (self.output_dir / "batch_crack_results_*.xlsx", "Excel详细报告")
        ]
        
        for file_path, description in files_to_check:
            if '*' in str(file_path):
                # 通配符文件，查找最新的
                files = list(file_path.parent.glob(file_path.name))
                if files:
                    latest_file = max(files, key=lambda f: f.stat().st_mtime)
                    console.print(f"[green]✅ {description}: {latest_file}[/green]")
                else:
                    console.print(f"[yellow]⚠️ {description}: 未找到[/yellow]")
            else:
                if file_path.exists():
                    size = file_path.stat().st_size
                    console.print(f"[green]✅ {description}: {file_path} ({size} bytes)[/green]")
                else:
                    console.print(f"[yellow]⚠️ {description}: 未生成[/yellow]")
        
        # 显示重要提示
        console.print("\n[bold yellow]💡 重要提示:[/bold yellow]")
        console.print("[yellow]- 如果GPU破解被中断，可以使用hashcat的--restore功能恢复[/yellow]")
        console.print("[yellow]- 破解过程中可以随时检查batch_results.potfile查看进度[/yellow]")
        console.print("[yellow]- 完整的6位密码破解可能需要数周时间[/yellow]")
        console.print("[yellow]- 建议定期备份potfile以防数据丢失[/yellow]")
    
    def run(self):
        """执行完整的批量破解流程"""
        self.show_banner()
        
        # 前置检查
        if not self.check_prerequisites():
            console.print("\n[red]❌ 环境检查失败，请解决上述问题后重试[/red]")
            return False
        
        console.print("\n[green]✅ 环境检查通过，准备开始批量破解[/green]")
        
        # 执行三个主要步骤
        try:
            # 步骤1: 提取hash
            if not self.step1_extract_hashes():
                console.print("[red]❌ 步骤1失败，无法继续[/red]")
                return False
            
            # 步骤2: GPU破解
            if not self.step2_gpu_cracking():
                console.print("[red]❌ 步骤2失败，无法继续[/red]")
                return False
            
            # 步骤3: 结果分析
            if not self.step3_analyze_results():
                console.print("[yellow]⚠️ 步骤3失败，但破解可能已完成[/yellow]")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]⏹️ 用户中断操作[/yellow]")
        except Exception as e:
            console.print(f"\n[red]💥 未预期的错误: {e}[/red]")
            return False
        finally:
            # 无论如何都显示总结
            self.show_final_summary()
        
        console.print("\n[bold green]🎉 批量破解流程完成！[/bold green]")
        return True

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="终极批量JKS破解器 - 一键完成Hash提取、GPU破解、结果分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python ultimate_batch_cracker.py                    # 使用默认的certificate目录
  python ultimate_batch_cracker.py my_certificates    # 使用自定义目录
  python ultimate_batch_cracker.py ../certs           # 使用相对路径
  python ultimate_batch_cracker.py /path/to/certs     # 使用绝对路径
        """
    )

    parser.add_argument(
        'certificate_dir',
        nargs='?',
        default='certificate',
        help='包含keystore文件的目录路径 (默认: certificate)'
    )

    args = parser.parse_args()

    console.print("=" * 80)
    console.print("[bold cyan]终极批量JKS破解器 v1.0[/bold cyan]")
    console.print("[yellow]专为Windows 11 + RTX 3080 + 70个keystore优化[/yellow]")
    console.print(f"[green]目标目录: {args.certificate_dir}[/green]")
    console.print("=" * 80)

    cracker = UltimateBatchCracker(certificate_dir=args.certificate_dir)
    success = cracker.run()

    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 