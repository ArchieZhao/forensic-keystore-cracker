# Forensic Keystore Cracker

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](https://www.microsoft.com/windows)

专业的密钥库密码恢复和证书分析工具，专注于数字取证场景下的 JKS/PKCS12 Keystore 破解与 Android APK 签名证书分析。

## ✨ 核心特性

- **🚀 GPU 加速破解**: 基于 Hashcat 的高性能密码破解（~10,000 H/s）
- **📦 批量处理**: 支持单文件和大规模目录批量破解（70+ 文件）
- **🔍 证书分析**: 自动提取公钥 MD5/SHA1 指纹、证书详细信息
- **💾 进度管理**: 断点续传、会话保存、结果导出（JSON/Excel）
- **🎯 多格式支持**: JKS、PKCS12 (.p12/.pfx)、Android Keystore

## 🎯 适用场景

- ✅ Android APK 签名证书密码恢复
- ✅ 数字取证调查中的证书分析
- ✅ 批量 keystore 密码破解
- ✅ 授权的安全测试和学术研究

⚠️ **法律声明**: 仅用于合法授权的场景，禁止用于非法破解他人证书。

## 🛠️ 快速开始

### 环境要求

- **Python**: 3.8+
- **Java**: JDK 8+（运行 JksPrivkPrepare.jar 和 keytool）
- **GPU**: NVIDIA 显卡（推荐 RTX 3080 或更高）
- **CUDA**: 兼容显卡的驱动程序
- **操作系统**: Windows 11（主要测试环境）

### 安装步骤

1. **克隆仓库**
```bash
git clone https://github.com/ArchieZhao/forensic-keystore-cracker.git
cd forensic-keystore-cracker
```

2. **安装 Python 依赖**
```bash
pip install -r requirements.txt
```

3. **下载必需工具**
   - [Hashcat 6.2.6](https://hashcat.net/hashcat/) - 解压到项目根目录的 `hashcat-6.2.6/` 文件夹
   - [John the Ripper 1.9.0](https://www.openwall.com/john/) - 解压到 `john-1.9.0/` 文件夹
   - JksPrivkPrepare.jar - 已包含在 `JKS-private-key-cracker-hashcat/` 目录中

4. **验证环境**
```bash
java -version
python cli_batch_crack.py --help
python extractor_jks_hash.py --help
```

## 📖 使用方法

### 1. 批量 Hash 提取

```bash
# 从默认 certificate 目录提取
python extractor_jks_hash.py -m ?a?a?a?a?a?a

# 从自定义目录提取
python extractor_jks_hash.py -d /path/to/keystores -m ?u?l?l?l?d?d

# 提取到指定输出文件
python extractor_jks_hash.py -m ?a?a?a?a?a?a -o my_hashes.txt
```

### 2. 批量破解

```bash
# 批量破解默认目录（certificate/）
python cli_batch_crack.py -m ?a?a?a?a?a?a

# 批量破解自定义目录
python cli_batch_crack.py -d /path/to/keystores -m ?u?l?l?l?d?d

# 指定输出目录
python cli_batch_crack.py -m ?a?a?a?a?a?a -o custom_output
```

### 3. GPU 破解

```bash
# 使用 GPU 破解 hash 文件
python cracker_hashcat_gpu.py hash.txt -m ?a?a?a?a?a?a

# 指定算法类型（JKS 私钥）
python cracker_hashcat_gpu.py hash.txt -m ?a?a?a?a?a?a -a jksprivk

# 启用优化和高性能模式
python cracker_hashcat_gpu.py hash.txt -m ?a?a?a?a?a?a -O -w 4
```

### 4. 证书信息提取

```bash
# 从已知密码的 keystore 提取证书和指纹
python extractor_certificate.py keystore.jks password123

# 提取指定别名
python extractor_certificate.py keystore.jks password123 -a mykey

# 指定输出目录
python extractor_certificate.py keystore.jks password123 -o certificates
```

### 5. Keystore 信息提取

```bash
# 提取 keystore 详细信息（别名、证书、指纹）
python extractor_keystore_info.py keystore.jks password123
```

## 🔐 常用密码掩码

| 掩码 | 描述 | 适用场景 |
|------|------|---------|
| `?a?a?a?a?a?a` | 6位任意字符 | 默认，最全面 |
| `?u?l?l?l?d?d` | 1大写+3小写+2数字 | 常见Android模式 |
| `?l?l?l?l?l?l` | 6位小写字母 | 简单密码 |
| `?d?d?d?d?d?d` | 6位数字 | 纯数字密码 |

更多掩码语法参考 [Hashcat Mask Attack 文档](https://hashcat.net/wiki/doku.php?id=mask_attack)。

## 🏗️ 架构设计

```
用户输入 → 批量破解工具
    ↓
    ├─→ extractor_jks_hash.py
    │    → 扫描目录下所有 keystore 文件
    │    → JksPrivkPrepare.jar (提取 $jksprivk$ 格式 hash)
    │    → 生成统一的 hash 文件
    │
    ├─→ cracker_hashcat_gpu.py
    │    → hashcat.exe -m 15500 (GPU 加速破解)
    │    → 实时监控破解进度
    │    → 返回破解结果
    │
    ├─→ cli_batch_crack.py
    │    → 整合 hash 提取 + GPU 破解 + 结果分析
    │    → 批量处理完整流程
    │    → 导出详细报告
    │
    └─→ 结果处理:
         ├─→ extractor_keystore_info.py (提取证书详细信息)
         ├─→ extractor_certificate.py (导出证书文件和指纹)
         ├─→ manager_crack_progress.py (进度管理和结果导出)
         └─→ analyzer_crack_result.py (批量结果分析)
```

### 核心模块

| 模块 | 功能 |
|------|------|
| `extractor_jks_hash.py` | 批量提取 keystore hash |
| `cli_batch_crack.py` | 终极批量破解器（完整流程） |
| `cracker_hashcat_gpu.py` | GPU 破解引擎 |
| `extractor_certificate.py` | 证书提取和指纹计算 |
| `extractor_keystore_info.py` | Keystore 信息提取器 |
| `manager_crack_progress.py` | 进度管理和结果导出 |
| `analyzer_crack_result.py` | 批量结果分析器 |
| `monitor_gpu_performance.py` | GPU 状态监控 |

## 📊 性能对比

| 破解模式 | 工具组合 | 性能 | 适用场景 |
|---------|---------|------|---------|
| JKS 私钥密码 | JksPrivkPrepare + Hashcat GPU | ~10,000 H/s | Android APK 签名破解 ⭐ |
| 批量破解 (70+ 文件) | ultimate_batch_cracker | 并行处理 | 大规模取证分析 ⭐ |

## 🔍 项目结构

```
forensic-keystore-cracker/
├── extractor_jks_hash.py          # 批量hash提取器
├── cli_batch_crack.py        # 终极批量破解器（完整流程）
├── cracker_hashcat_gpu.py           # GPU Hashcat破解引擎
├── extractor_certificate.py         # 证书提取和指纹计算
├── extractor_keystore_info.py       # Keystore信息提取器
├── manager_crack_progress.py              # 进度管理和结果导出
├── analyzer_crack_result.py         # 批量结果分析器
├── monitor_gpu_performance.py                   # GPU状态监控
├── requirements.txt                 # Python依赖
├── README.md                        # 项目说明文档
├── CLAUDE.md                        # 开发指南和架构文档
│
├── hashcat-6.2.6/                   # Hashcat工具（需下载）
│   ├── hashcat.exe                  # 主程序
│   └── OpenCL/                      # GPU计算内核
│
├── john-1.9.0/                      # John the Ripper（需下载）
│   └── run/keystore2john.py         # Keystore hash提取脚本
│
├── JKS-private-key-cracker-hashcat/
│   └── JksPrivkPrepare.jar          # ⭐关键工具：JKS hash提取
│
├── certificate/                     # 输入：待破解的keystore文件
│   └── [UUID]/                      # 使用UUID文件夹名作为唯一标识
│
├── batch_crack_output/              # 输出：批量破解结果
└── testandold/                      # 测试文件和旧版本代码
```

## 🧪 测试验证

```bash
# 验证 Java 环境
java -version

# 验证 keytool
keytool -help

# 检查 GPU 状态
nvidia-smi

# 手动提取 JKS hash
java -jar JKS-private-key-cracker-hashcat/JksPrivkPrepare.jar test.keystore

# 手动运行 Hashcat
cd hashcat-6.2.6
./hashcat.exe -m 15500 ../hash.txt -a 3 ?a?a?a?a?a?a --force
```

## 🔧 性能优化

### GPU 优化参数

```bash
# 启用优化内核（适用于短密码）
-O

# 调整工作负载（1-4，4为最高）
-w 4

# 调整 GPU 温度保护
--gpu-temp-abort=90

# 使用多 GPU
-d 1,2,3,4
```

## 🐛 常见问题

### "No hashes loaded" 错误
- **原因**: Hash 格式不兼容
- **解决**: 确保使用 JksPrivkPrepare.jar 生成 `$jksprivk$` 格式，而非 keystore2john

### "Separator unmatched" 错误
- **原因**: 混用了不同工具的 hash 格式
- **解决**: JKS 私钥破解必须使用 JksPrivkPrepare.jar

### GPU 性能低
- **解决**: 检查 CUDA 驱动，使用 `-w 4` 和 `-O` 参数优化

### Java 环境问题
- **解决**: 确保 `java` 和 `keytool` 命令在系统 PATH 中

## 📚 深入了解

查看 [CLAUDE.md](CLAUDE.md) 获取完整的：
- 详细架构设计
- 开发指南
- 关键技术要点
- 工作流程示例

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

## ⚠️ 安全和法律声明

**合法使用**：
- ✅ 仅用于自己拥有的证书
- ✅ 授权的密码恢复任务
- ✅ 学术研究和安全测试
- ❌ 禁止用于非法破解他人证书

**数据保护**：
- 破解完成后及时清理临时 hash 文件
- 安全存储破解结果
- 避免在网络上传输明文密码

## 🙏 致谢

- [Hashcat](https://hashcat.net/) - 高性能密码破解工具
- [John the Ripper](https://www.openwall.com/john/) - 经典密码破解工具
- [JKS-private-key-cracker-hashcat](https://github.com/floyd-fuh/JKS-private-key-cracker-hashcat) - JKS hash 提取工具

---

**⭐ 如果这个项目对您有帮助，请给个 Star！**
