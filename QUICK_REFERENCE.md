# 快速参考指南

## 🚀 三种使用模式速查表（v2.1+）

### 模式对比

| 模式 | 命令示例 | 何时使用 |
|------|---------|---------|
| **根目录批量** | `python cli_batch_crack.py certificate` | 批量处理多个证书 |
| **UUID子目录** ✨ | `python cli_batch_crack.py certificate/uuid123` | 处理特定UUID目录 |
| **单文件** ✨ | `python cli_batch_crack.py certificate/uuid123/app.jks` | 快速破解单个文件 |

---

## 📖 常用命令速查

### 批量破解（推荐）

```bash
# 默认批量破解
python cli_batch_crack.py

# 指定目录批量破解
python cli_batch_crack.py certificate

# UUID子目录模式（新增）
python cli_batch_crack.py certificate/00a2c44cdfd14d45addb4104acf3fe0c

# 单文件模式（新增）
python cli_batch_crack.py certificate/00a2c44cdfd14d45addb4104acf3fe0c/apk.keystore
```

### Hash提取

```bash
# 根目录批量提取
python extractor_jks_hash.py certificate

# UUID目录提取
python extractor_jks_hash.py certificate/uuid123

# 单文件提取
python extractor_jks_hash.py certificate/uuid123/apk.keystore
```

### GPU破解

```bash
# 基本破解
python cracker_hashcat_gpu.py hash.txt -m ?a?a?a?a?a?a

# 优化模式
python cracker_hashcat_gpu.py hash.txt -m ?a?a?a?a?a?a -O -w 4
```

### 证书提取

```bash
# 提取证书和指纹
python extractor_certificate.py keystore.jks password123

# 提取keystore信息
python extractor_keystore_info.py keystore.jks password123
```

---

## 🎭 常用密码掩码

```bash
?a?a?a?a?a?a      # 6位任意字符（最全面）
?u?l?l?l?d?d      # 1大写+3小写+2数字（常见Android）
?l?l?l?l?l?l      # 6位小写字母
?d?d?d?d?d?d      # 6位数字
```

---

## 🔍 路径识别规则

### 自动识别逻辑

```
输入路径
    │
    ├─ 文件路径（.jks/.keystore）
    │   → 单文件模式
    │
    └─ 目录路径
        │
        ├─ 目录下直接有.keystore/.jks文件
        │   → UUID子目录模式
        │
        └─ 目录下有子目录
            → 根目录批量模式
```

### 模式输出标识

```bash
✅ 单文件模式：apk.keystore           # 单文件模式
✅ UUID子目录模式：发现 1 个keystore    # UUID子目录模式
✅ 根目录批量模式：遍历 50 个子目录     # 根目录批量模式
```

---

## 🐛 快速故障排除

### "发现 0 个keystore文件"

```bash
# 检查文件是否存在
ls certificate/uuid123/

# 检查文件扩展名
# ✅ 支持: .jks, .keystore
# ❌ 不支持: .txt, .bin
```

### "不支持的文件类型"

```bash
# 确保文件扩展名正确
mv app.bin app.keystore  # 重命名为正确扩展名
```

### "目录名称无效"

```bash
# 旧版本可能不支持单文件模式
# 解决: 更新到 v2.1+
git pull
```

---

## 📊 性能参考

| 场景 | 文件数 | 耗时 | 性能 |
|------|--------|------|------|
| 单文件提取 | 1 | ~0.2秒 | 5 文件/秒 |
| UUID目录提取 | 1-5 | ~0.4秒 | 5 文件/秒 |
| 批量50个提取 | 50 | ~10秒 | 5 文件/秒 |
| GPU破解6位密码 | - | ~66天 | ~10,000 H/s |

---

## 🔧 环境检查命令

```bash
# Java环境
java -version

# Python环境
python --version

# GPU状态
nvidia-smi

# 验证工具
java -jar JKS-private-key-cracker-hashcat/JksPrivkPrepare.jar
```

---

## 📁 目录结构示例

### 批量模式目录结构

```
certificate/
├── 00a1234.../
│   └── apk.keystore
├── 00b5678.../
│   └── apk.keystore
└── 00c9012.../
    └── apk.keystore

命令: python cli_batch_crack.py certificate
输出: ✅ 根目录批量模式：遍历 3 个子目录
```

### UUID目录模式目录结构

```
certificate/00a1234.../
├── apk.keystore
├── app.jks
└── backup.keystore

命令: python cli_batch_crack.py certificate/00a1234...
输出: ✅ UUID子目录模式：发现 3 个keystore
```

### 单文件模式

```
certificate/00a1234.../
└── apk.keystore

命令: python cli_batch_crack.py certificate/00a1234.../apk.keystore
输出: ✅ 单文件模式：apk.keystore
```

---

## 🎯 典型工作流程

### 快速测试单个证书

```bash
# 1. 直接破解UUID目录
python cli_batch_crack.py certificate/uuid123

# 2. 查看结果
cat batch_crack_output/all_keystores.hash
cat batch_crack_output/uuid_hash_mapping.json
```

### 批量处理大规模证书

```bash
# 1. 批量提取和破解
python cli_batch_crack.py certificate

# 2. 监控GPU
nvidia-smi -l 1

# 3. 查看进度
tail -f batch_crack_output/batch_results.potfile
```

### 已知密码提取信息

```bash
# 1. 提取证书信息
python extractor_keystore_info.py keystore.jks password123

# 2. 导出证书文件
python extractor_certificate.py keystore.jks password123
```

---

## 📚 进一步阅读

- **[README.md](README.md)** - 项目概述和快速开始
- **[USAGE_UPDATE.md](USAGE_UPDATE.md)** - 智能路径识别详细指南
- **[CLAUDE.md](CLAUDE.md)** - 完整开发指南
- **[CHANGELOG.md](CHANGELOG.md)** - 版本变更记录

---

## ⚡ 快捷命令别名（可选）

在 `.bashrc` 或 `.zshrc` 中添加：

```bash
# 批量破解
alias jks-crack='python cli_batch_crack.py'

# Hash提取
alias jks-hash='python extractor_jks_hash.py'

# 证书提取
alias jks-cert='python extractor_certificate.py'

# GPU监控
alias gpu-mon='nvidia-smi -l 1'
```

使用示例：
```bash
jks-crack certificate/uuid123
jks-hash certificate
jks-cert keystore.jks password123
gpu-mon
```

---

**快速参考指南 v2.1.0**
**更新日期**: 2025-11-20
