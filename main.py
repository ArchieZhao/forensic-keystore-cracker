#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JKS Keystore 密码破解工具集 - 主程序
支持两种破解模式：
1. 容器密码破解 (keystore2john + John the Ripper)
2. 私钥密码破解 (JksPrivkPrepare + Hashcat) - 推荐用于Android APK签名
支持进度保存和断点续传功能
"""

import os
import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text

# 导入我们的处理器模块
try:
    from certificate_batch_processor import CertificateBatchProcessor
    from jks_privkey_processor import JKSPrivateKeyProcessor
    from progress_manager import ProgressManager
    # 导入新的批量破解模块
    from batch_hash_extractor import BatchHashExtractor
    from batch_result_analyzer import BatchResultAnalyzer
    from ultimate_batch_cracker import UltimateBatchCracker
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保所有模块文件都在同一目录")
    sys.exit(1)

console = Console()

class JKSCrackingTool:
    def __init__(self):
        self.container_processor = None
        self.privkey_processor = None
        self.progress_manager = ProgressManager()
        # 添加批量破解组件
        self.batch_extractor = None
        self.batch_analyzer = None
        self.ultimate_cracker = None
        
    def show_banner(self):
        """显示程序横幅"""
        banner = Text.assemble(
            ("🚀 JKS Keystore 终极破解器\n", "bold cyan"),
            ("智能批量破解 + GPU加速 + 自动分析\n", "white"),
            ("专为Android APK签名证书优化\n", "yellow"),
            ("✨ 一键完整破解70个keystore + MD5/SHA1提取", "green")
        )
        console.print(Panel.fit(banner, border_style="cyan"))
    
    def show_crack_modes(self):
        """显示破解模式说明"""
        table = Table(title="💡 破解模式对比", border_style="blue")
        table.add_column("模式", style="cyan", width=15)
        table.add_column("目标", style="yellow", width=15)
        table.add_column("工具组合", style="green", width=25)
        table.add_column("性能", style="magenta", width=15)
        table.add_column("适用场景", style="white", width=25)
        
        table.add_row(
            "容器密码",
            "整个keystore",
            "keystore2john + JtR",
            "~500 H/s",
            "需要完整访问keystore"
        )
        table.add_row(
            "私钥密码",
            "单个私钥",
            "JksPrivkPrepare + Hashcat",
            "~10,000 H/s",
            "Android APK签名"
        )
        table.add_row(
            "🚀 终极批量",
            "70个keystore",
            "批量Hash + GPU破解",
            "RTX 3080优化",
            "大规模6位密码破解 (推荐)"
        )
        
        console.print(table)
    
    def show_session_management(self):
        """显示会话管理选项"""
        # 检查是否有未完成的会话
        sessions = self.progress_manager.list_sessions()
        incomplete_sessions = []
        
        for session_id in sessions:
            session = self.progress_manager.load_session(session_id)
            if session:
                total_processed = (session.completed_files + 
                                 session.failed_files + 
                                 session.skipped_files)
                if total_processed < session.total_files:
                    incomplete_sessions.append((session_id, session))
        
        if incomplete_sessions:
            console.print("\n[yellow]📋 发现未完成的会话:[/yellow]")
            
            table = Table(border_style="yellow")
            table.add_column("会话ID", style="cyan", width=12)
            table.add_column("目标路径", style="white", width=25)
            table.add_column("进度", style="green", width=10)
            table.add_column("最后更新", style="yellow", width=15)
            
            for session_id, session in incomplete_sessions[:3]:  # 只显示前3个
                total_processed = (session.completed_files + 
                                 session.failed_files + 
                                 session.skipped_files)
                progress_text = f"{total_processed}/{session.total_files}"
                
                try:
                    from datetime import datetime
                    last_update = datetime.fromisoformat(session.last_update)
                    time_text = last_update.strftime("%m-%d %H:%M")
                except:
                    time_text = "未知"
                
                table.add_row(session_id, session.target_path, progress_text, time_text)
            
            console.print(table)
            
            if len(incomplete_sessions) > 3:
                console.print(f"[dim]... 及其他 {len(incomplete_sessions)-3} 个会话[/dim]")
            
            console.print("\n[cyan]选项:[/cyan]")
            console.print("  [bold]r[/bold] - 恢复最近的未完成会话")
            console.print("  [bold]l[/bold] - 列出所有会话")
            console.print("  [bold]n[/bold] - 创建新会话")
            console.print("  [bold]c[/bold] - 清理已完成的旧会话")
            
            choice = Prompt.ask("请选择操作", choices=["r", "l", "n", "c"], default="r")
            
            if choice == "r":
                # 恢复最近的会话
                latest_session = incomplete_sessions[0]
                return "resume", latest_session[0]
            elif choice == "l":
                return "list", None
            elif choice == "c":
                return "cleanup", None
            else:
                return "new", None
        
        return "new", None
    
    def select_crack_mode(self):
        """选择破解模式"""
        self.show_crack_modes()
        
        console.print("\n[bold yellow]请选择破解模式:[/bold yellow]")
        console.print("[cyan]1.[/cyan] 容器密码破解 (keystore2john + John the Ripper)")
        console.print("[cyan]2.[/cyan] 私钥密码破解 (JksPrivkPrepare + Hashcat)")
        console.print("[cyan]3.[/cyan] 🚀 终极批量破解 (70个keystore批量处理) [推荐]")
        
        choice = Prompt.ask("选择破解模式", choices=["1", "2", "3"], default="3")
        
        if choice == "1":
            return "container"
        elif choice == "2":
            return "privkey"
        else:
            return "ultimate"
    
    def setup_processors(self, mode):
        """初始化处理器"""
        console.print(f"\n[cyan]🔧 初始化 {mode} 处理器...[/cyan]")
        
        try:
            if mode == "container":
                self.container_processor = CertificateBatchProcessor()
                console.print("[green]✅ 容器密码处理器初始化成功[/green]")
            elif mode == "privkey":
                # 检查JksPrivkPrepare.jar是否存在
                jar_path = "JKS-private-key-cracker-hashcat/JksPrivkPrepare.jar"
                if not os.path.exists(jar_path):
                    console.print(f"[red]❌ 未找到 JksPrivkPrepare.jar: {jar_path}[/red]")
                    console.print("[yellow]正在尝试下载工具...[/yellow]")
                    
                    try:
                        from download_jks_tool import download_jks_tool
                        if download_jks_tool():
                            console.print("[green]✅ JksPrivkPrepare.jar 下载成功[/green]")
                        else:
                            console.print("[red]❌ 工具下载失败，请手动下载[/red]")
                            return False
                    except ImportError:
                        console.print("[red]❌ 下载工具模块未找到[/red]")
                        return False
                
                self.privkey_processor = JKSPrivateKeyProcessor(jar_path)
                console.print("[green]✅ 私钥密码处理器初始化成功[/green]")
            elif mode == "ultimate":
                # 初始化终极批量破解器
                self.ultimate_cracker = UltimateBatchCracker()
                console.print("[green]✅ 终极批量破解器初始化成功[/green]")
                console.print("[yellow]🎯 专为70个keystore + RTX 3080优化[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ 处理器初始化失败: {e}[/red]")
            return False
    
    def scan_targets(self, target_path):
        """扫描目标文件或目录"""
        console.print(f"\n[cyan]📁 扫描目标: {target_path}[/cyan]")
        
        path = Path(target_path)
        
        if path.is_file():
            if path.suffix.lower() in ['.keystore', '.jks', '.p12', '.pfx']:
                console.print(f"[green]✅ 找到单个keystore文件: {path.name}[/green]")
                return "single", str(path)
            else:
                console.print(f"[red]❌ 不支持的文件类型: {path.suffix}[/red]")
                return None, None
                
        elif path.is_dir():
            # 扫描目录
            keystore_files = []
            for pattern in ['*.keystore', '*.jks', '*.p12', '*.pfx']:
                keystore_files.extend(path.rglob(pattern))
            
            if keystore_files:
                console.print(f"[green]✅ 找到 {len(keystore_files)} 个keystore文件[/green]")
                
                # 显示前几个文件
                for i, kf in enumerate(keystore_files[:5]):
                    console.print(f"   📄 {kf.relative_to(path)}")
                if len(keystore_files) > 5:
                    console.print(f"   ... 及其他 {len(keystore_files)-5} 个文件")
                
                return "batch", str(path)
            else:
                console.print("[yellow]⚠️ 目录中未找到keystore文件[/yellow]")
                return None, None
        else:
            console.print(f"[red]❌ 无效的路径: {target_path}[/red]")
            return None, None
    
    def get_password_mask(self):
        """获取密码掩码配置"""
        console.print("\n[bold yellow]配置密码掩码:[/bold yellow]")
        console.print("[cyan]常用掩码模式:[/cyan]")
        console.print("  ?a?a?a?a?a?a - 6位任意字符 (默认)")
        console.print("  ?u?l?l?l?d?d - 1大写+3小写+2数字")
        console.print("  ?l?l?l?l?l?l - 6位小写字母")
        console.print("  ?d?d?d?d?d?d - 6位数字")
        
        mask = Prompt.ask(
            "输入密码掩码", 
            default="?a?a?a?a?a?a",
            show_default=True
        )
        
        return mask
    
    def process_container_mode(self, target_type, target_path, mask):
        """处理容器密码模式"""
        console.print(Panel.fit(
            "[bold cyan]🔐 容器密码破解模式[/bold cyan]\n"
            "使用 keystore2john + John the Ripper",
            border_style="cyan"
        ))
        
        if target_type == "single":
            return self.container_processor.process_single_keystore(target_path, mask)
        else:
            return self.container_processor.process_directory(target_path, mask)
    
    def process_privkey_mode(self, target_type, target_path, mask):
        """处理私钥密码模式"""
        console.print(Panel.fit(
            "[bold cyan]🚀 私钥密码破解模式[/bold cyan]\n"
            "使用 JksPrivkPrepare + Hashcat (GPU加速)\n"
            "✨ 支持断点续传",
            border_style="cyan"
        ))
        
        if target_type == "single":
            return self.privkey_processor.process_single_keystore(target_path, mask)
        else:
            return self.privkey_processor.process_directory(target_path, mask)
    
    def process_ultimate_mode(self, target_type, target_path, mask):
        """处理终极批量破解模式"""
        console.print(Panel.fit(
            "[bold cyan]🚀 终极批量破解模式[/bold cyan]\n"
            "三步集成: Hash提取 → GPU破解 → 结果分析\n"
            "✨ 专为70个keystore + RTX 3080 + 6位密码优化\n"
            "📊 自动生成MD5/SHA1哈希值报告",
            border_style="cyan"
        ))
        
        # 终极模式只支持目录批量处理
        if target_type == "single":
            console.print("[yellow]⚠️ 终极模式专为批量处理设计，建议使用目录[/yellow]")
            console.print("[cyan]💡 将单文件移至certificate目录进行批量处理[/cyan]")
            return False
        
        # 执行一键完整破解
        return self.ultimate_cracker.run()
    
    def interactive_mode(self):
        """交互模式"""
        self.show_banner()
        
        # 会话管理
        session_action, session_id = self.show_session_management()
        
        if session_action == "resume":
            console.print(f"[green]🔄 恢复会话: {session_id}[/green]")
            # 初始化私钥处理器（断点续传只支持私钥模式）
            if not self.setup_processors("privkey"):
                return False
            return self.privkey_processor.resume_session(session_id) is not None
        
        elif session_action == "list":
            self.privkey_processor = JKSPrivateKeyProcessor()
            self.privkey_processor.list_sessions()
            return True
        
        elif session_action == "cleanup":
            self.progress_manager.cleanup_completed_sessions()
            console.print("[green]✅ 清理完成[/green]")
            return True
        
        # 创建新会话
        # 选择破解模式
        mode = self.select_crack_mode()
        
        # 初始化处理器
        if not self.setup_processors(mode):
            return False
        
        # 选择目标
        console.print("\n[bold yellow]选择目标:[/bold yellow]")
        target_path = Prompt.ask("输入keystore文件或目录路径", default="certificate")
        
        # 扫描目标
        target_type, validated_path = self.scan_targets(target_path)
        if not target_type:
            return False
        
        # 获取密码掩码
        mask = self.get_password_mask()
        
        # 确认开始
        if not Confirm.ask("\n是否开始破解?"):
            console.print("[yellow]用户取消操作[/yellow]")
            return False
        
        # 执行破解
        console.print("\n[bold green]🚀 开始破解...[/bold green]")
        
        if mode == "container":
            results = self.process_container_mode(target_type, validated_path, mask)
        elif mode == "privkey":
            results = self.process_privkey_mode(target_type, validated_path, mask)
        else:  # ultimate mode
            results = self.process_ultimate_mode(target_type, validated_path, mask)
        
        return results is not None
    
    def auto_mode(self, target_path="certificate", mask="?a?a?a?a?a?a", mode="ultimate"):
        """自动模式 - 默认使用终极批量破解"""
        console.print("[bold cyan]🚀 一键完整破解启动[/bold cyan]")
        console.print(f"[cyan]📋 配置: 模式={mode}, 目标={target_path}, 掩码={mask}[/cyan]")
        
        # 默认使用终极模式进行一键完整破解
        if mode == "ultimate":
            console.print("[yellow]🎯 启动终极批量破解 - 专为70个keystore优化[/yellow]")
            # 初始化终极破解器
            if not self.setup_processors("ultimate"):
                return False
            
            # 执行一键完整破解（不需要扫描，直接处理certificate目录）
            return self.ultimate_cracker.run()
        
        # 传统模式
        console.print(f"[cyan]📋 传统模式: {mode}[/cyan]")
        
        # 初始化处理器
        if not self.setup_processors(mode):
            return False
        
        # 扫描目标
        target_type, validated_path = self.scan_targets(target_path)
        if not target_type:
            return False
        
        # 执行破解
        if mode == "container":
            results = self.process_container_mode(target_type, validated_path, mask)
        else:
            results = self.process_privkey_mode(target_type, validated_path, mask)
        
        return results is not None


def main():
    parser = argparse.ArgumentParser(
        description="JKS Keystore 终极破解器 - 一键完整破解",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 一键完整破解示例:
  python main.py                                    # 默认一键破解 (certificate目录70个keystore)
  python main.py certificate                       # 终极批量破解模式
  
📋 传统模式示例:
  python main.py file.keystore                     # 指定文件
  python main.py /path/to/keystores                # 自定义路径
  python main.py certificate -m ?u?l?l?l?d?d       # 指定密码掩码
  
🛠️ 高级功能:
  python main.py --interactive                     # 交互模式（完整配置）
  python main.py --resume SESSION_ID               # 恢复指定会话
  python main.py --list-sessions                   # 列出所有会话
  python main.py --cleanup                         # 清理旧会话
  python main.py --export SESSION_ID               # 导出会话结果(JSON+Excel)
  python main.py --export SESSION_ID --json-only   # 仅导出JSON文件

💡 终极模式特点:
  - 自动批量提取70个keystore的hash
  - RTX 3080 GPU加速破解6位字母数字密码
  - 自动生成包含MD5/SHA1哈希值的详细报告
  - 预计66天完成完整破解（连续运行）
        """
    )
    
    parser.add_argument(
        "target", 
        nargs="?", 
        default="certificate",
        help="目标keystore文件或目录路径 (默认: certificate)"
    )
    
    parser.add_argument(
        "-m", "--mask", 
        default="?a?a?a?a?a?a",
        help="密码掩码 (默认: ?a?a?a?a?a?a)"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="交互模式 - 逐步选择配置"
    )
    
    parser.add_argument(
        "--resume",
        help="恢复指定会话ID"
    )
    
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="列出所有会话"
    )
    
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="清理已完成的旧会话"
    )
    
    parser.add_argument(
        "--export",
        help="导出指定会话的结果到Excel文件"
    )
    
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="仅导出JSON文件，不生成Excel文件"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细输出"
    )
    
    args = parser.parse_args()
    
    # 创建主工具实例
    tool = JKSCrackingTool()
    
    try:
        if args.list_sessions:
            # 列出所有会话
            processor = JKSPrivateKeyProcessor()
            processor.list_sessions()
            success = True
        elif args.cleanup:
            # 清理旧会话
            tool.progress_manager.cleanup_completed_sessions()
            console.print("[green]✅ 清理完成[/green]")
            success = True
        elif args.export:
            # 导出指定会话结果
            session = tool.progress_manager.load_session(args.export)
            if session:
                tool.progress_manager.current_session = session
                export_xlsx = not args.json_only
                output_file = tool.progress_manager.export_results(export_xlsx=export_xlsx)
                if output_file:
                    console.print(f"[green]✅ 会话 {args.export} 结果导出成功[/green]")
                else:
                    console.print(f"[red]❌ 会话 {args.export} 结果导出失败[/red]")
                success = bool(output_file)
            else:
                console.print(f"[red]❌ 会话不存在: {args.export}[/red]")
                success = False
        elif args.resume:
            # 恢复指定会话
            processor = JKSPrivateKeyProcessor()
            success = processor.resume_session(args.resume) is not None
        elif args.interactive:
            # 交互模式
            success = tool.interactive_mode()
        else:
            # 自动模式 - 默认一键完整破解
            console.print("[bold green]🚀 一键完整破解启动[/bold green]")
            if args.target == "certificate":
                console.print("[cyan]💡 使用默认路径: certificate (70个keystore)[/cyan]")
                console.print("[yellow]🎯 启动终极批量破解模式[/yellow]")
            else:
                console.print(f"[cyan]💡 使用指定路径: {args.target}[/cyan]")
            
            # 根据掩码决定模式
            if args.mask == "?a?a?a?a?a?a" and args.target == "certificate":
                # 默认配置，使用终极模式
                mode = "ultimate"
                console.print("[green]✅ 检测到6位字母数字密码 + certificate目录[/green]")
                console.print("[green]✅ 自动启用终极批量破解模式[/green]")
            else:
                # 自定义配置，使用传统私钥模式
                mode = "privkey"
                console.print("[yellow]⚠️ 检测到自定义配置，使用传统私钥模式[/yellow]")
            
            success = tool.auto_mode(
                target_path=args.target,
                mask=args.mask,
                mode=mode
            )
        
        if success:
            console.print("\n[bold green]🎉 任务完成![/bold green]")
        else:
            console.print("\n[bold red]❌ 任务失败![/bold red]")
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️ 用户中断操作[/yellow]")
        console.print("[cyan]💡 进度已自动保存，可使用 --resume 恢复[/cyan]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]💥 未处理的错误: {e}[/red]")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()