#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量JKS Keystore Hash提取器

从指定目录批量扫描JKS keystore文件，调用JksPrivkPrepare.jar提取私钥hash值，
生成Hashcat -m 15500兼容的$jksprivk$格式批量破解文件。

Architecture:
    扫描keystore → JksPrivkPrepare.jar → $jksprivk$格式hash → 批量文件 + 映射JSON

    JksHashExtractor (extractor_jks_hash.py:89)
        ├─ verify_environment() (L108): 检查Java/JAR/证书目录/GPU环境
        ├─ scan_keystores() (L157): 递归扫描certificate/[UUID]/apk.keystore
        ├─ extract_single_hash() (L176): 单文件hash提取，30秒超时
        ├─ batch_extract_hashes() (L237): 16线程并行提取，rich进度条
        ├─ create_batch_hash_file() (L278): 生成all_keystores.hash + uuid_hash_mapping.json
        └─ generate_crack_script() (L312): 生成run_batch_crack.py破解脚本

Features:
    - 16线程并行提取 (ThreadPoolExecutor)
    - rich库实时进度显示
    - 单文件30秒超时控制
    - 失败文件详细记录

Args (命令行):
    certificate_dir (str, optional): keystore文件根目录，默认'certificate'

        示例：
        python extractor_jks_hash.py                    # 使用默认certificate目录
        python extractor_jks_hash.py /path/to/keystores # 绝对路径
        python extractor_jks_hash.py ../my_certs        # 相对路径

Returns (输出文件):
    batch_crack_output/all_keystores.hash: 纯hash文件，每行一个$jksprivk$格式hash
    batch_crack_output/uuid_hash_mapping.json: UUID→hash→path映射关系
    batch_crack_output/run_batch_crack.py: Hashcat破解脚本 (RTX 3080优化参数)

Requirements:
    - Python 3.8+
    - Java Runtime Environment (JRE 8+)
    - JksPrivkPrepare.jar (JKS-private-key-cracker-hashcat/JksPrivkPrepare.jar)
    - rich (pip install rich)

Technical Notes:
    Hash格式兼容性:
        JksPrivkPrepare.jar生成$jksprivk$格式 → Hashcat -m 15500 (batch_hash_extractor.py:198-202)
        keystore2john.py生成$keystore$格式 → John the Ripper (不兼容Hashcat)

    UUID作为唯一标识:
        使用certificate/[UUID]/apk.keystore的UUID文件夹名作为ID (batch_hash_extractor.py:296-300)
        避免多个证书使用相同文件名导致冲突

    环境检查策略:
        GPU检查失败不阻塞执行 (batch_hash_extractor.py:153-155)
        hash提取仅需CPU，GPU用于后续Hashcat破解

Performance:
    - 并发: 16线程 (Intel i9-12900K优化)
    - 单文件: <30秒
    - 70文件批量: 2-5分钟

Author: Forensic Keystore Cracker Project
Version: 2.0.0
License: 仅用于授权的数字取证和安全研究
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table

console = Console()

