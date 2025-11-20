# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🎯 项目定位

这是一个专业的数字取证工具集，专注于JKS/Keystore密码破解和Android APK签名证书分析。旨在帮助调查人员快速分析数据、编写脚本、找到答案、解决问题、完成调查任务，而不是被繁琐的流程和形式所束缚。

### 核心功能
- **GPU加速密码破解**: 使用Hashcat进行高性能JKS/PKCS12私钥密码破解
- **批量处理**: 支持单文件和大规模目录批量破解（70+文件）
- **证书分析**: 提取公钥MD5/SHA1指纹、证书信息
- **进度管理**: 断点续传、会话保存、结果导出（JSON/Excel）

### 适用场景
- Android APK签名证书密码恢复
- 数字取证调查中的证书分析
- 批量keystore密码破解
- 授权的安全测试和学术研究

## 🛠️ 常用命令

### 破解命令

#### 1. 批量Hash提取
```bash
# 从默认certificate目录提取
python extractor_jks_hash.py -m ?a?a?a?a?a?a

# 从自定义目录提取
python extractor_jks_hash.py -d /path/to/keystores -m ?u?l?l?l?d?d

# 提取到指定输出文件
python extractor_jks_hash.py -m ?a?a?a?a?a?a -o my_hashes.txt
```

#### 2. 批量破解（推荐）
```bash
# 批量破解默认目录（certificate/）
python cli_batch_crack.py -m ?a?a?a?a?a?a

# 批量破解自定义目录
python cli_batch_crack.py -d /path/to/keystores -m ?u?l?l?l?d?d

# 指定输出目录
python cli_batch_crack.py -m ?a?a?a?a?a?a -o custom_output
```

#### 3. GPU破解
```bash
# 使用GPU破解hash文件
python cracker_hashcat_gpu.py hash.txt -m ?a?a?a?a?a?a

# 指定算法类型（JKS私钥）
python cracker_hashcat_gpu.py hash.txt -m ?a?a?a?a?a?a -a jksprivk

# 启用优化和高性能模式
python cracker_hashcat_gpu.py hash.txt -m ?a?a?a?a?a?a -O -w 4
```

#### 4. 证书信息提取
```bash
# 提取证书并计算MD5/SHA1指纹
python extractor_certificate.py keystore.jks password123

# 提取指定别名
python extractor_certificate.py keystore.jks password123 -a mykey

# 指定输出目录
python extractor_certificate.py keystore.jks password123 -o certificates
```

#### 5. Keystore信息提取
```bash
# 提取keystore详细信息（别名、证书、指纹）
python extractor_keystore_info.py keystore.jks password123
```

#### 6. 性能测试
```bash
# 测试并行提取vs串行提取的性能对比
python test_parallel_performance.py
```

### 测试和调试命令

```bash
# 验证Java环境
java -version

# 验证keytool
keytool -help

# 检查GPU状态
nvidia-smi

# 手动提取JKS hash
java -jar JksPrivkPrepare.jar target.keystore

# 手动运行Hashcat
cd hashcat-6.2.6
./hashcat.exe -m 15500 ../hash.txt -a 3 ?a?a?a?a?a?a --force
```

## 🏗️ 架构设计

### 核心工作流程

```
用户输入 → 批量破解工具
    ↓
    ├─→ extractor_jks_hash.py
    │    → 扫描目录下所有keystore文件
    │    → JksPrivkPrepare.jar (提取$jksprivk$格式hash)
    │    → 生成统一的hash文件
    │
    ├─→ cracker_hashcat_gpu.py
    │    → hashcat.exe -m 15500 (GPU加速破解)
    │    → 实时监控破解进度
    │    → 返回破解结果
    │
    ├─→ cli_batch_crack.py
    │    → 整合hash提取 + GPU破解 + 结果分析
    │    → 批量处理完整流程
    │    → 导出详细报告
    │
    └─→ 结果处理:
         ├─→ extractor_keystore_info.py (提取证书详细信息)
         ├─→ extractor_certificate.py (导出证书文件和指纹)
         ├─→ manager_crack_progress.py (进度管理和结果导出)
         └─→ analyzer_crack_result.py (批量结果分析)
```

