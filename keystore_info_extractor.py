#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Keystore信息提取器

使用keytool命令行工具从JKS/PKCS12 keystore中提取证书信息，
包括别名列表、Subject/Issuer、有效期、公钥MD5/SHA1哈希值，
支持JKS和PKCS12格式自动回退，返回结构化KeystoreInfo数据类。

Architecture:
    keytool查找 → 别名获取 → 证书导出 → 信息解析 → 哈希计算 → 结构化返回

    KeystoreInfoExtractor (keystore_info_extractor.py:54)
        ├─ __init__() (L57): 查找keytool工具（7个常见路径）+ 初始化临时目录
        ├─ _find_keytool() (L61): glob匹配Java安装路径，测试keytool -help
        ├─ extract_keystore_info() (L95): 主提取流程，返回KeystoreInfo对象
        ├─ _get_aliases() (L137): keytool -list解析别名列表（正则匹配PrivateKeyEntry）
        ├─ _get_certificate_info() (L178): keytool -list -v提取Subject/Issuer/Valid等
        ├─ _calculate_public_key_md5() (L234): 导出证书 → hashlib.md5 → 大写无冒号
        ├─ _calculate_public_key_sha1() (L280): 导出证书 → hashlib.sha1 → 大写无冒号
        ├─ extract_simple_info() (L326): 简化接口返回4元组（alias, MD5, SHA1, type）
        └─ batch_extract_info() (L337): 批量处理多个keystore文件

    KeystoreInfo (dataclass, keystore_info_extractor.py:22)
        ├─ 12个字段：file_path, aliases, primary_alias, keystore_type,
        │            public_key_md5, public_key_sha1, certificate_info,
        │            subject, issuer, valid_from, valid_to, signature_algorithm
        └─ to_dict() (L38): 转换为字典便于JSON序列化

Features:
    - keytool自动查找：7个常见Java安装路径 + glob通配符 (keystore_info_extractor.py:64-80)
    - JKS/PKCS12回退：先尝试JKS，失败后自动尝试PKCS12 (keystore_info_extractor.py:150-157, 193-199)
    - 正则解析别名：匹配PrivateKeyEntry/trustedCertEntry/SecretKeyEntry (keystore_info_extractor.py:164)
    - 6项证书信息：Subject, Issuer, ValidFrom, ValidTo, Signature, SerialNumber (keystore_info_extractor.py:212-226)
    - 双哈希计算：MD5和SHA1公钥指纹（大写无冒号格式）(keystore_info_extractor.py:266, 312)
    - 临时文件管理：导出证书到temp目录，计算后自动清理 (keystore_info_extractor.py:238, 270)
    - dataclass结构：12个字段 + to_dict()方法 (keystore_info_extractor.py:22-52)

Args (方法参数):
    extract_keystore_info(keystore_path: str, password: str) -> Optional[KeystoreInfo]:
        从keystore提取完整信息，返回KeystoreInfo对象

    extract_simple_info(keystore_path: str, password: str) -> Tuple[str, str, str, str]:
        简化接口，返回4元组：(alias, public_key_md5, public_key_sha1, keystore_type)

    batch_extract_info(keystore_files: List[str], passwords: Dict[str, str]) -> Dict[str, KeystoreInfo]:
        批量提取多个keystore信息

        示例：
        extractor = KeystoreInfoExtractor()

        # 单文件提取
        info = extractor.extract_keystore_info("keystore.jks", "password123")
        print(f"Alias: {info.primary_alias}, MD5: {info.public_key_md5}")

        # 简化提取
        alias, md5, sha1, ktype = extractor.extract_simple_info("keystore.jks", "password123")

        # 批量提取
        files = ["cert1.jks", "cert2.jks"]
        passwords = {"cert1.jks": "pass1", "cert2.jks": "pass2"}
        results = extractor.batch_extract_info(files, passwords)

Returns (返回值):
    KeystoreInfo对象（12个字段）:
        file_path (str): keystore文件路径
        aliases (List[str]): 所有别名列表
        primary_alias (str): 第一个别名（主别名）
        keystore_type (str): "JKS" or "PKCS12"
        public_key_md5 (str): 公钥MD5哈希（大写无冒号，如"A1B2C3D4..."）
        public_key_sha1 (str): 公钥SHA1哈希（大写无冒号）
        certificate_info (Dict): 原始证书信息字典
        subject (str): 证书Subject（Owner）
        issuer (str): 证书Issuer
        valid_from (str): 有效期开始
        valid_to (str): 有效期结束
        signature_algorithm (str): 签名算法

