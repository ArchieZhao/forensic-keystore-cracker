# 🔐 JKS Keystore 密码破解成功指南

## 📋 概述

本文档详细记录了成功破解JKS Keystore密码的完整方法，特别适用于Android APK签名证书的密码恢复。该方案已在实际环境中验证成功，7秒内破解6位复杂密码。

## 🛠️ 环境配置

### 硬件要求

- **GPU**: NVIDIA RTX 3080 (推荐) 或其他CUDA兼容显卡
- **CPU**: Intel i9-12900K 或同等性能处理器
- **内存**: 16GB+ DDR4
- **存储**: SSD硬盘 (提升I/O性能)

### 软件环境

- **操作系统**: Windows 11 Pro (测试环境)
- **Java**: JDK 8+ (运行JksPrivkPrepare.jar)
- **Python**: 3.8+
- **CUDA**: 支持RTX 3080的驱动程序

## 🔑 核心技术原理

### 两种破解模式对比

| 破解模式           | 目标         | 工具链                          | 性能        | 适用场景                         |
| ------------------ | ------------ | ------------------------------- | ----------- | -------------------------------- |
| **容器密码** | 整个keystore | keystore2john + John the Ripper | ~500 H/s    | 需要完整访问keystore             |
| **私钥密码** | 单个私钥     | JksPrivkPrepare + Hashcat       | ~10,000 H/s | Android APK签名 (**推荐**) |

### 关键技术发现

**格式兼容性**：

- `$keystore$` 格式 → 仅适用于 John the Ripper
- `$jksprivk$` 格式 → 仅适用于 Hashcat -m 15500
- JksPrivkPrepare.jar 是关键桥接工具

## 🚀 成功案例详解

### 破解目标

- **文件**: `000a205bd2f549078ae9f7b7d5cde1a2\apk.keystore`
- **算法**: RSA 4096位
- **别名**: w8o4
- **密码长度**: 6位 (大小写字母+数字)

### 破解结果

- **密码**: `biCf2k`
- **破解时间**: 7秒
- **GPU速度**: 11,147.5 MH/s
- **进度**: 仅用10.63%即找到密码

## 📦 工具安装配置

### 1. 下载并配置Hashcat

```bash
# 下载Hashcat 6.2.6
wget https://hashcat.net/files/hashcat-6.2.6.7z
7z x hashcat-6.2.6.7z
```

### 2. 获取JksPrivkPrepare.jar

```bash
# 从GitHub获取
git clone https://github.com/FloatingGhost/JKS-private-key-cracker-hashcat.git
# 或直接下载jar文件
```

### 3. Python环境设置

```bash
# 安装依赖
pip install rich psutil colorama
```

## 🔧 关键步骤详解

### 第一步：提取私钥Hash

```bash
java -jar JKS-private-key-cracker-hashcat/JksPrivkPrepare.jar target.keystore > hash.txt
```

**输出示例**：

```
Alias: w8o4, algorithm: RSA, keysize or field size: 4096
$jksprivk$*16D9CFDFE496883B78A8539C1FB932B6035CA4A9*C79C5849366A3D96576A99AED9301A39A8CA49C4*...
```

### 第二步：GPU加速破解

```bash
cd hashcat-6.2.6
./hashcat.exe -m 15500 ../hash.txt -a 3 ?a?a?a?a?a?a --force
```

**关键参数说明**：

- `-m 15500`: JKS私钥模式
- `-a 3`: 暴力攻击模式
- `?a?a?a?a?a?a`: 6位任意字符掩码
- `--force`: 绕过兼容性警告

### 第三步：性能优化

```bash
# 启用优化内核 (适用于短密码)
./hashcat.exe -m 15500 hash.txt -a 3 ?a?a?a?a?a?a --force -O

# GPU工作负载调整
./hashcat.exe -m 15500 hash.txt -a 3 ?a?a?a?a?a?a --force -w 4
```

## 📊 性能分析

### RTX 3080 实测数据

- **原始速度**: 11,147.5 MH/s
- **GPU利用率**: 98%
- **温度**: 57°C (安全范围)
- **内存使用**: 2559MB / 10239MB

### 密码空间分析

- **6位完整字符集**: 62^6 = 56,800,235,584 种组合
- **破解时间估算**: 最坏情况 ~1.4小时
- **实际破解**: 7秒 (10.63%进度)

## 🔥 成功关键因素

### 1. 正确的工具组合

- ✅ **JksPrivkPrepare.jar** 生成正确的 `$jksprivk$` 格式
- ✅ **Hashcat -m 15500** 模式处理JKS私钥
- ❌ 避免使用错误的 `$keystore$` 格式给Hashcat

### 2. GPU优化配置

```bash
# 检查GPU状态
nvidia-smi

# 优化参数组合
-O              # 优化内核
-w 4            # 疯狗工作负载
--force         # 跳过兼容性检查
```

### 3. 密码掩码策略

```bash
# 常用Android签名密码模式
?a?a?a?a?a?a    # 6位任意字符 (推荐)
?u?l?l?l?d?d    # 1大写+3小写+2数字
?l?l?l?l?l?l    # 6位小写字母
?d?d?d?d?d?d    # 6位数字
```

