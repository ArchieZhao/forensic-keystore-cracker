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

#### 1. 交互式破解（推荐新手）
```bash
python main.py
```
程序会引导完成整个破解流程，包括模式选择、文件选择、掩码配置。

#### 2. 单文件私钥密码破解（推荐）
```bash
python jks_privkey_processor.py target.keystore -m ?a?a?a?a?a?a
```
使用JksPrivkPrepare.jar + Hashcat (mode 15500) 进行GPU加速破解。

#### 3. 批量破解
```bash
# 批量破解整个目录
python jks_privkey_processor.py certificate_folder -m ?u?l?l?l?d?d

# 终极批量破解（70+文件）
python ultimate_batch_cracker.py certificate_folder -m ?a?a?a?a?a?a
```

#### 4. 证书信息提取
```bash
# 提取证书并计算MD5/SHA1指纹
python certificate_extractor.py keystore.jks password123

# 提取指定别名
python certificate_extractor.py keystore.jks password123 -a mykey

# 指定输出目录
python certificate_extractor.py keystore.jks password123 -o certificates
```

### 结果管理命令

```bash
# 导出破解结果为JSON和Excel
python main.py --export SESSION_ID

# 仅导出JSON文件
python main.py --export SESSION_ID --json-only

# 查看所有会话
python main.py --list-sessions
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
用户输入 → main.py (入口)
    ↓
    ├─→ 交互式模式：引导式UI选择
    └─→ 命令行模式：直接处理
         ↓
         ├─→ 私钥破解路径（推荐）:
         │    jks_privkey_processor.py
         │      → JksPrivkPrepare.jar (提取$jksprivk$格式hash)
         │      → gpu_hashcat_cracker.py
         │          → hashcat.exe -m 15500 (GPU加速破解)
         │      → keystore_info_extractor.py (提取证书信息)
         │
         └─→ 容器密码路径:
              certificate_batch_processor.py
                → john/keystore2john.py (提取$keystore$格式)
                → john.exe (CPU破解)
```

### 模块职责

#### 1. **main.py** - 主程序入口
- 提供交互式和命令行两种模式
- 会话管理（新建、恢复、导出）
- 协调各个处理器模块

#### 2. **jks_privkey_processor.py** - JKS私钥破解器（核心）
- 调用JksPrivkPrepare.jar提取私钥hash
- 通过gpu_hashcat_cracker进行GPU破解
- 使用keystore_info_extractor提取成功破解的证书信息
- 支持单文件和批量处理

#### 3. **gpu_hashcat_cracker.py** - GPU破解引擎
- 封装Hashcat调用逻辑
- 实时监控破解进度和GPU状态
- 支持多种hash算法（MD5, JKS-15500, PKCS12-17200）
- 会话管理和断点续传

#### 4. **certificate_extractor.py** - 证书提取工具
- 从已知密码的keystore中提取证书
- 计算公钥MD5和SHA1指纹
- 导出证书为.cer文件

#### 5. **keystore_info_extractor.py** - Keystore信息提取器
- 使用keytool解析keystore详细信息
- 提取别名、证书主体、有效期等
- 计算双重哈希（MD5和SHA1）
- 返回结构化KeystoreInfo对象

#### 6. **progress_manager.py** - 进度管理器
- 保存和恢复破解会话
- 导出结果为JSON和Excel格式
- 使用UUID文件夹名作为唯一标识（而非文件名）

#### 7. **certificate_batch_processor.py** - 容器密码批量处理器
- 使用John the Ripper破解容器密码
- 处理keystore2john输出格式
- 性能较低（~500 H/s）

#### 8. **ultimate_batch_cracker.py** - 终极批量破解器
- 整合所有功能的高级批量处理
- 适用于大规模（70+）证书破解
- 自动化hash提取、破解、结果分析

#### 9. **batch_hash_extractor.py** - 批量hash提取器
- 从多个keystore文件批量提取hash
- 支持并行处理

#### 10. **batch_result_analyzer.py** - 批量结果分析器
- 分析破解结果统计
- 生成详细报告

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
| 私钥密码 | JksPrivkPrepare + Hashcat | ~10,000 H/s | Android APK签名 ⭐ |
| 容器密码 | keystore2john + John | ~500 H/s | 完整keystore访问 |