Requirements:
    - Java JDK 8+ (keytool命令必需)
    - rich (终端输出Console)
    - Python标准库: subprocess, hashlib, re, json, tempfile, pathlib, dataclasses

Technical Notes:
    keytool查找策略:
        7个路径: keytool, java/bin/keytool, jdk/bin/keytool,
                C:\Program Files\Java\jdk*\bin\keytool.exe,
                C:\Program Files\Eclipse Adoptium\jdk*\bin\keytool.exe,
                C:\Program Files\OpenJDK\jdk*\bin\keytool.exe (keystore_info_extractor.py:64-71)
        glob匹配: 处理jdk*通配符路径 (keystore_info_extractor.py:75-80)
        测试方法: keytool -help检查returncode或stderr含"keytool" (keystore_info_extractor.py:82-88)

    JKS/PKCS12格式回退:
        初始尝试: -storetype JKS (keystore_info_extractor.py:145)
        失败回退: -storetype PKCS12 (keystore_info_extractor.py:152-153)
        类型识别: 根据成功的storetype设置keystore_type (keystore_info_extractor.py:206-209)

    别名解析正则:
        模式: ^([^,\s]+),\s+\d+.*(?:PrivateKeyEntry|trustedCertEntry|SecretKeyEntry)
        匹配: "mykey, 2024-01-01, PrivateKeyEntry" → 提取"mykey" (keystore_info_extractor.py:164, 168-170)

    证书信息正则解析:
        6个字段模式 (keystore_info_extractor.py:212-219):
            subject: "Owner:\s*(.+?)(?:\n|$)"
            issuer: "Issuer:\s*(.+?)(?:\n|$)"
            valid_from: "Valid from:\s*(.+?)\s+until:"
            valid_to: "until:\s*(.+?)(?:\n|$)"
            signature_algorithm: "Signature algorithm name:\s*(.+?)(?:\n|$)"
            serial_number: "Serial number:\s*(.+?)(?:\n|$)"

    公钥哈希计算流程:
        1. keytool -export导出证书到临时文件 (keystore_info_extractor.py:240-250)
        2. 读取证书二进制数据 (keystore_info_extractor.py:262-263)
        3. hashlib.md5()/sha1()计算哈希 (keystore_info_extractor.py:266, 312)
        4. hexdigest().upper()转大写无冒号格式 (keystore_info_extractor.py:266, 312)
        5. 删除临时文件temp_cert.unlink() (keystore_info_extractor.py:270, 316)

    临时文件命名:
        MD5: temp_cert_{pid}.crt (keystore_info_extractor.py:238)
        SHA1: temp_cert_sha1_{pid}.crt (keystore_info_extractor.py:284)
        目录: tempfile.gettempdir() (keystore_info_extractor.py:59)

    超时控制:
        所有keytool命令设置30秒超时 (keystore_info_extractor.py:148, 191, 250, 296)

Workflow:
    1. 初始化时查找keytool工具（7个常见路径）
    2. 调用extract_keystore_info(keystore_path, password)
    3. 使用keytool -list获取别名列表（JKS → PKCS12回退）
    4. 选择第一个别名作为primary_alias
    5. 使用keytool -list -v提取证书详细信息（6个正则解析）
    6. 导出证书到临时文件（keytool -export）
    7. 读取证书二进制数据
    8. 计算MD5和SHA1哈希（hashlib）
    9. 删除临时文件
    10. 构建KeystoreInfo对象（12个字段）
    11. 返回结构化数据