### 模块职责

#### 1. **extractor_jks_hash.py** - 批量Hash提取器
- 扫描指定目录下的所有keystore文件
- 调用JksPrivkPrepare.jar批量提取私钥hash
- 支持自定义证书目录和输出文件
- 生成统一的hash文件供Hashcat使用

#### 2. **cli_batch_crack.py** - 终极批量破解器（核心）
- 整合完整的批量破解流程
- 自动提取hash、GPU破解、结果分析
- 支持自定义证书目录和输出目录
- 生成详细的Excel和JSON报告
- 适用于大规模（70+）证书破解

#### 3. **cracker_hashcat_gpu.py** - GPU破解引擎
- 封装Hashcat调用逻辑
- 实时监控破解进度和GPU状态
- 支持多种hash算法（MD5, JKS-15500, PKCS12-17200）
- 会话管理和断点续传

#### 4. **extractor_certificate.py** - 证书提取工具
- 从已知密码的keystore中提取证书
- 计算公钥MD5和SHA1指纹
- 导出证书为.cer文件

#### 5. **extractor_keystore_info.py** - Keystore信息提取器
- 使用keytool解析keystore详细信息
- 提取别名、证书主体、有效期等
- 计算双重哈希（MD5和SHA1）
- 返回结构化KeystoreInfo对象

#### 6. **manager_crack_progress.py** - 进度管理器
- 保存和恢复破解会话
- 导出结果为JSON和Excel格式
- 使用UUID文件夹名作为唯一标识（而非文件名）

#### 7. **analyzer_crack_result.py** - 批量结果分析器（⚡ 多进程并行优化）
- 分析破解结果统计
- 生成详细报告
- **多进程并行提取**：利用CPU多核并行提取证书信息，性能提升12-15倍
- 支持CPU核心数自动检测（使用N-1个进程）
- 实时进度条显示并行提取进度

#### 8. **monitor_gpu_performance.py** - GPU状态监控
- 实时监控GPU温度和利用率
- 显示破解性能数据

### 关键技术要点

#### Hash格式兼容性（重要！）
```
工具                  输出格式          兼容工具
keystore2john.py  →  $keystore$    →  John the Ripper
JksPrivkPrepare.jar → $jksprivk$   →  Hashcat -m 15500 ⭐
```

**关键发现**: 必须使用JksPrivkPrepare.jar生成`$jksprivk$`格式才能用Hashcat破解JKS私钥。keystore2john生成的格式只能用于John the Ripper。

#### 破解模式对比
| 模式 | 工具组合 | 性能 | 适用场景 |
|------|---------|------|---------|
| JKS私钥密码 | JksPrivkPrepare + Hashcat GPU | ~10,000 H/s | Android APK签名破解 ⭐ |
| 批量破解 (70+ 文件) | ultimate_batch_cracker | 并行处理 | 大规模取证分析 ⭐ |

#### 常用密码掩码
```bash
?a?a?a?a?a?a    # 6位任意字符（默认，最全面）
?u?l?l?l?d?d    # 1大写+3小写+2数字（常见Android模式）
?l?l?l?l?l?l    # 6位小写字母
?d?d?d?d?d?d    # 6位数字
```

## 📂 项目结构