#### 常用密码掩码
```bash
?a?a?a?a?a?a    # 6位任意字符（默认，最全面）
?u?l?l?l?d?d    # 1大写+3小写+2数字（常见Android模式）
?l?l?l?l?l?l    # 6位小写字母
?d?d?d?d?d?d    # 6位数字
```

## 📂 项目结构

```
forensic/
├── main.py                          # 主程序入口
├── jks_privkey_processor.py         # JKS私钥密码破解器（核心）
├── gpu_hashcat_cracker.py           # GPU Hashcat破解引擎
├── certificate_batch_processor.py   # 容器密码批量处理器
├── certificate_extractor.py         # 证书提取和MD5/SHA1计算工具
├── keystore_info_extractor.py       # Keystore信息提取器
├── progress_manager.py              # 进度管理和结果导出
├── ultimate_batch_cracker.py        # 终极批量破解器
├── batch_hash_extractor.py          # 批量hash提取器
├── batch_result_analyzer.py         # 批量结果分析器
├── requirements.txt                 # Python依赖
│
├── hashcat-6.2.6/                   # Hashcat工具（GPU破解引擎）
│   ├── hashcat.exe                  # 主程序
│   └── OpenCL/                      # GPU计算内核
│
├── john-1.9.0/                      # John the Ripper（CPU破解）
│   ├── run/john.exe
│   └── run/keystore2john.py         # Keystore hash提取脚本
│
├── JKS-private-key-cracker-hashcat/
│   └── JksPrivkPrepare.jar          # ⭐关键工具：生成Hashcat兼容的JKS hash
│
├── certificate/                     # 输入：待破解的keystore文件
│   └── [UUID]/                      # 使用UUID文件夹名作为唯一标识
│       └── apk.keystore
│
├── certificates/                    # 输出：导出的证书文件
├── analysis_results/                # 输出：破解结果和日志
├── progress/                        # 会话进度保存目录
└── batch_crack_output/              # 批量破解输出目录
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
在`gpu_hashcat_cracker.py`的`hash_algorithms`字典中添加：
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
修改`progress_manager.py`中的导出函数：
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

### 场景1：单个证书快速破解
```bash
# 1. 直接运行私钥破解
python jks_privkey_processor.py certificate/uuid/apk.keystore -m ?a?a?a?a?a?a

# 2. 自动流程：
#    - 提取$jksprivk$格式hash
#    - 调用Hashcat GPU破解
#    - 破解成功后提取证书信息（别名、MD5、SHA1）
#    - 显示结果表格
```

### 场景2：批量破解70个证书
```bash
# 1. 运行终极批量破解器
python ultimate_batch_cracker.py certificate_folder -m ?a?a?a?a?a?a

# 2. 自动流程：
#    - 扫描目录下所有keystore文件
#    - 批量提取所有hash
#    - GPU并行破解
#    - 提取所有成功破解的证书信息
#    - 生成Excel和JSON报告
```

### 场景3：已知密码提取证书信息
```bash
# 1. 提取证书和指纹
python certificate_extractor.py keystore.jks password123

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
- 使用`ultimate_batch_cracker.py`而非循环调用单文件处理
- 合并hash文件后统一破解
- 利用Hashcat的并行hash处理能力

## 🔍 调试技巧

### 查看Hashcat破解状态
```bash
cd hashcat-6.2.6
./hashcat.exe -m 15500 ../hash.txt --show  # 查看已破解密码
```

### 检查会话进度
```bash
python main.py --list-sessions  # 列出所有会话
python main.py --export SESSION_ID  # 导出会话结果
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

### 为什么推荐私钥模式而非容器模式？
- 性能差异巨大：~10,000 H/s vs ~500 H/s
- Android APK签名只需要私钥密码
- GPU加速仅在Hashcat中有效（私钥模式）

### 为什么同时提取MD5和SHA1？
- Android不同版本使用不同算法
- MD5用于旧版本APK签名验证
- SHA1是当前主流标准
- 提供双重验证确保证书匹配

## 🔄 更新日志

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
