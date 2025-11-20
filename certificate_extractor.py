#!/usr/bin/env python3
"""
JKS证书提取和MD5计算工具
用于从已知密码的JKS keystore中提取公钥证书并计算MD5签名
"""

import os
import sys
import subprocess
import hashlib
import tempfile
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import argparse

console = Console()

class CertificateExtractor:
    def __init__(self):
        self.java_path = "java"
        self.keytool_path = "keytool"  # 通常随JDK安装
        
    def validate_keystore(self, keystore_path, password):
        """验证keystore路径和密码是否正确"""
        if not os.path.exists(keystore_path):
            console.print(f"[red]❌ Keystore文件不存在: {keystore_path}[/red]")
            return False
            
        try:
            # 使用keytool验证密码
            cmd = [
                self.keytool_path, "-list", 
                "-keystore", keystore_path,
                "-storepass", password,
                "-v"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                console.print("[green]✅ Keystore验证成功[/green]")
                return True
            else:
                console.print(f"[red]❌ Keystore验证失败: {result.stderr}[/red]")
                return False
                
        except subprocess.TimeoutExpired:
            console.print("[red]❌ Keystore验证超时[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ 验证过程出错: {e}[/red]")
            return False
    
    def list_aliases(self, keystore_path, password):
        """列出keystore中的所有别名"""
        console.print("[cyan]🔍 扫描keystore中的证书别名...[/cyan]")
        
        try:
            cmd = [
                self.keytool_path, "-list",
                "-keystore", keystore_path,
                "-storepass", password
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]❌ 无法列出别名: {result.stderr}[/red]")
                return []
            
            # 解析别名
            aliases = []
            lines = result.stdout.split('\n')
            
            for line in lines:
                line = line.strip()
                if ', ' in line and ('PrivateKeyEntry' in line or 'trustedCertEntry' in line):
                    # 提取别名 (在第一个逗号之前)
                    alias = line.split(',')[0].strip()
                    entry_type = 'Private Key' if 'PrivateKeyEntry' in line else 'Certificate'
                    aliases.append((alias, entry_type))
            
            if aliases:
                console.print(f"[green]✅ 找到 {len(aliases)} 个证书条目[/green]")
                
                # 显示别名表格
                table = Table(title="📋 证书别名列表", border_style="blue")
                table.add_column("别名", style="cyan")
                table.add_column("类型", style="yellow")
                
                for alias, entry_type in aliases:
                    table.add_row(alias, entry_type)
                
                console.print(table)
            else:
                console.print("[yellow]⚠️ 未找到任何证书条目[/yellow]")
            
            return aliases
            
        except Exception as e:
            console.print(f"[red]❌ 列出别名时发生错误: {e}[/red]")
            return []
    
    def export_certificate(self, keystore_path, password, alias, output_file=None):
        """从keystore中导出指定别名的证书"""
        if output_file is None:
            output_file = f"{alias}_certificate.crt"
        
        console.print(f"[cyan]📤 导出证书: {alias} → {output_file}[/cyan]")
        
        try:
            cmd = [
                self.keytool_path, "-exportcert",
                "-keystore", keystore_path,
                "-storepass", password,
                "-alias", alias,
                "-file", output_file,
                "-rfc"  # 输出为PEM格式
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    console.print(f"[green]✅ 证书导出成功: {output_file} ({file_size} bytes)[/green]")
                    return output_file
                else:
                    console.print("[red]❌ 证书文件未生成[/red]")
                    return None
            else:
                console.print(f"[red]❌ 证书导出失败: {result.stderr}[/red]")
                return None
                
        except Exception as e:
            console.print(f"[red]❌ 导出证书时发生错误: {e}[/red]")
            return None
    
    def calculate_certificate_md5(self, cert_file):
        """计算证书文件的MD5值"""
        console.print(f"[cyan]🔐 计算证书MD5: {cert_file}[/cyan]")
        
        try:
            # 方法1: 直接计算证书文件的MD5
            with open(cert_file, 'rb') as f:
                file_content = f.read()
                file_md5 = hashlib.md5(file_content).hexdigest()
            
            # 方法2: 使用keytool计算证书的指纹
            cmd = [
                self.keytool_path, "-printcert",
                "-file", cert_file,
                "-v"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            cert_md5 = None
            cert_sha1 = None
            cert_sha256 = None
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    line = line.strip()
                    if 'MD5:' in line:
                        cert_md5 = line.split('MD5:')[1].strip().replace(':', '').lower()
                    elif 'SHA1:' in line:
                        cert_sha1 = line.split('SHA1:')[1].strip().replace(':', '').lower()
                    elif 'SHA256:' in line:
                        cert_sha256 = line.split('SHA256:')[1].strip().replace(':', '').lower()
            
            # 显示结果
            table = Table(title="🔐 证书MD5签名信息", border_style="green")
            table.add_column("类型", style="cyan", width=15)
            table.add_column("值", style="green", width=50)
            table.add_column("说明", style="yellow")
            
            table.add_row("文件MD5", file_md5, "证书文件的MD5值")
            
            if cert_md5:
                table.add_row("证书MD5", cert_md5, "Android APK签名MD5 ⭐")
            if cert_sha1:
                table.add_row("证书SHA1", cert_sha1, "证书SHA1指纹")
            if cert_sha256:
                table.add_row("证书SHA256", cert_sha256, "证书SHA256指纹")
            
            console.print(table)
            
            # 返回Android APK签名最常用的MD5值
            return cert_md5 if cert_md5 else file_md5
            
        except Exception as e:
            console.print(f"[red]❌ 计算MD5时发生错误: {e}[/red]")
            return None
    
    def get_certificate_details(self, cert_file):
        """获取证书的详细信息"""
        console.print(f"[cyan]📋 获取证书详细信息: {cert_file}[/cyan]")
        
        try:
            cmd = [
                self.keytool_path, "-printcert",
                "-file", cert_file,
                "-v"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]❌ 无法获取证书信息: {result.stderr}[/red]")
                return None
            
            # 解析证书信息
            cert_info = {}
            lines = result.stdout.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('Owner:'):
                    cert_info['owner'] = line.replace('Owner:', '').strip()
                elif line.startswith('Issuer:'):
                    cert_info['issuer'] = line.replace('Issuer:', '').strip()
                elif line.startswith('Serial number:'):
                    cert_info['serial'] = line.replace('Serial number:', '').strip()
                elif line.startswith('Valid from:'):
                    cert_info['valid_from'] = line.replace('Valid from:', '').strip()
                elif 'until:' in line:
                    cert_info['valid_until'] = line.split('until:')[1].strip()
                elif line.startswith('Certificate fingerprints:'):
                    cert_info['fingerprints_start'] = True
            
            # 显示证书详细信息
            if cert_info:
                table = Table(title="📜 证书详细信息", border_style="blue")
                table.add_column("项目", style="cyan", width=15)
                table.add_column("值", style="white", width=60)
                
                for key, value in cert_info.items():
                    if not key.endswith('_start'):
                        display_key = key.replace('_', ' ').title()
                        table.add_row(display_key, value)
                
                console.print(table)
            
            return cert_info
            
        except Exception as e:
            console.print(f"[red]❌ 获取证书信息时发生错误: {e}[/red]")
            return None
    
    def process_keystore(self, keystore_path, password, alias=None, output_dir="certificates"):
        """处理keystore，提取证书并计算MD5"""
        console.print(Panel.fit(
            f"[bold cyan]🔐 JKS证书提取与MD5计算[/bold cyan]\n"
            f"Keystore: {keystore_path}\n"
            f"输出目录: {output_dir}",
            border_style="cyan"
        ))
        
        # 验证keystore
        if not self.validate_keystore(keystore_path, password):
            return None
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取别名列表
        aliases = self.list_aliases(keystore_path, password)
        if not aliases:
            return None
        
        # 确定要处理的别名
        target_aliases = []
        if alias:
            # 验证指定的别名是否存在
            alias_names = [a[0] for a in aliases]
            if alias in alias_names:
                target_aliases = [(alias, [a[1] for a in aliases if a[0] == alias][0])]
            else:
                console.print(f"[red]❌ 指定的别名 '{alias}' 不存在[/red]")
                return None
        else:
            # 处理所有别名
            target_aliases = aliases
        
        results = []
        
        for alias_name, entry_type in target_aliases:
            console.print(f"\n[bold yellow]处理别名: {alias_name} ({entry_type})[/bold yellow]")
            
            # 导出证书
            cert_file = os.path.join(output_dir, f"{alias_name}_certificate.crt")
            exported_cert = self.export_certificate(keystore_path, password, alias_name, cert_file)
            
            if exported_cert:
                # 计算MD5
                md5_value = self.calculate_certificate_md5(exported_cert)
                
                # 获取详细信息
                cert_details = self.get_certificate_details(exported_cert)
                
                result = {
                    'alias': alias_name,
                    'type': entry_type,
                    'cert_file': exported_cert,
                    'md5': md5_value,
                    'details': cert_details
                }
                
                results.append(result)
        
        # 显示汇总结果
        if results:
            self._show_summary_results(results)
        
        return results
    
    def _show_summary_results(self, results):
        """显示汇总结果"""
        console.print("\n" + "="*60)
        console.print("[bold green]🎉 证书提取完成![/bold green]")
        
        table = Table(title="📊 提取结果汇总", border_style="green")
        table.add_column("别名", style="cyan", width=15)
        table.add_column("类型", style="yellow", width=12)
        table.add_column("MD5签名", style="green", width=32)
        table.add_column("证书文件", style="blue", width=25)
        
        for result in results:
            table.add_row(
                result['alias'],
                result['type'],
                result['md5'][:32] if result['md5'] else "N/A",
                os.path.basename(result['cert_file']) if result['cert_file'] else "N/A"
            )
        
        console.print(table)
        
        # 显示Android APK签名相关的重要信息
        for result in results:
            if result['type'] == 'Private Key' and result['md5']:
                console.print(f"\n[bold green]🤖 Android APK签名MD5: {result['md5']}[/bold green]")
                console.print(f"[yellow]💡 这个MD5值用于验证APK签名证书[/yellow]")


def main():
    parser = argparse.ArgumentParser(
        description="JKS证书提取和MD5计算工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python certificate_extractor.py keystore.jks password123           # 提取所有证书
  python certificate_extractor.py keystore.jks password123 -a mykey  # 提取指定别名的证书
  python certificate_extractor.py keystore.jks password123 -o certs  # 指定输出目录
        """
    )
    
    parser.add_argument("keystore", help="JKS keystore文件路径")
    parser.add_argument("password", help="Keystore密码")
    parser.add_argument("-a", "--alias", help="指定证书别名 (默认处理所有)")
    parser.add_argument("-o", "--output", default="certificates", help="输出目录 (默认: certificates)")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细输出")
    
    args = parser.parse_args()
    
    # 创建提取器
    extractor = CertificateExtractor()
    
    try:
        # 处理keystore
        results = extractor.process_keystore(
            args.keystore, 
            args.password, 
            args.alias, 
            args.output
        )
        
        if results:
            console.print("\n[bold green]✅ 处理完成![/bold green]")
        else:
            console.print("\n[bold red]❌ 处理失败![/bold red]")
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️ 用户中断操作[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]💥 未处理的错误: {e}[/red]")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 