Author: Forensic Keystore Cracker Project
Version: 1.0.0
License: 仅用于授权的数字取证和安全研究
"""

import os
import sys
import subprocess
import hashlib
import re
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from rich.console import Console

console = Console()

@dataclass
class KeystoreInfo:
    """Keystore信息结构"""
    file_path: str
    aliases: List[str]
    primary_alias: str
    keystore_type: str
    public_key_md5: str
    public_key_sha1: str
    certificate_info: Dict[str, Any]
    subject: str
    issuer: str
    valid_from: str
    valid_to: str
    signature_algorithm: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "aliases": self.aliases,
            "primary_alias": self.primary_alias,
            "keystore_type": self.keystore_type,
            "public_key_md5": self.public_key_md5,
            "public_key_sha1": self.public_key_sha1,
            "certificate_info": self.certificate_info,
            "subject": self.subject,
            "issuer": self.issuer,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "signature_algorithm": self.signature_algorithm
        }

class KeystoreInfoExtractor:
    """Keystore信息提取器"""
    
    def __init__(self):
        self.keytool_path = self._find_keytool()
        self.temp_dir = Path(tempfile.gettempdir())
        
    def _find_keytool(self) -> Optional[str]:
        """查找keytool工具"""
        # 常见的keytool路径
        possible_paths = [
            "keytool",  # 系统PATH中
            "java/bin/keytool",
            "jdk/bin/keytool",
            r"C:\Program Files\Java\jdk*\bin\keytool.exe",
            r"C:\Program Files\Eclipse Adoptium\jdk*\bin\keytool.exe",
            r"C:\Program Files\OpenJDK\jdk*\bin\keytool.exe"
        ]
        
        for path in possible_paths:
            try:
                if "*" in path:
                    # 处理通配符路径
                    import glob
                    matches = glob.glob(path)
                    if matches:
                        path = matches[0]
                
                result = subprocess.run([path, "-help"], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=5)
                if result.returncode == 0 or "keytool" in result.stderr.lower():
                    console.print(f"[green]✅ 找到keytool: {path}[/green]")
                    return path
            except:
                continue
        
        console.print("[yellow]⚠️ 未找到keytool工具，某些功能可能无法使用[/yellow]")
        return None
    
    def extract_keystore_info(self, keystore_path: str, password: str) -> Optional[KeystoreInfo]:
        """提取keystore完整信息"""
        if not self.keytool_path:
            console.print("[yellow]⚠️ keytool不可用，跳过信息提取[/yellow]")
            return None
            
        try:
            # 首先获取别名列表
            aliases = self._get_aliases(keystore_path, password)
            if not aliases:
                return None
            
            primary_alias = aliases[0]  # 使用第一个别名作为主别名
            
            # 获取证书详细信息
            cert_info = self._get_certificate_info(keystore_path, password, primary_alias)
            if not cert_info:
                return None
            
            # 计算公钥MD5和SHA1
            public_key_md5 = self._calculate_public_key_md5(keystore_path, password, primary_alias)
            public_key_sha1 = self._calculate_public_key_sha1(keystore_path, password, primary_alias)
            
            return KeystoreInfo(
                file_path=keystore_path,
                aliases=aliases,
                primary_alias=primary_alias,
                keystore_type=cert_info.get("keystore_type", "JKS"),
                public_key_md5=public_key_md5 or "计算失败",
                public_key_sha1=public_key_sha1 or "计算失败",
                certificate_info=cert_info,
                subject=cert_info.get("subject", "未知"),
                issuer=cert_info.get("issuer", "未知"),
                valid_from=cert_info.get("valid_from", "未知"),
                valid_to=cert_info.get("valid_to", "未知"),
                signature_algorithm=cert_info.get("signature_algorithm", "未知")
            )
            
        except Exception as e:
            console.print(f"[red]❌ 提取keystore信息失败: {e}[/red]")
            return None
    
    def _get_aliases(self, keystore_path: str, password: str) -> List[str]:
        """获取keystore中的所有别名"""
        try:
            cmd = [
                self.keytool_path,
                "-list",
                "-keystore", keystore_path,
                "-storepass", password,
                "-storetype", "JKS"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # 尝试PKCS12格式
                cmd[-1] = "PKCS12"
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    console.print(f"[red]❌ 无法列出keystore别名[/red]")
                    return []
            
            # 解析别名
            aliases = []
            output = result.stdout
            
            # 匹配别名行（通常格式：alias_name, date, PrivateKeyEntry 或 trustedCertEntry）
            alias_pattern = r'^([^,\s]+),\s+\d+.*(?:PrivateKeyEntry|trustedCertEntry|SecretKeyEntry)'
            
            for line in output.split('\n'):
                line = line.strip()
                match = re.match(alias_pattern, line, re.IGNORECASE)
                if match:
                    aliases.append(match.group(1))
            
            return aliases
            
        except Exception as e:
            console.print(f"[red]❌ 获取别名失败: {e}[/red]")
            return []
    
    def _get_certificate_info(self, keystore_path: str, password: str, alias: str) -> Optional[Dict[str, Any]]:
        """获取证书详细信息"""
        try:
            cmd = [
                self.keytool_path,
                "-list",
                "-v",
                "-keystore", keystore_path,
                "-storepass", password,
                "-alias", alias,
                "-storetype", "JKS"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # 尝试PKCS12格式
                cmd[-1] = "PKCS12"
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    return None
            
            # 解析证书信息
            output = result.stdout
            cert_info = {}
            
            # 提取keystore类型
            if "PKCS12" in cmd:
                cert_info["keystore_type"] = "PKCS12"
            else:
                cert_info["keystore_type"] = "JKS"
            
            # 解析各种信息
            patterns = {
                "subject": r"Owner:\s*(.+?)(?:\n|$)",
                "issuer": r"Issuer:\s*(.+?)(?:\n|$)",
                "valid_from": r"Valid from:\s*(.+?)\s+until:",
                "valid_to": r"until:\s*(.+?)(?:\n|$)",
                "signature_algorithm": r"Signature algorithm name:\s*(.+?)(?:\n|$)",
                "serial_number": r"Serial number:\s*(.+?)(?:\n|$)"
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
                if match:
                    cert_info[key] = match.group(1).strip()
                else:
                    cert_info[key] = "未知"
            
            return cert_info
            
        except Exception as e:
            console.print(f"[red]❌ 获取证书信息失败: {e}[/red]")
            return None
    
    def _calculate_public_key_md5(self, keystore_path: str, password: str, alias: str) -> Optional[str]:
        """计算公钥的MD5值"""
        try:
            # 导出证书到临时文件
            temp_cert = self.temp_dir / f"temp_cert_{os.getpid()}.crt"
            
            export_cmd = [
                self.keytool_path,
                "-export",
                "-keystore", keystore_path,
                "-storepass", password,
                "-alias", alias,
                "-file", str(temp_cert),
                "-storetype", "JKS"
            ]
            
            result = subprocess.run(export_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # 尝试PKCS12格式
                export_cmd[-1] = "PKCS12"
                result = subprocess.run(export_cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    return None
            
            # 读取证书文件并计算MD5
            if temp_cert.exists():
                with open(temp_cert, 'rb') as f:
                    cert_data = f.read()
                
                # 计算MD5
                md5_hash = hashlib.md5(cert_data).hexdigest().upper()
                
                # 返回无冒号分割的大写格式
                # 清理临时文件
                temp_cert.unlink()
                
                return md5_hash
            
            return None
            
        except Exception as e:
            console.print(f"[red]❌ 计算公钥MD5失败: {e}[/red]")
            return None
    
    def _calculate_public_key_sha1(self, keystore_path: str, password: str, alias: str) -> Optional[str]:
        """计算公钥的SHA1值"""
        try:
            # 导出证书到临时文件
            temp_cert = self.temp_dir / f"temp_cert_sha1_{os.getpid()}.crt"
            
            export_cmd = [
                self.keytool_path,
                "-export",
                "-keystore", keystore_path,
                "-storepass", password,
                "-alias", alias,
                "-file", str(temp_cert),
                "-storetype", "JKS"
            ]
            
            result = subprocess.run(export_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # 尝试PKCS12格式
                export_cmd[-1] = "PKCS12"
                result = subprocess.run(export_cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    return None
            
            # 读取证书文件并计算SHA1
            if temp_cert.exists():
                with open(temp_cert, 'rb') as f:
                    cert_data = f.read()
                
                # 计算SHA1
                sha1_hash = hashlib.sha1(cert_data).hexdigest().upper()
                
                # 返回无冒号分割的大写格式
                # 清理临时文件
                temp_cert.unlink()
                
                return sha1_hash
            
            return None
            
        except Exception as e:
            console.print(f"[red]❌ 计算公钥SHA1失败: {e}[/red]")
            return None
    
    def extract_simple_info(self, keystore_path: str, password: str) -> Tuple[str, str, str, str]:
        """简化信息提取，返回别名、公钥MD5、公钥SHA1、keystore类型"""
        try:
            info = self.extract_keystore_info(keystore_path, password)
            if info:
                return info.primary_alias, info.public_key_md5, info.public_key_sha1, info.keystore_type
            else:
                return "未知", "提取失败", "提取失败", "JKS"
        except:
            return "未知", "提取失败", "提取失败", "JKS"
    
    def batch_extract_info(self, keystore_files: List[str], passwords: Dict[str, str]) -> Dict[str, KeystoreInfo]:
        """批量提取keystore信息"""
        results = {}
        
        for keystore_file in keystore_files:
            password = passwords.get(keystore_file)
            if not password:
                console.print(f"[yellow]⚠️ 没有密码，跳过: {keystore_file}[/yellow]")
                continue
            
            console.print(f"[cyan]📋 提取信息: {Path(keystore_file).name}[/cyan]")
            
            info = self.extract_keystore_info(keystore_file, password)
            if info:
                results[keystore_file] = info
                console.print(f"[green]✅ 信息提取成功[/green]")
            else:
                console.print(f"[red]❌ 信息提取失败[/red]")
        
        return results 