class JksHashExtractor:
    def __init__(self, certificate_dir="certificate"):
        self.jar_path = "JKS-private-key-cracker-hashcat/JksPrivkPrepare.jar"
        self.certificate_dir = Path(certificate_dir)
        self.output_dir = Path("batch_crack_output")
        self.output_dir.mkdir(exist_ok=True)

        # 线程池大小（基于12900K的线程数）
        self.max_workers = 16

        # 统计信息
        self.stats = {
            'total_keystores': 0,
            'successful_extracts': 0,
            'failed_extracts': 0,
            'total_time': 0,
            'failed_files': []
        }
    
    def verify_environment(self):
        """验证运行环境"""
        console.print("[cyan]🔍 环境检查...[/cyan]")
        
        checks = [
            ("Java环境", self._check_java),
            ("JksPrivkPrepare.jar", self._check_jar),
            ("Certificate目录", self._check_certificate_dir),
            ("GPU状态", self._check_gpu)
        ]
        
        for name, check_func in checks:
            try:
                result = check_func()
                status = "✅" if result else "❌"
                console.print(f"  {status} {name}")
                if not result:
                    return False
            except Exception as e:
                console.print(f"  ❌ {name}: {e}")
                return False
        
        return True
    
    def _check_java(self):
        try:
            result = subprocess.run(['java', '-version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _check_jar(self):
        return Path(self.jar_path).exists()
    
    def _check_certificate_dir(self):
        return self.certificate_dir.exists()
    
    def _check_gpu(self):
        try:
            result = subprocess.run(['nvidia-smi'], capture_output=True, timeout=5)
            if result.returncode == 0:
                # 如果nvidia-smi成功运行，就认为GPU可用
                return True
            return False
        except:
            # GPU检查失败不影响hash提取（hash提取不需要GPU）
            console.print("[yellow]  ⚠️ 无法检测GPU，但hash提取不需要GPU，将继续运行[/yellow]")
            return True
    
    def scan_keystores(self):
        """扫描所有keystore文件"""
        console.print("[cyan]📁 扫描keystore文件...[/cyan]")
        
        keystores = []
        for uuid_dir in self.certificate_dir.iterdir():
            if uuid_dir.is_dir():
                keystore_file = uuid_dir / "apk.keystore"
                if keystore_file.exists():
                    keystores.append({
                        'uuid': uuid_dir.name,
                        'path': keystore_file,
                        'size': keystore_file.stat().st_size
                    })
        
        self.stats['total_keystores'] = len(keystores)
        console.print(f"[green]✅ 发现 {len(keystores)} 个keystore文件[/green]")
        return keystores
    
    def extract_single_hash(self, keystore_info):
        """提取单个keystore的hash"""
        uuid = keystore_info['uuid']
        keystore_path = keystore_info['path']
        
        try:
            # 执行JksPrivkPrepare.jar
            cmd = [
                "java", "-jar", self.jar_path,
                str(keystore_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # 查找$jksprivk$格式的hash
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.startswith('$jksprivk$'):
                        # 🔧 修复：保留完整的$jksprivk$格式，包括别名部分
                        # JksPrivkPrepare.jar生成的格式是正确的，不需要清理
                        clean_hash = line.strip()
                        
                        return {
                            'success': True,
                            'hash': clean_hash,
                            'uuid': uuid,
                            'alias': 'extracted',
                            'message': f'Hash extracted successfully for {uuid}'
                        }
                
                return {
                    'uuid': uuid,
                    'success': False,
                    'error': '未找到有效hash'
                }
            else:
                return {
                    'uuid': uuid,
                    'success': False,
                    'error': f'JksPrivkPrepare执行失败: {result.stderr}'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'uuid': uuid,
                'success': False,
                'error': '提取超时'
            }
        except Exception as e:
            return {
                'uuid': uuid,
                'success': False,
                'error': str(e)
            }
    
    def batch_extract_hashes(self, keystores):
        """批量并行提取hash"""
        console.print(f"[cyan]⚡ 启动并行提取 (最大 {self.max_workers} 线程)...[/cyan]")
        
        successful_hashes = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("提取hash...", total=len(keystores))
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_keystore = {
                    executor.submit(self.extract_single_hash, ks): ks 
                    for ks in keystores
                }
                
                # 收集结果
                for future in as_completed(future_to_keystore):
                    result = future.result()
                    
                    if result['success']:
                        successful_hashes.append(result)
                        self.stats['successful_extracts'] += 1
                    else:
                        self.stats['failed_extracts'] += 1
                        self.stats['failed_files'].append({
                            'uuid': result['uuid'],
                            'error': result['error']
                        })
                    
                    progress.advance(task, 1)
        
        return successful_hashes
    
    def create_batch_hash_file(self, hash_results):
        """创建批量hash文件供hashcat使用"""
        batch_file = self.output_dir / "all_keystores.hash"
        mapping_file = self.output_dir / "uuid_hash_mapping.json"
        
        console.print(f"[cyan]📝 创建批量hash文件: {batch_file}[/cyan]")
        
        # 创建UUID到hash的映射数据
        mapping_data = {}
        hash_index = 0
        
        # 生成纯净的hash文件（hashcat要求）
        with open(batch_file, 'w', encoding='utf-8') as f:
            for result in hash_results:
                # hashcat需要纯净的$jksprivk$格式，不能有前缀
                f.write(f"{result['hash']}\n")
                
                # 建立映射关系：hash行号 → UUID信息
                mapping_data[hash_index] = {
                    'uuid': result['uuid'],
                    'hash': result['hash'],
                    'keystore_path': f"certificate/{result['uuid']}/apk.keystore"
                }
                hash_index += 1
        
        # 保存映射文件用于结果分析
        import json
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mapping_data, f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]✅ 批量hash文件创建完成 ({len(hash_results)} 个hash)[/green]")
        console.print(f"[green]✅ UUID映射文件已生成: {mapping_file}[/green]")
        return batch_file
    
    def generate_crack_script(self, hash_file):
        """生成优化的破解脚本"""
        script_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成的GPU批量破解脚本
针对RTX 3080 + 6位字母数字密码优化
"""

import subprocess
import time
from pathlib import Path

def run_optimized_crack():
    """运行优化的6位密码破解"""
    print("🚀 启动RTX 3080优化破解...")
    print("🎯 目标: 6位大小写字母+数字 (62^6 = 56,800,235,584 组合)")
    print("⏰ 预计耗时: 约66天 (连续运行)")
    
    hash_file = r"{hash_file}"
    hashcat_path = r"hashcat-6.2.6\\hashcat.exe"
    
    # RTX 3080专用优化参数
    cmd = [
        hashcat_path,
        "-m", "15500",                    # JKS私钥模式
        "-a", "3",                        # 掩码攻击
        hash_file,                        # hash文件
        "-1", "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",  # 自定义字符集
        "?1?1?1?1?1?1",                   # 6位掩码
        "--force",                        # 强制运行
        "-O",                            # 优化内核
        "-w", "4",                       # 最高工作负载
        "--markov-disable",              # 禁用马尔可夫链
        "--segment-size", "32",          # 优化内存段
        "--status",                      # 显示状态
        "--status-timer", "60",          # 每分钟更新状态
        "--session", "batch_6digit_crack", # 会话名
        "--potfile-path", "batch_results.potfile"  # 结果文件
    ]
    
    print("执行命令:")
    print(" ".join(cmd))
    print("\\n" + "="*60)
    
    try:
        # 在hashcat目录执行
        process = subprocess.Popen(
            cmd,
            cwd="hashcat-6.2.6",
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
        print(f"\\n破解完成，返回码: {{return_code}}")
        
        if return_code == 0:
            print("🎉 密码破解成功！检查 batch_results.potfile 查看结果")
        elif return_code == 1:
            print("⚠️ 破解完成但未找到密码")
        else:
            print("❌ 破解过程出现错误")
            
    except KeyboardInterrupt:
        print("\\n⏹️ 用户中断破解")
        print("💡 可以使用 --restore 恢复会话")
    except Exception as e:
        print(f"❌ 破解执行失败: {{e}}")

if __name__ == "__main__":
    run_optimized_crack()
'''
        
        script_file = self.output_dir / "run_batch_crack.py"
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        console.print(f"[green]✅ 破解脚本已生成: {script_file}[/green]")
        return script_file
    
    def show_stats(self):
        """显示统计信息"""
        table = Table(title="📊 批量Hash提取统计", border_style="green")
        table.add_column("项目", style="cyan")
        table.add_column("数值", style="white")
        
        table.add_row("总keystore数", str(self.stats['total_keystores']))
        table.add_row("成功提取", str(self.stats['successful_extracts']))
        table.add_row("提取失败", str(self.stats['failed_extracts']))
        table.add_row("成功率", f"{(self.stats['successful_extracts']/max(self.stats['total_keystores'],1)*100):.1f}%")
        table.add_row("处理时间", f"{self.stats['total_time']:.2f}秒")
        
        console.print(table)
        
        # 显示失败的文件
        if self.stats['failed_files']:
            console.print("\\n[red]❌ 提取失败的文件:[/red]")
            for failed in self.stats['failed_files'][:5]:
                console.print(f"  {failed['uuid']}: {failed['error']}")
            if len(self.stats['failed_files']) > 5:
                console.print(f"  ... 及其他 {len(self.stats['failed_files'])-5} 个文件")
    
    def run(self):
        """执行批量提取"""
        console.print(Panel.fit(
            "[bold cyan]🚀 批量JKS Hash提取器[/bold cyan]\\n"
            "RTX 3080 + 6位密码专用优化\\n"
            "目标: 70个keystore批量处理",
            border_style="cyan"
        ))
        
        start_time = time.time()
        
        # 1. 环境检查
        if not self.verify_environment():
            console.print("[red]❌ 环境检查失败[/red]")
            return False
        
        # 2. 扫描keystore文件
        keystores = self.scan_keystores()
        if not keystores:
            console.print("[red]❌ 未找到keystore文件[/red]")
            return False
        
        # 3. 批量提取hash
        hash_results = self.batch_extract_hashes(keystores)
        
        # 4. 创建批量hash文件
        if hash_results:
            batch_file = self.create_batch_hash_file(hash_results)
            
            # 5. 生成破解脚本
            crack_script = self.generate_crack_script(batch_file)
            
            # 6. 统计和指导
            self.stats['total_time'] = time.time() - start_time
            self.show_stats()
            
            # 显示后续操作指南
            console.print("\\n" + "="*60)
            console.print("[bold green]🎯 下一步操作:[/bold green]")
            console.print(f"[cyan]1. 执行批量破解:[/cyan]")
            console.print(f"   python {crack_script}")
            console.print(f"[cyan]2. 监控破解进度:[/cyan]")
            console.print(f"   nvidia-smi")
            console.print(f"[cyan]3. 查看破解结果:[/cyan]")
            console.print(f"   type {self.output_dir}\\\\batch_results.potfile")
            
            console.print(f"\\n[yellow]⚠️ 重要提示:[/yellow]")
            console.print(f"[yellow]- 6位密码完整破解预计需要约66天[/yellow]")
            console.print(f"[yellow]- 建议24/7连续运行以获得最佳效果[/yellow]")
            console.print(f"[yellow]- 可随时Ctrl+C中断，稍后用--restore恢复[/yellow]")
            
            return True
        else:
            console.print("[red]❌ 未能提取任何有效hash[/red]")
            return False

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="JKS Hash提取器 - 从多个keystore文件批量提取hash",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python extractor_jks_hash.py                    # 使用默认的certificate目录
  python extractor_jks_hash.py my_certificates    # 使用自定义目录
  python extractor_jks_hash.py ../certs           # 使用相对路径
        """
    )

    parser.add_argument(
        'certificate_dir',
        nargs='?',
        default='certificate',
        help='包含keystore文件的目录路径 (默认: certificate)'
    )

    args = parser.parse_args()

    extractor = JksHashExtractor(certificate_dir=args.certificate_dir)
    success = extractor.run()
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 