#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Keystore信息提取器
用于提取JKS/PKCS12文件的详细信息，包括别名、公钥MD5、证书信息等
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

