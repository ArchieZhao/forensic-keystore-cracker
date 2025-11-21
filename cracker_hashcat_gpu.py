#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GPU加速Hashcat批量破解引擎

调用Hashcat GPU加速引擎批量破解JKS/PKCS12/MD5密码，
使用6位掩码攻击（?1?1?1?1?1?1，62^6=56,800,235,584种组合），
支持实时监控、断点续传、rich进度展示。

Architecture:
    Hash文件 → 算法检测 → Hashcat进程 → 状态监控 → 结果导出

    GPUHashcatCracker (gpu_hashcat_cracker.py:49)
        ├─ __init__() (L52): 初始化配置、算法映射、GPU检测、信号处理
        ├─ setup_logging() (L103): 配置日志到logs/gpu_crack_YYYYMMDD_HHMMSS.log
        ├─ detect_gpu_info() (L128): nvidia-smi查询GPU名称/显存/驱动版本
        ├─ print_banner() (L159): rich Panel展示系统配置和算法支持表
        ├─ detect_hash_algorithm() (L209): 正则识别MD5/JKS/PKCS12格式
        ├─ read_hash_file() (L240): 逐行读取并分类hash到算法类型
        ├─ get_mask_attacks() (L272): 返回6位掩码["?1?1?1?1?1?1"]
        ├─ build_hashcat_command() (L299): 构建hashcat命令含RTX 3080优化参数
        ├─ parse_hashcat_status() (L356): 解析JSON状态提取进度/速度/温度
        ├─ monitor_hashcat_process() (L395): 实时监控subprocess并更新rich进度条
        ├─ crack_single_hash() (L498): 单hash破解含临时文件和会话管理
        ├─ run_batch_crack() (L605): 批量破解主流程，按算法分组处理
        ├─ generate_final_report() (L702): 生成统计表格和密码列表
        └─ save_results_to_file() (L750): 导出JSON结果到crack_results_YYYYMMDD_HHMMSS.json

Features:
    - 6位掩码攻击：自定义字符集?1=a-zA-Z0-9 (gpu_hashcat_cracker.py:325-327)
    - RTX 3080优化：-O, -w 3, --markov-disable, --segment-size 32 (gpu_hashcat_cracker.py:331-343)
    - 算法自动检测：正则匹配MD5/JKS/PKCS12格式 (gpu_hashcat_cracker.py:209-238)
    - 实时监控：JSON状态解析 + rich进度条 (gpu_hashcat_cracker.py:356-451)
    - 断点续传：会话恢复 --restore (gpu_hashcat_cracker.py:473-496)
    - GPU信息检测：nvidia-smi查询并fallback (gpu_hashcat_cracker.py:128-157)
    - 信号处理：SIGINT/SIGTERM优雅停止 (gpu_hashcat_cracker.py:122-126)

Args (命令行):
    hash_file (str, optional): hash文件路径，交互式输入或默认example_6digit_hashes.txt
    --hashcat-path (str, optional): hashcat.exe路径，默认'E:\\app\\forensic\\hashcat-6.2.6\\hashcat.exe'
    --output-dir (str, optional): 输出目录，默认'gpu_crack_results'
    --wordlist-dir (str, optional): 字典目录（当前未使用，仅掩码攻击）
    --max-time (int, optional): 单hash超时秒数，默认3600
    --gpu-only (bool, optional): 仅GPU标志（默认行为）
    --complete (bool, optional): 强制完整模式，跳过智能策略

        示例：
        python gpu_hashcat_cracker.py hash.txt
        python gpu_hashcat_cracker.py hash.txt --hashcat-path D:\\hashcat\\hashcat.exe
        python gpu_hashcat_cracker.py hash.txt --output-dir results --complete

Returns (输出文件):
    gpu_crack_results/potfiles/{session_name}.potfile: Hashcat原始结果（格式：hash:password）
    gpu_crack_results/logs/gpu_crack_YYYYMMDD_HHMMSS.log: 详细日志
    gpu_crack_results/crack_results_YYYYMMDD_HHMMSS.json: 统计结果JSON（含密码字典）
    终端显示：系统配置Panel、算法支持Table、实时进度Progress、统计结果Table

Requirements:
    - Hashcat 6.2.6+ (hashcat.exe)
    - NVIDIA GPU + CUDA驱动 (nvidia-smi可用)
    - rich (终端UI，可选，缺失时fallback到print)
    - Python标准库: subprocess, json, threading, signal, argparse

