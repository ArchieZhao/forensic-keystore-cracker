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
python main.py --help
```

## 📖 使用方法

### 1. 交互式模式（推荐新手）

```bash
python main.py
```

程序会引导您完成：
- 模式选择（单文件/批量）
- 文件选择
- 掩码配置
- 实时进度监控

### 2. 单文件私钥密码破解

```bash
python jks_privkey_processor.py target.keystore -m ?a?a?a?a?a?a
```

使用 JksPrivkPrepare.jar + Hashcat (mode 15500) 进行 GPU 加速破解。

### 3. 批量破解

```bash
# 批量破解整个目录
python jks_privkey_processor.py certificate_folder -m ?u?l?l?l?d?d

# 终极批量破解（70+ 文件）
python ultimate_batch_cracker.py certificate_folder -m ?a?a?a?a?a?a
```

### 4. 证书信息提取

```bash
# 从已知密码的 keystore 提取证书和指纹
python certificate_extractor.py keystore.jks password123

# 提取指定别名
python certificate_extractor.py keystore.jks password123 -a mykey

# 指定输出目录
python certificate_extractor.py keystore.jks password123 -o certificates
```

### 5. 结果管理

```bash
# 导出破解结果为 JSON 和 Excel
python main.py --export SESSION_ID

# 仅导出 JSON 文件
python main.py --export SESSION_ID --json-only

# 查看所有会话
python main.py --list-sessions
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
用户输入 → main.py
    ↓
    ├─→ 交互式模式：引导式 UI
    └─→ 命令行模式
         ↓
         ├─→ 私钥破解（推荐）:
         │    jks_privkey_processor.py
         │      → JksPrivkPrepare.jar (提取 $jksprivk$ 格式 hash)
         │      → gpu_hashcat_cracker.py
         │          → hashcat.exe -m 15500 (GPU 加速破解)
         │      → keystore_info_extractor.py (提取证书信息)
         │
         └─→ 容器密码路径:
              certificate_batch_processor.py
                → john/keystore2john.py (提取 $keystore$ 格式)
                → john.exe (CPU 破解)
```

### 核心模块

| 模块 | 功能 |
|------|------|
| `main.py` | 主程序入口，会话管理 |
| `jks_privkey_processor.py` | JKS 私钥破解器（核心） |
| `gpu_hashcat_cracker.py` | GPU 破解引擎 |
| `certificate_extractor.py` | 证书提取和指纹计算 |
| `keystore_info_extractor.py` | Keystore 信息提取器 |
| `progress_manager.py` | 进度管理和结果导出 |

## 📊 性能对比

| 破解模式 | 工具组合 | 性能 | 适用场景 |
|---------|---------|------|---------|
| 私钥密码 | JksPrivkPrepare + Hashcat | ~10,000 H/s | Android APK 签名 ⭐ |
| 容器密码 | keystore2john + John | ~500 H/s | 完整 keystore 访问 |

## 🔍 项目结构

```
forensic-keystore-cracker/
├── main.py                          # 主程序入口
├── jks_privkey_processor.py         # JKS私钥密码破解器
├── gpu_hashcat_cracker.py           # GPU Hashcat破解引擎
├── certificate_extractor.py         # 证书提取工具
├── keystore_info_extractor.py       # Keystore信息提取器
├── progress_manager.py              # 进度管理
├── ultimate_batch_cracker.py        # 终极批量破解器
├── requirements.txt                 # Python依赖
├── CLAUDE.md                        # 项目详细文档
│
├── hashcat-6.2.6/                   # Hashcat工具（需下载）
├── john-1.9.0/                      # John the Ripper（需下载）
├── JKS-private-key-cracker-hashcat/
│   └── JksPrivkPrepare.jar          # JKS hash提取工具
│
└── certificate/                     # 输入：待破解的keystore文件
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