```
forensic-keystore-cracker/
├── extractor_jks_hash.py          # 批量hash提取器
├── cli_batch_crack.py        # 终极批量破解器（完整流程）
├── cracker_hashcat_gpu.py           # GPU Hashcat破解引擎
├── extractor_certificate.py         # 证书提取和MD5/SHA1计算
├── extractor_keystore_info.py       # Keystore信息提取器
├── manager_crack_progress.py              # 进度管理和结果导出
├── analyzer_crack_result.py         # 批量结果分析器
├── monitor_gpu_performance.py                   # GPU状态监控
├── requirements.txt                 # Python依赖
├── README.md                        # 项目说明文档
├── CLAUDE.md                        # 开发指南和架构文档
│
├── hashcat-6.2.6/                   # Hashcat工具（GPU破解引擎）
│   ├── hashcat.exe                  # 主程序
│   └── OpenCL/                      # GPU计算内核
│
├── john-1.9.0/                      # John the Ripper（CPU破解）
│   └── run/keystore2john.py         # Keystore hash提取脚本
│
├── JKS-private-key-cracker-hashcat/
│   └── JksPrivkPrepare.jar          # ⭐关键工具：JKS hash提取
│
├── certificate/                     # 输入：待破解的keystore文件
│   └── [UUID]/                      # 使用UUID文件夹名作为唯一标识
│       └── apk.keystore
│
├── batch_crack_output/              # 输出：批量破解结果
├── progress/                        # 会话进度保存目录
└── testandold/                      # 测试文件和旧版本代码
```

## 🔧 开发指南

### 环境要求
- **Python**: 3.8+
- **Java**: JDK 8+（运行JksPrivkPrepare.jar和keytool）
- **GPU**: NVIDIA显卡（推荐RTX 3080）
- **CUDA**: 兼容显卡的驱动程序
- **操作系统**: Windows 11（主要测试环境）

### 依赖安装
```bash
pip install -r requirements.txt
```

核心依赖：
- `rich` - 终端UI和进度显示
- `pandas` + `openpyxl` - Excel结果导出
- `psutil` - 系统和GPU监控
- `colorama` - 彩色输出

### 添加新功能的指南

#### 1. 添加新的hash算法支持
在`cracker_hashcat_gpu.py`的`hash_algorithms`字典中添加：
```python
self.hash_algorithms = {
    'new_algo': {
        'mode': 'XXXXX',  # Hashcat模式号
        'name': 'Algorithm Name',
        'pattern': r'regex_pattern'
    }
}
```

#### 2. 添加新的密码掩码模式
在调用破解函数时传入自定义掩码：
```python
processor.process_keystore(file, mask="?u?u?l?l?d?d?s?s")
```

#### 3. 扩展结果导出格式
修改`manager_crack_progress.py`中的导出函数：
```python
def export_to_format(self, session_id, format_type):
    # 添加新的导出格式逻辑
```

### 错误处理最佳实践

#### 常见错误和处理
1. **"No hashes loaded"** - 确保使用正确的hash格式（JksPrivkPrepare.jar → `$jksprivk$`）
2. **"Separator unmatched"** - 检查hash文件格式，避免使用keystore2john输出给Hashcat
3. **GPU性能低** - 检查CUDA驱动，使用`-w 4`和`-O`参数优化
4. **Java环境问题** - 确保`java`和`keytool`在PATH中

### 代码风格
- 使用Rich库进行所有终端输出
- 所有用户可见信息使用中文
- 文件路径统一使用`Path`对象处理
- 错误信息要详细且可操作

## 🎯 工作流程示例

### 场景1：批量破解证书（推荐）
```bash
# 1. 运行终极批量破解器
python cli_batch_crack.py -m ?a?a?a?a?a?a

# 2. 自动流程：
#    - 扫描默认certificate目录下所有keystore文件
#    - 批量提取所有hash（调用JksPrivkPrepare.jar）
#    - GPU并行破解（Hashcat -m 15500）
#    - 提取所有成功破解的证书信息（别名、MD5、SHA1）
#    - 生成Excel和JSON报告到batch_crack_output/
```

### 场景2：自定义目录批量破解
```bash
# 1. 指定证书目录和输出目录
python cli_batch_crack.py -d /path/to/keystores -m ?u?l?l?l?d?d -o custom_output

# 2. 自动流程：
#    - 扫描指定目录下所有keystore文件
#    - 批量提取、GPU破解、结果分析
#    - 输出到custom_output目录
```

