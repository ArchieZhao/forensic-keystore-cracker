#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JKS私钥密码破解处理器 - 支持进度保存和断点续传
使用JksPrivkPrepare.jar + Hashcat进行GPU加速破解
"""

import os
import sys
import time
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# 导入进度管理器和keystore信息提取器
try:
    from progress_manager import ProgressManager, TaskProgress
    from keystore_info_extractor import KeystoreInfoExtractor
except ImportError:
    print("错误: 无法导入必要模块")
    sys.exit(1)

console = Console()

class JKSPrivateKeyProcessor:
    def __init__(self, jar_path: str = "JKS-private-key-cracker-hashcat/JksPrivkPrepare.jar"):
        self.jar_path = jar_path
        self.hashcat_path = "hashcat-6.2.6/hashcat.exe"
        self.progress_manager = ProgressManager()
        self.keystore_extractor = KeystoreInfoExtractor()
        self.verify_tools()
    
    def verify_tools(self):
        """验证所需工具"""
        missing_tools = []
        
        if not os.path.exists(self.jar_path):
            missing_tools.append(f"JksPrivkPrepare.jar: {self.jar_path}")
        
        if not os.path.exists(self.hashcat_path):
            missing_tools.append(f"hashcat.exe: {self.hashcat_path}")
        
        # 检查Java环境
        try:
            result = subprocess.run(['java', '-version'], 
                                  capture_output=True, text=True, timeout=10)
        except:
            missing_tools.append("Java (JDK/JRE)")
        
        if missing_tools:
            console.print("[red]❌ 缺少必要工具:[/red]")
            for tool in missing_tools:
                console.print(f"   - {tool}")
            raise RuntimeError("工具验证失败")
        
        console.print("[green]✅ 所有工具验证通过[/green]")
    
    def extract_private_key_hash(self, keystore_path: str) -> Optional[str]:
        """提取JKS私钥hash - 修复临时文件冲突"""
        if not os.path.exists(keystore_path):
            console.print(f"[red]❌ Keystore文件不存在: {keystore_path}[/red]")
            return None
        
        # 使用更安全的临时文件处理
        temp_dir = Path(tempfile.gettempdir()) / "jks_crack"
        temp_dir.mkdir(exist_ok=True)
        
        # 使用时间戳和进程ID避免冲突
        timestamp = int(time.time() * 1000)
        pid = os.getpid()
        hash_file = temp_dir / f"hash_{timestamp}_{pid}.txt"
        
        try:
            # 执行JksPrivkPrepare.jar
            cmd = [
                "java", "-jar", self.jar_path,
                keystore_path
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30,
                cwd=os.getcwd()
            )
            
            if result.returncode != 0:
                console.print(f"[red]❌ JksPrivkPrepare.jar执行失败[/red]")
                console.print(f"[red]错误: {result.stderr}[/red]")
                return None
            
            # 解析输出获取hash
            lines = result.stdout.strip().split('\n')
            hash_line = None
            
            for line in lines:
                if line.startswith('$jksprivk$'):
                    hash_line = line.strip()
                    break
            
            if not hash_line:
                console.print(f"[red]❌ 未找到有效的hash值[/red]")
                console.print(f"[yellow]输出: {result.stdout}[/yellow]")
                return None
            
            # 写入hash文件
            try:
                with open(hash_file, 'w', encoding='utf-8') as f:
                    f.write(hash_line + '\n')
                    f.flush()  # 确保写入
                
                # 验证文件是否成功创建
                if hash_file.exists() and hash_file.stat().st_size > 0:
                    console.print(f"[green]✅ Hash文件已创建: {hash_file}[/green]")
                    return str(hash_file)
                else:
                    console.print(f"[red]❌ Hash文件创建失败[/red]")
                    return None
                    
            except Exception as e:
                console.print(f"[red]❌ 写入hash文件失败: {e}[/red]")
                return None
                
        except subprocess.TimeoutExpired:
            console.print(f"[red]❌ JksPrivkPrepare.jar执行超时[/red]")
            return None
        except Exception as e:
            console.print(f"[red]❌ 提取hash失败: {e}[/red]")
            return None
    
    def check_cracked_password(self, hash_file: str) -> Optional[str]:
        """检查已破解的密码"""
        try:
            hashcat_dir = Path(self.hashcat_path).parent
            cmd = [
                str(self.hashcat_path),
                "-m", "15500",
                str(hash_file),
                "--show"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=str(hashcat_dir),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if ':' in line and '$jksprivk$' in line:
                        password = line.split(':')[-1].strip()
                        if password:
                            console.print(f"[green]✅ 从--show命令获取密码: {password}[/green]")
                            return password
            
            return None
            
        except Exception as e:
            console.print(f"[yellow]⚠️ 检查已破解密码失败: {e}[/yellow]")
            return None
    
    def crack_with_hashcat(self, hash_file: str, mask: str = "?a?a?a?a?a?a", extra_args: List[str] = []) -> Optional[Tuple[str, float]]:
        """使用hashcat破解JKS私钥密码 - 修复版本"""
        start_time = time.time()
        
        # 获取绝对路径
        hashcat_dir = Path(self.hashcat_path).parent
        hash_file_path = Path(hash_file)
        
        # 复制hash文件到hashcat目录以避免路径问题
        target_hash_file = hashcat_dir / "temp_hash.txt"
        try:
            shutil.copy2(hash_file_path, target_hash_file)
        except Exception as e:
            console.print(f"[red]❌ 复制hash文件失败: {e}[/red]")
            return None
        
        try:
            # 在hashcat目录中执行命令，使用相对路径
            cmd = [
                str(self.hashcat_path),
                "-m", "15500",  # JKS私钥模式
                "temp_hash.txt",  # 使用临时文件
                "-a", "3",       # 掩码攻击
                mask,
                "--force",       # 忽略警告
                "-O",           # 优化内核
                "--quiet",       # 减少输出
                "--potfile-disable"  # 禁用pot文件避免缓存干扰
            ]
            
            cmd.extend(extra_args)
            
            console.print(f"[dim]执行目录: {hashcat_dir}[/dim]")
            console.print(f"[dim]命令: {' '.join(cmd)}[/dim]")
            
            # 在hashcat目录中执行
            result = subprocess.run(
                cmd,
                cwd=str(hashcat_dir),  # 关键修复：在hashcat目录执行
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            
            duration = time.time() - start_time
            
            # 正确处理返回码
            if result.returncode == 0:
                # 返回码0: 找到密码
                console.print(f"[green]✅ Hashcat返回码0: 找到密码[/green]")
                
                # 从输出中提取密码
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if ':' in line and '$jksprivk$' in line:
                        password = line.split(':')[-1].strip()
                        if password:
                            console.print(f"[green]🎉 密码破解成功: {password}[/green]")
                            return password, duration
                
                # 如果输出中没有密码，尝试--show命令
                console.print("[yellow]从输出中未找到密码，尝试--show命令[/yellow]")
                show_result = self.check_cracked_password(target_hash_file)
                if show_result:
                    return show_result, duration
                    
            elif result.returncode == 1:
                # 返回码1: 正常完成但未找到密码（非错误）
                console.print(f"[yellow]⚠️ Hashcat返回码1: 未找到密码（正常完成）[/yellow]")
                return None
                
            else:
                # 其他返回码: 真正的错误
                console.print(f"[red]❌ Hashcat执行异常，返回码: {result.returncode}[/red]")
                console.print(f"[red]错误输出: {result.stderr}[/red]")
                return None
            
            return None
            
        except subprocess.TimeoutExpired:
            console.print(f"[red]❌ Hashcat执行超时（>10分钟）[/red]")
            return None
        except Exception as e:
            console.print(f"[red]❌ Hashcat执行异常: {e}[/red]")
            return None
        finally:
            # 清理临时文件
            try:
                if target_hash_file.exists():
                    target_hash_file.unlink()
            except:
                pass
    
    def process_single_keystore(self, keystore_path: str, mask: str = "?a?a?a?a?a?a") -> Optional[Dict[str, Any]]:
        """处理单个keystore文件"""
        console.print(Panel.fit(
            f"[bold cyan]🚀 JKS私钥密码破解[/bold cyan]\n"
            f"文件: {keystore_path}\n"
            f"掩码: {mask}\n"
            f"优化: 启用",
            border_style="cyan"
        ))
        
        start_time = time.time()
        
        # 提取私钥hash
        console.print(f"🔑 提取私钥hash: {keystore_path}")
        hash_file = self.extract_private_key_hash(keystore_path)
        
        if not hash_file:
            console.print("[red]❌ 无法提取私钥hash[/red]")
            return {
                "file": keystore_path,
                "error": "无法提取私钥hash",
                "duration": time.time() - start_time,
                "success": False
            }
        
        console.print("[green]✅ 成功提取hash[/green]")
        
        # 破解密码 - 专门针对6位大小写字母+数字密码
        console.print(f"🔨 开始破解6位字母数字密码...")
        
        # 只使用一种策略：6位混合字母数字
        strategy_mask = "?1?1?1?1?1?1"
        description = "6位混合字母数字 (a-z,A-Z,0-9)"
        
        # 定义字符集
        charset_cmd = ["--custom-charset1", "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"]
        
        console.print(f"🎯 使用策略: {description}")
        console.print(f"🔨 执行命令: hashcat -m 15500 hash.txt -a 3 {strategy_mask} --force -O --custom-charset1 a-zA-Z0-9")
        
        result = self.crack_with_hashcat(hash_file, strategy_mask, charset_cmd)
        
        if result:
            password, duration = result
            total_time = time.time() - start_time
            
            # 提取keystore详细信息
            console.print(f"📋 提取keystore信息...")
            alias, public_key_md5, public_key_sha1, keystore_type = self.keystore_extractor.extract_simple_info(
                keystore_path, password
            )
            
            # 显示结果
            result_table = Table(title="🎉 破解成功!")
            result_table.add_column("项目", style="cyan")
            result_table.add_column("值", style="white")
            
            result_table.add_row("文件", Path(keystore_path).name)
            result_table.add_row("密码", f"[bold green]{password}[/bold green]")
            result_table.add_row("别名", alias)
            result_table.add_row("公钥MD5", public_key_md5)
            result_table.add_row("公钥SHA1", public_key_sha1)
            result_table.add_row("类型", keystore_type)
            result_table.add_row("破解时间", f"{duration:.2f}秒")
            result_table.add_row("总耗时", f"{total_time:.2f}秒")
            
            console.print(result_table)
            
            return {
                "file": keystore_path,
                "password": password,
                "duration": total_time,
                "alias": alias,
                "public_key_md5": public_key_md5,
                "public_key_sha1": public_key_sha1,
                "keystore_type": keystore_type,
                "success": True
            }
        else:
            total_time = time.time() - start_time
            console.print("[red]❌ 所有策略都失败了[/red]")
            console.print(f"[cyan]💡 建议: 检查密码长度是否确实为6位，或尝试更复杂的掩码[/cyan]")
            return {
                "file": keystore_path,
                "error": "所有破解策略都失败",
                "duration": total_time,
                "success": False
            }
    
    def scan_keystore_files(self, target_path: str) -> List[str]:
        """扫描keystore文件"""
        path = Path(target_path)
        keystore_files = []
        
        if path.is_file():
            if path.suffix.lower() in ['.keystore', '.jks', '.p12', '.pfx']:
                keystore_files.append(str(path))
        elif path.is_dir():
            for pattern in ['*.keystore', '*.jks', '*.p12', '*.pfx']:
                keystore_files.extend([str(f) for f in path.rglob(pattern)])
        
        return sorted(keystore_files)
    
    def process_directory(self, target_path: str, mask: str = "?a?a?a?a?a?a") -> Optional[Dict[str, Any]]:
        """批量处理目录中的keystore文件（支持断点续传）"""
        console.print(f"📁 扫描目录: {target_path}")
        
        # 扫描文件
        keystore_files = self.scan_keystore_files(target_path)
        
        if not keystore_files:
            console.print("[yellow]⚠️ 未找到keystore文件[/yellow]")
            return None
        
        console.print(f"✅ 找到 {len(keystore_files)} 个keystore文件")
        
        # 创建或恢复会话
        session_id = self.progress_manager.create_session(
            target_path=target_path,
            mask=mask,
            mode="privkey",
            file_list=keystore_files
        )
        
        # 获取待处理的任务
        pending_tasks = self.progress_manager.get_pending_tasks()
        
        if not pending_tasks:
            console.print("[green]✅ 所有任务已完成[/green]")
            self.progress_manager.show_progress()
            return self.progress_manager.get_results_summary()
        
        console.print(f"📋 待处理任务: {len(pending_tasks)} 个")
        
        # 处理每个文件
        total_files = len(keystore_files)
        processed_count = total_files - len(pending_tasks)
        
        for task in pending_tasks:
            processed_count += 1
            
            console.print(f"\n处理 {processed_count}/{total_files}")
            
            # 开始任务
            self.progress_manager.start_task(task.file_path)
            
            # 处理文件
            result = self.process_single_keystore(task.file_path, mask)
            
            if result and result.get("success"):
                # 任务成功
                self.progress_manager.complete_task(
                    task.file_path,
                    result["password"],
                    result["duration"],
                    alias=result.get("alias"),
                    public_key_md5=result.get("public_key_md5"),
                    public_key_sha1=result.get("public_key_sha1"),
                    keystore_type=result.get("keystore_type")
                )
            else:
                # 任务失败
                error_msg = result.get("error", "未知错误") if result else "处理失败"
                self.progress_manager.fail_task(task.file_path, error_msg)
            
            # 显示当前进度
            if processed_count % 5 == 0 or processed_count == total_files:
                self.progress_manager.show_progress()
        
        # 最终保存会话
        self.progress_manager.save_session()
        
        # 显示汇总结果
        summary = self.progress_manager.get_results_summary()
        self.display_batch_results(summary)
        
        # 导出结果
        self.progress_manager.export_results()
        
        return summary
    
    def display_batch_results(self, summary: Dict[str, Any]):
        """显示批量破解结果"""
        if not summary or not summary.get("results"):
            return
        
        # 创建结果表格
        table = Table(title="📊 批量破解结果汇总", border_style="green")
        table.add_column("文件", style="yellow")
        table.add_column("状态", style="green")
        table.add_column("密码", style="cyan")
        
        # 添加成功结果
        for result in summary["results"]:
            table.add_row(
                result["file"],
                "✅ 成功",
                result["password"]
            )
        
        console.print(table)
        console.print(f"\n成功破解: {summary['successful']}/{summary['total_files']}")
        
        if summary.get("failed", 0) > 0:
            console.print(f"失败: {summary['failed']}")
        if summary.get("skipped", 0) > 0:
            console.print(f"跳过: {summary['skipped']}")
    
    def resume_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """恢复指定会话"""
        session = self.progress_manager.load_session(session_id)
        if not session:
            console.print(f"[red]❌ 会话不存在: {session_id}[/red]")
            return None
        
        console.print(f"[green]🔄 恢复会话: {session_id}[/green]")
        self.progress_manager.current_session = session
        
        return self.process_directory(session.target_path, session.mask)
    
    def list_sessions(self):
        """列出所有会话"""
        sessions = self.progress_manager.list_sessions()
        
        if not sessions:
            console.print("[yellow]📝 没有保存的会话[/yellow]")
            return
        
        table = Table(title="📋 已保存的会话", border_style="blue")
        table.add_column("会话ID", style="cyan")
        table.add_column("目标路径", style="yellow")
        table.add_column("进度", style="green")
        table.add_column("最后更新", style="white")
        
        for session_id in sessions:
            session = self.progress_manager.load_session(session_id)
            if session:
                total_processed = (session.completed_files + 
                                 session.failed_files + 
                                 session.skipped_files)
                progress_text = f"{total_processed}/{session.total_files}"
                
                # 格式化时间
                try:
                    from datetime import datetime
                    last_update = datetime.fromisoformat(session.last_update)
                    time_text = last_update.strftime("%m-%d %H:%M")
                except:
                    time_text = "未知"
                
                table.add_row(
                    session_id,
                    session.target_path,
                    progress_text,
                    time_text
                )
        
        console.print(table)
    
    def cleanup_sessions(self, keep_days: int = 7):
        """清理旧会话"""
        self.progress_manager.cleanup_completed_sessions(keep_days)


# 命令行接口
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="JKS私钥密码破解工具")
    parser.add_argument("target", help="目标keystore文件或目录")
    parser.add_argument("-m", "--mask", default="?a?a?a?a?a?a", help="密码掩码")
    parser.add_argument("--jar", help="JksPrivkPrepare.jar路径")
    parser.add_argument("--resume", help="恢复指定会话ID")
    parser.add_argument("--list-sessions", action="store_true", help="列出所有会话")
    parser.add_argument("--cleanup", action="store_true", help="清理旧会话")
    
    args = parser.parse_args()
    
    try:
        if args.jar:
            processor = JKSPrivateKeyProcessor(args.jar)
        else:
            processor = JKSPrivateKeyProcessor()
        
        if args.list_sessions:
            processor.list_sessions()
        elif args.cleanup:
            processor.cleanup_sessions()
        elif args.resume:
            processor.resume_session(args.resume)
        else:
            # 检查目标类型
            target_path = Path(args.target)
            if target_path.is_file():
                processor.process_single_keystore(str(target_path), args.mask)
            elif target_path.is_dir():
                processor.process_directory(str(target_path), args.mask)
            else:
                console.print(f"[red]❌ 无效目标: {args.target}[/red]")
                return 1
        
        return 0
        
    except Exception as e:
        console.print(f"[red]💥 错误: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 