#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终极批量JKS破解器 - 一键完成所有步骤
专为Windows 11 + RTX 3080 + 70个keystore优化
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
    def __init__(self):
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
            "[green]目标: 70个keystore × 6位字母数字密码[/green]\n"
            "[red]预计: 62^6 = 56,800,235,584 种组合 ≈ 66天[/red]",
            border_style="cyan"
        ))
    
    def check_prerequisites(self):
        """检查前置条件"""
        console.print("[cyan]🔍 系统环境检查...[/cyan]")
        
        checks = [
            ("Certificate目录", Path("certificate").exists()),
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
            extractor = BatchHashExtractor()
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
    console.print("=" * 80)
    console.print("[bold cyan]终极批量JKS破解器 v1.0[/bold cyan]")
    console.print("[yellow]专为Windows 11 + RTX 3080 + 70个keystore优化[/yellow]")
    console.print("=" * 80)
    
    cracker = UltimateBatchCracker()
    success = cracker.run()
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 