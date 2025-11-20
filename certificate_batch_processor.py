#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
证书批量处理工具
扫描certificate目录下的所有apk.keystore文件，提取hash并准备进行破解
"""

import os
import sys
import subprocess
from pathlib import Path
import json
import hashlib
from datetime import datetime

class CertificateBatchProcessor:
    def __init__(self, certificate_dir="certificate", output_dir="analysis_results"):
        self.certificate_dir = Path(certificate_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 工具路径
        self.keystore2john_path = self._find_keystore2john()
        self.hashcat_path = self._find_hashcat()
        
        # 结果统计
        self.stats = {
            'total_certificates': 0,
            'processed': 0,
            'hash_extracted': 0,
            'failed': 0,
            'certificates': {}
        }
        
    def _find_keystore2john(self):
        """智能查找keystore2john工具"""
        possible_paths = [
            Path("john/run/keystore2john.py"),
            Path("john-1.9.0/run/keystore2john.py"), 
            Path(r"C:\tools\john\run\keystore2john.py"),
            Path("./keystore2john.py")
        ]
        
        for path in possible_paths:
            if path.exists():
                print(f"✅ 找到 keystore2john: {path}")
                return path
        
        print("❌ 未找到 keystore2john 工具，请检查 John the Ripper 安装")
        return None

    def _find_hashcat(self):
        """智能查找hashcat工具"""
        possible_paths = [
            Path("hashcat-6.2.6/hashcat.exe"),
            Path(r"C:\tools\hashcat\hashcat.exe"),
            Path("./hashcat.exe")
        ]
        
        for path in possible_paths:
            if path.exists():
                print(f"✅ 找到 hashcat: {path}")
                return path
        
        print("❌ 未找到 hashcat 工具")
        return None
        
    def scan_certificates(self):
        """扫描证书目录，发现所有apk.keystore文件"""
        print("🔍 扫描证书目录...")
        print(f"📁 证书目录: {self.certificate_dir}")
        
        certificates = []
        
        if not self.certificate_dir.exists():
            print(f"❌ 证书目录不存在: {self.certificate_dir}")
            return certificates
            
        # 扫描所有子目录中的apk.keystore文件
        for cert_dir in self.certificate_dir.iterdir():
            if cert_dir.is_dir():
                keystore_file = cert_dir / "apk.keystore"
                if keystore_file.exists():
                    certificates.append({
                        'id': cert_dir.name,
                        'path': keystore_file,
                        'size': keystore_file.stat().st_size,
                        'dir': cert_dir
                    })
                    
        self.stats['total_certificates'] = len(certificates)
        print(f"✅ 发现 {len(certificates)} 个证书文件")
        
        for cert in certificates:
            print(f"  📄 {cert['id']}: {cert['path']} ({cert['size']} bytes)")
            
        return certificates
        
    def extract_hash_from_keystore(self, keystore_path, cert_id):
        """从keystore文件提取hash"""
        try:
            print(f"\n🔧 处理证书: {cert_id}")
            
            # 检查keystore2john工具
            if not self.keystore2john_path:
                print(f"❌ keystore2john工具不存在: {self.keystore2john_path}")
                return None
                
            # 执行keystore2john提取hash
            cmd = ["python", str(self.keystore2john_path), str(keystore_path)]
            print(f"🔍 执行命令: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ keystore2john执行失败:")
                print(f"   stderr: {result.stderr}")
                return None
                
            hash_line = result.stdout.strip()
            if not hash_line:
                print("❌ 未提取到hash")
                return None
                
            print(f"✅ 成功提取hash: {hash_line[:50]}...")
            return hash_line
            
        except Exception as e:
            print(f"❌ 提取hash时出错: {e}")
            return None
            
    def create_batch_hash_file(self, certificates):
        """创建批量hash文件供hashcat破解"""
        hash_file = self.output_dir / "certificates_batch.hash"
        valid_hashes = []
        
        print(f"\n📝 创建批量hash文件: {hash_file}")
        
        with open(hash_file, 'w', encoding='utf-8') as f:
            for cert in certificates:
                self.stats['processed'] += 1
                
                # 提取hash
                hash_line = self.extract_hash_from_keystore(cert['path'], cert['id'])
                
                if hash_line:
                    # 使用证书ID作为标识符
                    hash_entry = f"{cert['id']}:{hash_line}"
                    f.write(hash_entry + '\n')
                    valid_hashes.append(hash_entry)
                    
                    # 记录到统计信息
                    self.stats['hash_extracted'] += 1
                    self.stats['certificates'][cert['id']] = {
                        'path': str(cert['path']),
                        'size': cert['size'],
                        'hash_extracted': True,
                        'hash_preview': hash_line[:50] + '...'
                    }
                else:
                    self.stats['failed'] += 1
                    self.stats['certificates'][cert['id']] = {
                        'path': str(cert['path']),
                        'size': cert['size'],
                        'hash_extracted': False,
                        'error': 'Failed to extract hash'
                    }
                    
        print(f"✅ 批量hash文件创建完成")
        print(f"📊 有效hash数量: {len(valid_hashes)}")
        
        return hash_file, valid_hashes
        
    def create_md5_test_file(self):
        """创建MD5测试文件用于验证破解逻辑"""
        md5_file = self.output_dir / "test_certificates_md5.hash"
        
        # 生成一些6位测试密码的MD5
        test_passwords = [
            '123456', 'admin1', 'qwerty', 'abc123', 'test01',
            'user01', 'pass01', '111111', 'admin0', '123abc'
        ]
        
        print(f"\n🧪 创建MD5测试文件: {md5_file}")
        
        with open(md5_file, 'w', encoding='utf-8') as f:
            for i, password in enumerate(test_passwords, 1):
                md5_hash = hashlib.md5(password.encode()).hexdigest()
                f.write(f"{md5_hash}\n")
                print(f"  {i:2d}. {password} -> {md5_hash}")
                
        print(f"✅ MD5测试文件创建完成，包含 {len(test_passwords)} 个6位密码")
        return md5_file
        
    def generate_report(self):
        """生成处理报告"""
        report_file = self.output_dir / f"certificate_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'certificate_directory': str(self.certificate_dir),
            'output_directory': str(self.output_dir),
            'statistics': self.stats,
            'summary': {
                'total_found': self.stats['total_certificates'],
                'successfully_processed': self.stats['hash_extracted'],
                'failed': self.stats['failed'],
                'success_rate': f"{(self.stats['hash_extracted'] / max(self.stats['total_certificates'], 1) * 100):.1f}%"
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        print(f"\n📊 处理报告已保存: {report_file}")
        
        # 打印摘要
        print("\n" + "="*60)
        print("📊 证书处理统计")
        print("="*60)
        print(f"发现证书数量: {self.stats['total_certificates']}")
        print(f"成功处理: {self.stats['hash_extracted']}")
        print(f"处理失败: {self.stats['failed']}")
        print(f"成功率: {(self.stats['hash_extracted'] / max(self.stats['total_certificates'], 1) * 100):.1f}%")
        
        return report_file
        
    def process_directory(self, certificate_dir):
        """处理指定的证书目录 - 兼容main.py调用"""
        # 更新证书目录
        self.certificate_dir = Path(certificate_dir)
        
        # 执行完整处理流程
        success = self.run()
        
        # 返回与main.py期望的格式兼容的结果
        return {
            "success": success,
            "total_processed": self.stats.get('total_certificates', 0),
            "hash_extracted": self.stats.get('hash_extracted', 0),
            "failed": self.stats.get('failed', 0),
            "error": None if success else "Processing failed"
        }
        
    def run(self):
        """运行批量处理"""
        print("="*60)
        print("🚀 证书批量处理工具")
        print("="*60)
        
        # 1. 扫描证书
        certificates = self.scan_certificates()
        if not certificates:
            print("❌ 未找到任何证书文件")
            return False
            
        # 2. 提取hash并创建批量文件
        hash_file, valid_hashes = self.create_batch_hash_file(certificates)
        
        # 3. 创建MD5测试文件
        md5_test_file = self.create_md5_test_file()
        
        # 4. 生成报告
        report_file = self.generate_report()
        
        print(f"\n🎯 推荐下一步操作:")
        print(f"1. 📝 使用MD5测试文件验证破解逻辑: {md5_test_file}")
        print(f"2. 🔐 使用批量hash文件进行实际破解: {hash_file}")
        print(f"3. 📊 查看详细报告: {report_file}")
        
        print(f"\n💡 GPU破解命令示例:")
        print(f"   python gpu_hashcat_cracker.py {md5_test_file} --complete")
        print(f"   python gpu_hashcat_cracker.py {hash_file} --complete")
        
        return True

def main():
    processor = CertificateBatchProcessor()
    processor.run()

if __name__ == "__main__":
    main() 