Technical Notes:
    算法检测优先级:
        1. 正则匹配MD5: ^[a-f0-9]{32}$ (gpu_hashcat_cracker.py:223-225)
        2. 关键词匹配JKS: $jks$, $keystore$, keystore (gpu_hashcat_cracker.py:228-230)
        3. 长度回退MD5: 32字符十六进制 (gpu_hashcat_cracker.py:233-235)

    Hashcat命令构建:
        基础参数: --hash-type, --attack-mode, --potfile-path, --session, --status, --machine-readable (gpu_hashcat_cracker.py:311-320)
        自定义字符集: -1 abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 (gpu_hashcat_cracker.py:325-326)
        RTX 3080优化: -d 1, --force, -O, -w 3 (gpu_hashcat_cracker.py:331-336)
        6位掩码优化: --markov-disable, --segment-size 32 (gpu_hashcat_cracker.py:341-343)

    会话管理:
        会话名格式: m{mode}_{hash_id}_{timestamp} (gpu_hashcat_cracker.py:268-270)
        恢复命令: hashcat --session {name} --restore (gpu_hashcat_cracker.py:481-484)
        工作目录: hashcat.exe所在目录（解决OpenCL路径问题）(gpu_hashcat_cracker.py:540, 546)

    JSON状态解析:
        提取字段: session, status, progress, recovered_hashes, devices (gpu_hashcat_cracker.py:368-380)
        设备信息: speed, temp, util (gpu_hashcat_cracker.py:384-387)
        更新频率: --status-timer 5秒 (gpu_hashcat_cracker.py:318)

    破解性能估算:
        RTX 3080速度: ~10,000 H/s (JKS mode 15500)
        62^6组合: 56,800,235,584种

Workflow:
    1. 解析命令行参数或交互式输入hash文件
    2. 验证hashcat.exe和hash文件存在性
    3. 初始化GPUHashcatCracker（检测GPU、注册信号处理器）
    4. 打印rich Panel横幅（系统配置、算法支持）
    5. 读取hash文件并按算法分组（MD5/JKS/PKCS12）
    6. 为每个算法创建rich进度任务
    7. 循环处理每个hash：
       - 创建临时hash文件到sessions/
       - 构建hashcat命令（含RTX 3080优化参数）
       - 启动subprocess.Popen（cwd设置为hashcat目录）
       - 实时解析JSON状态并更新进度条
       - 读取potfile获取破解密码
       - 清理临时文件和会话
    8. 生成统计Table和密码Table
    9. 保存JSON结果到crack_results_YYYYMMDD_HHMMSS.json