### 场景3：分步操作（高级用户）
```bash
# 1. 批量提取hash
python extractor_jks_hash.py -m ?a?a?a?a?a?a -o my_hashes.txt

# 2. GPU破解
python cracker_hashcat_gpu.py my_hashes.txt -m ?a?a?a?a?a?a -a jksprivk -O -w 4

# 3. 提取证书信息（破解成功后）
python extractor_certificate.py keystore.jks password123
```

### 场景4：已知密码提取证书信息
```bash
# 1. 提取证书和指纹
python extractor_certificate.py keystore.jks password123

# 2. 输出：
#    - 导出证书文件（.cer）
#    - 显示MD5指纹
#    - 显示SHA1指纹
#    - 证书详细信息
```

## 🚨 安全和法律注意事项

### 合法使用
- ✅ 仅用于自己拥有的证书
- ✅ 授权的密码恢复任务
- ✅ 学术研究和安全测试
- ❌ 禁止用于非法破解他人证书

### 数据保护
- 破解完成后及时清理临时hash文件
- 安全存储破解结果
- 避免在网络上传输明文密码
- 使用`analysis_results/`目录保存敏感结果

## 📊 性能优化建议

### GPU优化
```bash
# 启用优化内核（适用于短密码）
-O

# 调整工作负载（1-4，4为最高）
-w 4

# 调整GPU利用率
--gpu-temp-abort=90

# 使用多GPU
-d 1,2,3,4
```

### 批量处理优化
- 使用`cli_batch_crack.py`而非循环调用单文件处理
- 合并hash文件后统一破解
- 利用Hashcat的并行hash处理能力

## 🔍 调试技巧

### 查看Hashcat破解状态
```bash
cd hashcat-6.2.6
./hashcat.exe -m 15500 ../hash.txt --show  # 查看已破解密码
```

### 检查破解结果
```bash
# 查看批量破解输出目录
ls batch_crack_output/

# 查看Excel结果
# 打开 batch_crack_output/batch_crack_results_YYYYMMDD_HHMMSS.xlsx
```

### 手动验证工具链
```bash
# 1. 验证Java环境
java -version

# 2. 测试JksPrivkPrepare.jar
java -jar JksPrivkPrepare.jar test.keystore

# 3. 验证keytool
keytool -list -keystore test.keystore -storepass password

# 4. 检查GPU
nvidia-smi
```

## 📝 关键设计决策

### 为什么使用UUID文件夹名作为ID？
在Excel/JSON导出中，使用父目录名（UUID）而非文件名作为唯一标识，因为：
- 多个证书可能使用相同文件名（如`apk.keystore`）
- UUID提供唯一性，便于数据库关联
- 符合Android开发者证书管理习惯

### 为什么使用批量破解模式？
- 大规模取证场景需要处理多个证书
- 批量提取hash后可并行破解，提升效率
- 统一的结果管理和报告生成
- GPU加速下性能可达~10,000 H/s

### 为什么同时提取MD5和SHA1？
- Android不同版本使用不同算法
- MD5用于旧版本APK签名验证
- SHA1是当前主流标准
- 提供双重验证确保证书匹配

## 🔄 更新日志

### v2.0.0 (2025-11-20)
- 简化项目结构，移除交互式模式
- 专注于批量破解场景
- 新增自定义证书目录支持
- 改进命令行参数和帮助信息
- 优化批量处理性能

### v1.2.0 (2024-12-17)
- 双重哈希值提取（MD5 + SHA1）
- ID字段改为UUID文件夹名
- 并行计算优化

### v1.1.0 (2024-06-17)
- 结果导出（JSON + Excel）
- 自动信息提取

### v1.0.0 (2024-06-17)
- 首次发布
- JKS私钥GPU破解
- 批量处理支持