## 🛡️ 故障排除

### 常见问题及解决方案

#### 1. "No hashes loaded" 错误

**原因**: 使用了错误的hash格式
**解决**: 确保使用JksPrivkPrepare.jar生成 `$jksprivk$` 格式

#### 2. "Separator unmatched" 错误

**原因**: keystore2john输出与Hashcat不兼容
**解决**: 使用专门的JksPrivkPrepare.jar工具

#### 3. GPU性能低下

**解决方案**:

```bash
# 检查CUDA驱动
nvidia-smi

# 更新显卡驱动
# 安装最新CUDA Toolkit

# 调整GPU工作负载
./hashcat.exe ... -w 4
```

#### 4. "All hashes found as potfile"

**解决**: 密码已被破解，使用 `--show` 查看结果

```bash
./hashcat.exe -m 15500 hash.txt --show
```

## 📝 自动化脚本

### Python集成破解工具

我们提供了完整的Python工具集：

#### 1. 单文件破解

```bash
python jks_privkey_processor.py target.keystore -m ?a?a?a?a?a?a
```

#### 2. 批量破解

```bash
python jks_privkey_processor.py certificate_directory -m ?a?a?a?a?a?a
```

#### 3. 交互式主程序

```bash
python main.py
```

### 关键代码示例

```python
# JKS私钥处理器核心逻辑
def extract_jks_hash(self, keystore_path):
    result = subprocess.run([
        "java", "-jar", self.jks_prepare_jar, keystore_path
    ], capture_output=True, text=True, check=True)
  
    # 解析输出获取$jksprivk$格式hash
    for line in result.stdout.strip().split('\n'):
        if line.startswith("$jksprivk$"):
            return line
    return None

def crack_jks_password(self, keystore_path, mask="?a?a?a?a?a?a"):
    # 提取hash
    hash_line = self.extract_jks_hash(keystore_path)
  
    # 运行Hashcat
    cmd = [
        self.hashcat_path, "-m", "15500", 
        hash_file, "-a", "3", mask, "--force", "-O"
    ]
  
    result = subprocess.run(cmd, capture_output=True, text=True, cwd="hashcat-6.2.6")
    # 解析破解结果...
```

## 🎯 最佳实践

### 1. 密码策略分析

- **Android开发者常用**: 简单6位字母数字组合
- **企业级**: 可能使用更复杂的8-12位密码
- **测试环境**: 通常使用简单密码如"123456"

### 2. 破解策略优化

```bash
# 阶段1: 快速字典攻击
./hashcat.exe -m 15500 hash.txt -a 0 common_passwords.txt

# 阶段2: 规则增强字典
./hashcat.exe -m 15500 hash.txt -a 0 passwords.txt -r best64.rule

# 阶段3: 掩码暴力破解
./hashcat.exe -m 15500 hash.txt -a 3 ?a?a?a?a?a?a
```

### 3. 性能监控

```bash
# 实时监控GPU状态
watch -n 1 nvidia-smi

# Hashcat状态监控
./hashcat.exe ... --status --status-timer=60
```

## 📈 结果验证

### 成功破解标志

```
Status...........: Cracked
Hash.Mode........: 15500 (JKS Java Key Store Private Keys (SHA1))
Time.Started.....: Tue Jun 17 02:38:52 2025, (7 secs)
Speed.#1.........: 11147.5 MH/s
Recovered........: 1/1 (100.00%) Digests
```

### 密码提取

需要使用JksPrivkPrepare.jar获取hash

```bash
# 查看破解结果
./hashcat.exe -m 15500 hash.txt --show

# 输出格式
$jksprivk$*...*w8o4:biCf2k
```

## 🔒 安全考虑

### 1. 法律合规

- ✅ 仅用于自己拥有的证书
- ✅ 授权的密码恢复任务
- ❌ 禁止用于非法破解他人证书

### 2. 数据保护

- 及时清理临时hash文件
- 安全存储破解结果
- 避免在网络上传输明文密码

## 📚 扩展阅读

### 技术文档

- [Hashcat官方文档](https://hashcat.net/wiki/)
- [JKS格式规范](https://docs.oracle.com/javase/8/docs/technotes/guides/security/crypto/CryptoSpec.html)
- [Android APK签名机制](https://source.android.com/security/apksigning)

### 工具源码

- [JKS-private-key-cracker-hashcat](https://github.com/FloatingGhost/JKS-private-key-cracker-hashcat)
- [John the Ripper](https://github.com/openwall/john)
- [Hashcat](https://github.com/hashcat/hashcat)

## 📞 支持与维护

如需技术支持或遇到问题，请检查：

1. 确保所有依赖工具版本正确
2. 验证GPU驱动程序是否最新
3. 检查Java环境配置
4. 确认hash格式是否正确

---

**最后更新**: 2025年6月17日
**版本**: v1.0
**测试环境**: Windows 11 + RTX 3080 + Hashcat 6.2.6