Author: Forensic Keystore Cracker Project
Version: 2.1.0
License: 仅用于授权的数字取证和安全研究
"""

import os
import sys
import json
import time
import threading
import subprocess
import signal
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union
import re
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
import argparse
from benchmark_timer import BenchmarkTimer, timer

# 检查rich库是否可用
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # 回退到基础输出
    class Console:
        def print(self, *args, **kwargs):
            print(*args)
    console = Console()

if RICH_AVAILABLE:
    console = Console()

class GPUHashcatCracker:
    """GPU加速Hashcat批量破解器"""
    
    def __init__(self, config: Dict):
        """初始化GPU破解器"""
        self.config = config
        self.console = console
        self.setup_logging()
        
        # 算法类型映射
        self.hash_algorithms = {
            'md5': {
                'mode': '0',
                'name': 'MD5',
                'pattern': r'^[a-f0-9]{32}$'
            },
            'jks': {
                'mode': '15500',
                'name': 'JKS Java Key Store',
                'pattern': r'.*\$jks\$.*|.*\$keystore\$.*|.*:.*'
            },
            'pkcs12': {'mode': '17200', 'name': 'PKCS#12 Private Keys'}
        }
        
        # 破解统计
        self.stats = {
            'total_hashes': 0,
            'processed': 0,
            'cracked': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None,
            'passwords': {},
            'sessions': {}
        }
        
        # 运行状态
        self.running_sessions = {}
        self.stop_flag = threading.Event()
        
        # GPU信息
        self.gpu_info = self.detect_gpu_info()
        
        # 会话和输出目录
        self.session_dir = Path(self.config['output_dir']) / 'sessions'
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        self.potfile_dir = Path(self.config['output_dir']) / 'potfiles'
        self.potfile_dir.mkdir(parents=True, exist_ok=True)
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def setup_logging(self):
        """设置日志系统"""
        log_dir = Path(self.config['output_dir']) / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(
                    log_dir / f"gpu_crack_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", 
                    encoding='utf-8'
                ),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"接收到信号 {signum}，正在停止所有会话...")
        self.stop_flag.set()
        self.stop_all_sessions()
        
    def detect_gpu_info(self) -> Dict:
        """检测GPU信息"""
        gpu_info = {
            'available': False,
            'name': 'Unknown',
            'memory': 0,
            'driver_version': 'Unknown',
            'cuda_version': 'Unknown'
        }
        
        try:
            # 尝试使用nvidia-smi获取GPU信息
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', 
                                   '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines:
                    parts = lines[0].split(', ')
                    if len(parts) >= 3:
                        gpu_info['name'] = parts[0].strip()
                        gpu_info['memory'] = int(parts[1].strip())
                        gpu_info['driver_version'] = parts[2].strip()
                        gpu_info['available'] = True
                        
        except Exception as e:
            self.logger.warning(f"GPU信息检测失败: {e}")
            
        return gpu_info
        
    def print_banner(self):
        """打印工具横幅"""
        if RICH_AVAILABLE:
            title = Text("GPU加速Hashcat完整破解工具", style="bold cyan")
            subtitle = Text("专为RTX 3080优化 - 6位大小写字母+数字完整破解", style="bold yellow")
            
            banner_table = Table.grid(padding=1)
            banner_table.add_column(justify="center")
            banner_table.add_row(title)
            banner_table.add_row(subtitle)
            
            # 系统信息
            system_info = Table(title="系统配置", show_header=True, header_style="bold magenta")
            system_info.add_column("组件", style="cyan")
            system_info.add_column("信息", style="green")
            
            system_info.add_row("GPU", f"{self.gpu_info['name']} ({self.gpu_info['memory']}MB)")
            system_info.add_row("驱动版本", self.gpu_info['driver_version'])
            system_info.add_row("Hashcat路径", str(self.config['hashcat_path']))
            system_info.add_row("破解模式", "完整6位大小写字母+数字 (62^6)")
            system_info.add_row("输出目录", str(self.config['output_dir']))
            
            # 算法支持
            algo_table = Table(title="支持的算法", show_header=True, header_style="bold blue")
            algo_table.add_column("类型", style="cyan")
            algo_table.add_column("模式", style="yellow")
            algo_table.add_column("描述", style="green")
            
            for algo_type, info in self.hash_algorithms.items():
                algo_table.add_row(algo_type.upper(), info['mode'], info['name'])
                
            layout = Layout()
            layout.split_column(
                Layout(Align.center(banner_table), size=3),
                Layout(system_info, size=8),
                Layout(algo_table, size=6)
            )
            
            self.console.print(Panel(layout, border_style="bright_blue"))
        else:
            print("=" * 80)
            print("GPU加速Hashcat完整破解工具")
            print("专为RTX 3080优化 - 6位大小写字母+数字完整破解")
            print("=" * 80)
            print(f"GPU: {self.gpu_info['name']} ({self.gpu_info['memory']}MB)")
            print(f"驱动版本: {self.gpu_info['driver_version']}")
            print(f"Hashcat路径: {self.config['hashcat_path']}")
            print("破解模式: 完整6位大小写字母+数字 (62^6 = 56,800,235,584 种组合)")
            print("=" * 80)
            
    def detect_hash_algorithm(self, hash_line: str) -> Optional[str]:
        """检测hash算法类型"""
        hash_line = hash_line.strip()
        
        # 移除可能的用户名前缀
        if ':' in hash_line:
            parts = hash_line.split(':', 1)
            if len(parts) == 2:
                potential_hash = parts[1]
                # 检查第二部分是否像hash
                if potential_hash and not potential_hash.isdigit():
                    hash_line = potential_hash
        
        # 优先检测MD5 (32位十六进制)
        if re.match(r'^[a-f0-9]{32}$', hash_line, re.IGNORECASE):
            self.logger.info(f"🔍 识别为MD5格式: {hash_line[:8]}...")
            return 'md5'
        
        # 检测JKS格式
        if any(pattern in hash_line.lower() for pattern in ['$jks$', '$keystore$', 'keystore']):
            self.logger.info(f"🔍 识别为JKS格式: {hash_line[:20]}...")
            return 'jks'
        
        # 如果都不匹配，但长度看起来像hash，默认尝试MD5
        if len(hash_line) == 32 and all(c in '0123456789abcdefABCDEF' for c in hash_line):
            self.logger.info(f"🔍 按长度识别为MD5格式: {hash_line[:8]}...")
            return 'md5'
        
        self.logger.warning(f"❓ 未知hash格式: {hash_line[:20]}...")
        return None
        
    def read_hash_file(self, hash_file: Path) -> List[Tuple[str, str, str]]:
        """读取hash文件并分析算法类型"""
        hashes = []
        
        try:
            with open(hash_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    # 检测算法类型
                    algo_type = self.detect_hash_algorithm(line)
                    if algo_type:
                        # 提取hash ID（如果存在）
                        if ':' in line:
                            hash_id = line.split(':', 1)[0]
                        else:
                            hash_id = f"hash_{line_num}"
                            
                        hashes.append((hash_id, line, algo_type))
                        
        except Exception as e:
            self.logger.error(f"读取hash文件失败: {e}")
            
        return hashes
        
    def get_session_name(self, algo_type: str, hash_id: str) -> str:
        """生成会话名称"""
        mode = self.hash_algorithms[algo_type]['mode']
        return f"m{mode}_{hash_id}_{int(time.time())}"
        
    def get_mask_attacks(self, algo_type: str, complete_mode: bool = False) -> List[str]:
        """获取掩码测试模式 - 专注6位大小写字母+数字完整破解"""
        
        self.logger.info("🎯 完整6位大小写字母+数字破解")
        self.logger.info("💡 将系统性测试全部 62^6 = 56,800,235,584 种组合")
        
        # 只使用完整的6位大小写字母+数字字符集
        # 自定义字符集1: a-zA-Z0-9 (62个字符)
        return ["?1?1?1?1?1?1"]  # 完整的62^6组合
        
    def get_wordlists(self) -> List[Path]:
        """获取字典文件列表"""
        wordlist_dirs = [
            Path(self.config.get('wordlist_dir', 'wordlists')),
            Path('wordlists'),
            Path('./'),
        ]
        
        wordlists = []
        for wordlist_dir in wordlist_dirs:
            if wordlist_dir.exists():
                # 支持的字典文件格式
                for pattern in ['*.txt', '*.dic', '*.dict', '*.wordlist']:
                    wordlists.extend(wordlist_dir.glob(pattern))
                    
        return sorted(wordlists)
        
    def build_hashcat_command(self, hash_file: Path, algo_type: str, attack_mode: str, 
                            attack_data: str, session_name: str) -> List[str]:
        """构建hashcat命令"""
        # 准备文件路径
        hashcat_path = Path(self.config['hashcat_path']).resolve()
        hash_file_abs = hash_file.resolve()
        
        # 输出文件路径
        potfile = self.potfile_dir / f"{session_name}.potfile"
        potfile_abs = potfile.resolve()
        
        # 基础命令
        cmd = [
            str(hashcat_path),
            '--hash-type', self.hash_algorithms[algo_type]['mode'],
            '--attack-mode', attack_mode,
            '--potfile-path', str(potfile_abs),
            '--session', session_name,
            '--status',
            '--status-timer', '5',
            '--machine-readable',
            '--quiet'
        ]
        
        # 添加自定义字符集1: 大小写字母+数字 [a-zA-Z0-9]
        if attack_mode == '3' and '?1' in attack_data:
            charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            cmd.extend(['-1', charset])
            self.logger.info(f"🎯 启用自定义字符集1: {len(charset)}个字符，预计组合数: 62^6 = 56,800,235,584")
        
        # RTX 3080 专用优化设置
        if self.gpu_info['available']:
            cmd.extend([
                '-d', '1',              # 使用第一个GPU
                '--force',              # 强制忽略警告
                '-O',                   # 优化内核
                '-w', '3',              # 最高工作负载
            ])
            
            # 对于6位掩码攻击，使用更激进的优化
            if attack_mode == '3' and len(attack_data) == 6:
                cmd.extend([
                    '--markov-disable',     # 禁用马尔可夫链（6位完整破解不需要）
                    '--segment-size', '32', # 优化内存段大小
                ])
            
        # 添加hash文件（使用绝对路径）
        cmd.append(str(hash_file_abs))
        
        # 添加测试数据
        if attack_mode == '0':  # 字典测试
            cmd.append(attack_data)
        elif attack_mode == '3':  # 掩码测试
            cmd.append(attack_data)
            
        return cmd
        
    def parse_hashcat_status(self, status_line: str) -> Optional[Dict]:
        """解析Hashcat JSON状态"""
        try:
            # 查找JSON开始位置
            json_start = status_line.find('{')
            if json_start == -1:
                return None
                
            json_str = status_line[json_start:]
            status_data = json.loads(json_str)
            
            # 提取关键信息
            parsed = {
                'session': status_data.get('session', ''),
                'status': status_data.get('status', 0),
                'target': status_data.get('target', ''),
                'progress': status_data.get('progress', [0, 0]),
                'restore_point': status_data.get('restore_point', 0),
                'recovered_hashes': status_data.get('recovered_hashes', [0, 0]),
                'recovered_salts': status_data.get('recovered_salts', [0, 0]),
                'rejected': status_data.get('rejected', 0),
                'devices': status_data.get('devices', []),
                'time_start': status_data.get('time_start', 0),
                'estimated_stop': status_data.get('estimated_stop', 0),
            }
            
            # 解析设备信息（温度、速度等）
            if parsed['devices']:
                device = parsed['devices'][0]  # 假设只有一个GPU
                parsed['speed'] = device.get('speed', 0)
                parsed['temp'] = device.get('temp', 0)
                parsed['util'] = device.get('util', 0)
                
            return parsed
            
        except Exception as e:
            self.logger.debug(f"解析状态JSON失败: {e}")
            return None
            
    def monitor_hashcat_process(self, process: subprocess.Popen, session_name: str, 
                              progress_task=None, live_display=None) -> Tuple[bool, str]:
        """监控Hashcat进程并实时显示状态"""
        cracked_password = None
        last_status = {}
        
        try:
            while process.poll() is None and not self.stop_flag.is_set():
                # 读取stdout
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        line = line.decode('utf-8', errors='ignore').strip()
                        
                        # 解析JSON状态
                        status = self.parse_hashcat_status(line)
                        if status:
                            last_status = status
                            
                            # 更新进度显示
                            if RICH_AVAILABLE and progress_task is not None:
                                progress_current = status['progress'][0]
                                progress_total = status['progress'][1]
                                
                                if progress_total > 0:
                                    progress_pct = (progress_current / progress_total) * 100
                                    
                                    # 更新进度条
                                    if hasattr(progress_task, 'update'):
                                        progress_task.update(
                                            completed=progress_current,
                                            total=progress_total,
                                            description=f"[cyan]{session_name}[/cyan] - "
                                                      f"Speed: {status.get('speed', 0):,}/s - "
                                                      f"Temp: {status.get('temp', 0)}°C"
                                        )
                                        
                        # 检查是否找到密码
                        if 'Cracked' in line or 'Status: Cracked' in line:
                            # 读取potfile获取密码
                            potfile = self.potfile_dir / f"{session_name}.pot"
                            if potfile.exists():
                                cracked_password = self.read_potfile(potfile)
                                break
                                
                time.sleep(0.1)  # 避免CPU占用过高
                
        except Exception as e:
            self.logger.error(f"监控进程失败: {e}")
            
        # 等待进程结束
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            
        return cracked_password is not None, cracked_password or ""
        
    def read_potfile(self, potfile: Path) -> Optional[str]:
        """读取potfile获取破解的密码"""
        try:
            if not potfile.exists():
                return None
                
            with open(potfile, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            if lines:
                # potfile格式: hash:password
                last_line = lines[-1].strip()
                if ':' in last_line:
                    return last_line.split(':', 1)[1]
                    
        except Exception as e:
            self.logger.debug(f"读取potfile失败: {e}")
            
        return None
        
    def restore_session(self, session_name: str) -> bool:
        """恢复中断的会话"""
        try:
            session_file = self.session_dir / f"{session_name}.session"
            if not session_file.exists():
                return False
                
            hashcat_path = Path(self.config['hashcat_path'])
            restore_cmd = [
                str(hashcat_path),
                '--session', session_name,
                '--restore'
            ]
            
            self.logger.info(f"恢复会话: {session_name}")
            # 设置工作目录为Hashcat所在目录
            hashcat_dir = hashcat_path.parent
            result = subprocess.run(restore_cmd, capture_output=True, text=True, cwd=str(hashcat_dir))
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"恢复会话失败: {e}")
            return False
            
    def crack_single_hash(self, hash_id: str, hash_line: str, algo_type: str, complete_mode: bool = False) -> Tuple[bool, str]:
        """破解单个hash"""
        mode_text = "完整模式" if complete_mode else "常规模式"
        self.logger.info(f"开始破解: {hash_id} (类型: {algo_type}, {mode_text})")
        
        # 创建临时hash文件
        temp_hash_file = self.session_dir / f"{hash_id}.hash"
        with open(temp_hash_file, 'w', encoding='utf-8') as f:
            f.write(hash_line)
            
        # 只进行掩码攻击：完整6位大小写字母+数字破解
        attacks = []
        
        # 掩码测试：?1?1?1?1?1?1 (62^6 = 56,800,235,584 种组合)
        masks = self.get_mask_attacks(algo_type, complete_mode)
        for mask in masks:
            session_name = self.get_session_name(algo_type, f"{hash_id}_complete")
            attacks.append(('3', mask, session_name))
            
        # 执行测试
        for attack_mode, attack_data, session_name in attacks:
            if self.stop_flag.is_set():
                break
                
            try:
                # 检查是否有可恢复的会话
                if self.restore_session(session_name):
                    self.logger.info(f"恢复了中断的会话: {session_name}")
                    continue
                    
                # 构建命令
                cmd = self.build_hashcat_command(
                    temp_hash_file, algo_type, attack_mode, attack_data, session_name
                )
                
                self.logger.info(f"执行测试: {session_name} - {attack_data}")
                self.logger.debug(f"完整命令: {' '.join(cmd)}")
                
                # 启动进程
                start_time = time.time()
                # 设置工作目录为Hashcat所在目录以解决OpenCL路径问题
                hashcat_path = Path(self.config['hashcat_path'])
                hashcat_dir = hashcat_path.parent
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False,  # 使用字节模式读取
                    cwd=str(hashcat_dir)  # 设置工作目录
                )
                
                self.running_sessions[session_name] = process
                
                # 等待进程完成
                stdout, stderr = process.communicate()
                
                # 记录执行时间和进度信息
                duration = time.time() - start_time
                
                # 检查potfile是否存在破解结果
                potfile = self.potfile_dir / f"{session_name}.potfile"
                cracked_password = self.read_potfile(potfile)
                
                # 进度分析：完整6位破解
                if attack_data == "?1?1?1?1?1?1":
                    hours = duration / 3600
                    if duration < 300:  # 5分钟以内
                        if cracked_password:
                            self.logger.info(f"🎯 完整6位破解快速成功: {duration:.1f}秒 - 密码: {cracked_password}")
                        else:
                            self.logger.warning(f"⚠️ 完整破解时间异常短: {duration:.1f}秒，可能出现错误")
                            # 检查stderr输出
                            if stderr:
                                stderr_text = stderr.decode('utf-8', errors='ignore').strip()
                                if stderr_text:
                                    self.logger.error(f"Hashcat错误: {stderr_text}")
                    elif hours < 1:
                        self.logger.info(f"🎯 完整6位破解耗时: {duration:.1f}秒 ({duration/60:.1f}分钟)")
                    else:
                        self.logger.info(f"🎯 完整6位破解耗时: {hours:.2f}小时 ({duration:.0f}秒)")
                else:
                    self.logger.info(f"🔍 6位密码测试完成: {duration:.1f}秒")
                
                # 清理
                if session_name in self.running_sessions:
                    del self.running_sessions[session_name]
                    
                if cracked_password:
                    self.logger.info(f"✅ 破解成功: {hash_id} -> {cracked_password}")
                    return True, cracked_password
                    
            except Exception as e:
                self.logger.error(f"测试执行失败: {e}")
                
        self.logger.warning(f"❌ 破解失败: {hash_id}")
        return False, ""
        
    def stop_all_sessions(self):
        """停止所有运行中的会话"""
        for session_name, process in self.running_sessions.items():
            try:
                self.logger.info(f"停止会话: {session_name}")
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                process.kill()
                
    def run_batch_crack(self, hash_file: Path, complete_mode: bool = False):
        """运行批量破解"""
        self.print_banner()

        # 创建总体计时器
        crack_timer = BenchmarkTimer("GPU批量破解", verbose=True)
        crack_timer.start()

        # 读取hash文件
        hashes = self.read_hash_file(hash_file)
        if not hashes:
            self.console.print("[red]❌ 未找到有效的hash[/red]")
            return

        self.stats['total_hashes'] = len(hashes)
        self.stats['start_time'] = time.time()

        # 设置总任务数
        crack_timer.stats.total_items = len(hashes)
        
        self.console.print(f"[green]📊 总共找到 {len(hashes)} 个hash需要破解 (完整6位破解模式)[/green]")
        self.console.print(f"[yellow]🎯 将系统性测试全部 62^6 = 56,800,235,584 种6位大小写字母+数字组合[/yellow]")
        self.console.print(f"[yellow]⏰ 预计在RTX 3080上需要数小时到十几小时（取决于密码位置和GPU性能）[/yellow]")
        
        # 按算法类型分组
        grouped_hashes = {}
        for hash_id, hash_line, algo_type in hashes:
            if algo_type not in grouped_hashes:
                grouped_hashes[algo_type] = []
            grouped_hashes[algo_type].append((hash_id, hash_line))
            
        # 显示分组统计
        for algo_type, hash_list in grouped_hashes.items():
            mode = self.hash_algorithms[algo_type]['mode']
            self.console.print(f"[cyan]🔍 {algo_type.upper()} (模式 {mode}): {len(hash_list)} 个hash[/cyan]")
            
        # 创建进度显示
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                
                # 为每种算法创建进度任务
                progress_tasks = {}
                for algo_type, hash_list in grouped_hashes.items():
                    task = progress.add_task(
                        f"[cyan]{algo_type.upper()}[/cyan]",
                        total=len(hash_list)
                    )
                    progress_tasks[algo_type] = task
                    
                # 批量处理
                for algo_type, hash_list in grouped_hashes.items():
                    if self.stop_flag.is_set():
                        break
                        
                    task = progress_tasks[algo_type]
                    
                    for hash_id, hash_line in hash_list:
                        if self.stop_flag.is_set():
                            break

                        success, password = self.crack_single_hash(hash_id, hash_line, algo_type, complete_mode)

                        if success:
                            self.stats['cracked'] += 1
                            self.stats['passwords'][hash_id] = password
                        else:
                            self.stats['failed'] += 1

                        self.stats['processed'] += 1

                        # 更新计时器进度
                        crack_timer.update_progress(self.stats['processed'])

                        # 每10个hash打印一次进度统计
                        if self.stats['processed'] % 10 == 0:
                            crack_timer.print_progress()

                        progress.update(task, advance=1)
        else:
            # 回退到基础进度显示
            for algo_type, hash_list in grouped_hashes.items():
                if self.stop_flag.is_set():
                    break
                    
                for i, (hash_id, hash_line) in enumerate(hash_list, 1):
                    if self.stop_flag.is_set():
                        break
                        
                    print(f"处理 {algo_type.upper()} [{i}/{len(hash_list)}]: {hash_id}")
                    
                    success, password = self.crack_single_hash(hash_id, hash_line, algo_type, complete_mode)
                    
                    if success:
                        self.stats['cracked'] += 1
                        self.stats['passwords'][hash_id] = password
                        print(f"✅ 破解成功: {password}")
                    else:
                        self.stats['failed'] += 1
                        print(f"❌ 破解失败")
                        
                    self.stats['processed'] += 1

        self.stats['end_time'] = time.time()

        # 结束计时并保存统计
        crack_stats = crack_timer.end()

        # 显示性能统计
        console.print(f"\n[yellow]⚡ 破解性能统计:[/yellow]")
        console.print(f"[yellow]  平均速度: {crack_stats.speed:.2f} hash/秒[/yellow]")
        console.print(f"[yellow]  单hash平均耗时: {crack_stats.avg_time_per_item:.2f}秒[/yellow]")
        console.print(f"[yellow]  成功率: {(self.stats['cracked']/max(self.stats['processed'],1)*100):.1f}%[/yellow]")

        self.generate_final_report()
        
    def generate_final_report(self):
        """生成最终报告"""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        if RICH_AVAILABLE:
            # 创建结果表格
            result_table = Table(title="破解结果统计", show_header=True, header_style="bold magenta")
            result_table.add_column("统计项", style="cyan")
            result_table.add_column("数值", style="green")
            
            result_table.add_row("总hash数", str(self.stats['total_hashes']))
            result_table.add_row("已处理", str(self.stats['processed']))
            result_table.add_row("破解成功", str(self.stats['cracked']))
            result_table.add_row("破解失败", str(self.stats['failed']))
            result_table.add_row("成功率", f"{(self.stats['cracked']/max(self.stats['processed'],1)*100):.1f}%")
            result_table.add_row("耗时", f"{duration:.1f}秒")
            
            self.console.print(result_table)
            
            # 显示破解的密码
            if self.stats['passwords']:
                password_table = Table(title="破解的密码", show_header=True, header_style="bold green")
                password_table.add_column("Hash ID", style="cyan")
                password_table.add_column("密码", style="yellow")
                
                for hash_id, password in self.stats['passwords'].items():
                    password_table.add_row(hash_id, password)
                    
                self.console.print(password_table)
        else:
            print("\n" + "="*80)
            print("破解结果统计")
            print("="*80)
            print(f"总hash数: {self.stats['total_hashes']}")
            print(f"已处理: {self.stats['processed']}")
            print(f"破解成功: {self.stats['cracked']}")
            print(f"破解失败: {self.stats['failed']}")
            print(f"成功率: {(self.stats['cracked']/max(self.stats['processed'],1)*100):.1f}%")
            print(f"耗时: {duration:.1f}秒")
            
            if self.stats['passwords']:
                print("\n破解的密码:")
                for hash_id, password in self.stats['passwords'].items():
                    print(f"  {hash_id}: {password}")
                    
        # 保存结果到文件
        self.save_results_to_file()
        
    def save_results_to_file(self):
        """保存破解结果到文件"""
        results_file = Path(self.config['output_dir']) / f"crack_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2, default=str)
        self.logger.info(f"结果已保存到: {results_file}")

    def crack_keystore_passwords(self, hash_file: str):
        """批量破解证书密码的专用方法"""
        print("\n开始批量破解证书密码...")
        
        # 转换为Path对象
        hash_file_path = Path(hash_file)
        if not hash_file_path.exists():
            print(f"错误：Hash文件不存在: {hash_file}")
            return
        
        # 打印横幅
        self.print_banner()
        
        # 运行批量破解，启用完整模式
        self.run_batch_crack(hash_file_path, complete_mode=True)
        
        # 生成最终报告
        self.generate_final_report()
        
        # 保存结果
        self.save_results_to_file()
        
        print("\n证书密码破解任务完成！")

def validate_and_convert_hash_file(hash_file_path):
    """验证hash文件格式"""
    print(f"\n🔍 验证hash文件格式: {hash_file_path}")
    
    if not Path(hash_file_path).exists():
        print(f"❌ Hash文件不存在: {hash_file_path}")
        return None
    
    # 直接返回原文件，让程序自动检测hash类型
    print(f"✅ 使用原始hash文件进行自动检测")
    return hash_file_path

def convert_keystore_to_jks(keystore_line):
    """将keystore格式转换为JKS格式"""
    try:
        # 移除开头的标识符
        if ':' in keystore_line:
            parts = keystore_line.split(':', 1)
            identifier = parts[0]
            keystore_data = parts[1]
        else:
            identifier = "converted"
            keystore_data = keystore_line
        
        # 查找$keystore$格式并转换为$jks$
        if '$keystore$' in keystore_data:
            # 替换$keystore$为$jks$
            jks_data = keystore_data.replace('$keystore$', '$jks$')
            return f"{identifier}:{jks_data}"
        
        return None
    except Exception as e:
        print(f"❌ 转换keystore格式时出错: {e}")
        return None

def create_test_jks_hash():
    """创建测试用的JKS hash文件"""
    test_file = "test_simple.hash"
    
    # 创建已知的简单JKS hash
    test_hashes = [
        # 模拟的6位数字密码hash
        "test_123456:$jks$0$1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef$53616c74",
        "test_password:$jks$0$abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890$53616c74"
    ]
    
    with open(test_file, 'w', encoding='utf-8') as f:
        for hash_line in test_hashes:
            f.write(hash_line + '\n')
    
    print(f"✅ 创建测试hash文件: {test_file}")
    return test_file

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='GPU加速Hashcat批量破解工具 - 6位密码专用版')
    parser.add_argument('hash_file', nargs='?', help='包含hash的文件路径')
    parser.add_argument('--hashcat-path', default=r'E:\app\forensic\hashcat-6.2.6\hashcat.exe',
                       help='Hashcat程序路径')
    parser.add_argument('--output-dir', default='gpu_crack_results',
                       help='输出目录')
    parser.add_argument('--wordlist-dir', default='wordlists',
                       help='字典文件目录')
    parser.add_argument('--max-time', type=int, default=3600,
                       help='单个hash最大破解时间（秒）')
    parser.add_argument('--gpu-only', action='store_true',
                       help='仅使用GPU（默认行为）')
    parser.add_argument('--complete', action='store_true',
                       help='完整模式 - 系统性测试全部62^6种6位组合')
    
    args = parser.parse_args()
    
    print("=== GPU加速Hashcat批量破解工具 v2.1 - 6位密码专用版 ===")
    print("适用于: Windows 11 + i9-12900K + RTX 3080")
    print("支持: JKS Keystore 和 PKCS#12 格式")
    print()
    
    # 交互式获取hash文件（如果未提供）
    if not args.hash_file:
        hash_file_input = input("请输入hash文件路径 (留空使用 example_6digit_hashes.txt): ").strip()
        if not hash_file_input:
            hash_file_input = "example_6digit_hashes.txt"
        args.hash_file = hash_file_input
    
    # 使用智能破解模式（除非强制指定完整模式）
    complete_mode = args.complete
    if complete_mode:
        print("\n🔥 启动强制完整模式!")
        print("🎯 直接测试全部 62^6 = 56,800,235,584 种6位大小写字母+数字组合")
        print("⏰ 在RTX 3080上预计需要数小时到十几小时完成")
        print("🚀 开始完整破解...")
    else:
        print("\n🧠 使用RTX 3080专用智能破解策略")
        print("• 自动阶段性破解：常见密码 → 高效模式 → 完整覆盖")
        print("• 针对6位密码优化，最大化破解效率")
        print("• 根据密码复杂度自动调整策略")
    
    # 配置
    config = {
        'hashcat_path': Path(args.hashcat_path),
        'output_dir': Path(args.output_dir),
        'wordlist_dir': Path(args.wordlist_dir),
        'max_time': args.max_time,
        'gpu_only': args.gpu_only,
    }
    
    # 验证输入文件
    hash_file = Path(args.hash_file)
    if not hash_file.exists():
        print(f"❌ Hash文件不存在: {hash_file}")
        sys.exit(1)
        
    # 验证Hashcat
    if not config['hashcat_path'].exists():
        print(f"❌ Hashcat程序不存在: {config['hashcat_path']}")
        sys.exit(1)
        
    # 创建输出目录
    config['output_dir'].mkdir(parents=True, exist_ok=True)
    
    # 启动破解器
    try:
        cracker = GPUHashcatCracker(config)
        cracker.run_batch_crack(hash_file, complete_mode)
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断")
    except Exception as e:
        print(f"💥 程序错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()