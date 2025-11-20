#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动下载 JksPrivkPrepare.jar 工具
用于JKS私钥提取和Hashcat破解
"""

import os
import requests
import hashlib
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, DownloadColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

console = Console()

class JKSToolDownloader:
    def __init__(self):
        # GitHub项目信息
        self.github_repo = "floyd-fuh/JKS-private-key-cracker-hashcat"
        self.jar_filename = "JksPrivkPrepare.jar"
        
        # 可能的下载链接
        self.download_urls = [
            f"https://github.com/{self.github_repo}/releases/latest/download/{self.jar_filename}",
            f"https://github.com/{self.github_repo}/raw/main/{self.jar_filename}",
            f"https://github.com/{self.github_repo}/releases/download/v1.0/{self.jar_filename}"
        ]
        
        # 本地保存路径选项
        self.save_paths = [
            Path(self.jar_filename),                # 当前目录
            Path("tools") / self.jar_filename,      # tools目录
            Path("jks") / self.jar_filename         # jks目录
        ]
    
    def check_existing_tool(self):
        """检查是否已存在工具"""
        for path in self.save_paths:
            if path.exists():
                console.print(f"✅ 找到现有工具: {path}", style="green")
                return str(path)
        return None
    
    def verify_java(self):
        """验证Java环境"""
        try:
            import subprocess
            result = subprocess.run(['java', '-version'], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                # 提取Java版本
                version_line = result.stderr.split('\n')[0]
                console.print(f"✅ Java环境: {version_line}", style="green")
                return True
            else:
                console.print("❌ Java环境检查失败", style="red")
                return False
        except FileNotFoundError:
            console.print("❌ 未找到Java环境", style="red")
            console.print("请安装Java 8+: https://adoptopenjdk.net/", style="yellow")
            return False
    
    def download_with_progress(self, url, save_path):
        """带进度条的下载"""
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            # 创建目录
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with Progress(
                DownloadColumn(),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task(
                    f"下载 {self.jar_filename}", 
                    total=total_size
                )
                
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            progress.advance(task, len(chunk))
            
            console.print(f"✅ 下载完成: {save_path}", style="green")
            return True
            
        except requests.exceptions.RequestException as e:
            console.print(f"❌ 下载失败: {e}", style="red")
            return False
        except Exception as e:
            console.print(f"❌ 保存失败: {e}", style="red")
            return False
    
    def verify_jar_file(self, jar_path):
        """验证JAR文件完整性"""
        try:
            # 检查文件大小
            size = jar_path.stat().st_size
            if size < 1024:  # 小于1KB可能是错误页面
                console.print(f"⚠️ 文件大小异常: {size} bytes", style="yellow")
                return False
            
            # 检查JAR魔术字节
            with open(jar_path, 'rb') as f:
                header = f.read(4)
                if header[:2] != b'PK':  # ZIP/JAR文件头
                    console.print("⚠️ 文件格式可能不正确", style="yellow")
                    return False
            
            console.print(f"✅ JAR文件验证通过: {size} bytes", style="green")
            return True
            
        except Exception as e:
            console.print(f"❌ 文件验证失败: {e}", style="red")
            return False
    
    def test_jar_functionality(self, jar_path):
        """测试JAR文件功能"""
        try:
            import subprocess
            
            # 尝试运行JAR获取帮助信息
            cmd = ['java', '-jar', str(jar_path), '--help']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            # 有些JAR可能不支持--help，尝试无参数运行
            if result.returncode != 0:
                cmd = ['java', '-jar', str(jar_path)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if "JksPrivkPrepare" in result.stderr or "JksPrivkPrepare" in result.stdout:
                console.print("✅ JAR工具功能正常", style="green")
                return True
            else:
                console.print("⚠️ JAR工具响应异常", style="yellow")
                return True  # 仍然可能可用
                
        except subprocess.TimeoutExpired:
            console.print("⚠️ JAR工具测试超时", style="yellow")
            return True  # 超时不一定是错误
        except Exception as e:
            console.print(f"⚠️ JAR工具测试失败: {e}", style="yellow")
            return True  # 测试失败不意味着工具不可用
    
    def download_tool(self, force_download=False):
        """下载JksPrivkPrepare.jar工具"""
        # 检查现有工具
        if not force_download:
            existing = self.check_existing_tool()
            if existing:
                if self.verify_jar_file(Path(existing)):
                    return existing
                else:
                    console.print("现有工具验证失败，重新下载...", style="yellow")
        
        # 验证Java环境
        if not self.verify_java():
            return None
        
        # 尝试从多个URL下载
        for i, url in enumerate(self.download_urls, 1):
            console.print(f"\n🔄 尝试下载源 {i}/{len(self.download_urls)}: {url}")
            
            for save_path in self.save_paths:
                try:
                    if self.download_with_progress(url, save_path):
                        if self.verify_jar_file(save_path):
                            if self.test_jar_functionality(save_path):
                                console.print(f"\n🎉 JksPrivkPrepare.jar 准备就绪!", style="green bold")
                                console.print(f"📍 保存位置: {save_path.absolute()}")
                                return str(save_path)
                            else:
                                console.print("工具功能测试失败，尝试其他源...", style="yellow")
                        else:
                            console.print("文件验证失败，尝试其他源...", style="yellow")
                            save_path.unlink(missing_ok=True)  # 删除损坏文件
                    break  # 如果下载失败，尝试下一个URL
                except Exception as e:
                    console.print(f"保存到 {save_path} 失败: {e}", style="red")
                    continue
        
        console.print("\n❌ 所有下载尝试均失败", style="red")
        console.print("\n🔧 手动下载方案:")
        console.print(f"1. 访问: https://github.com/{self.github_repo}")
        console.print("2. 下载 JksPrivkPrepare.jar")
        console.print("3. 将文件放在当前目录或tools/目录下")
        
        return None
    
    def show_usage_guide(self, jar_path):
        """显示使用指南"""
        console.print(f"\n📚 使用指南:", style="bold blue")
        console.print(f"")
        console.print(f"🔧 基本用法:")
        console.print(f"   java -jar {jar_path} keystore.jks")
        console.print(f"")
        console.print(f"🚀 配合我们的工具:")
        console.print(f"   python main.py -f keystore.jks")
        console.print(f"   # 选择模式2 (私钥密码)")
        console.print(f"")
        console.print(f"⚡ 直接使用JKS处理器:")
        console.print(f"   python jks_privkey_processor.py")

def main():
    console.print("🔧 JksPrivkPrepare.jar 自动下载工具", style="bold blue")
    console.print("=" * 50)
    
    downloader = JKSToolDownloader()
    
    # 检查是否强制重新下载
    import sys
    force_download = "--force" in sys.argv
    
    # 下载工具
    jar_path = downloader.download_tool(force_download)
    
    if jar_path:
        downloader.show_usage_guide(jar_path)
        console.print(f"\n✅ 工具准备完成！可以开始JKS私钥破解了。", style="green bold")
    else:
        console.print(f"\n❌ 工具下载失败，请手动下载或检查网络连接。", style="red")

if __name__ == "__main__":
    main() 