# 使用指南 - 指定破解目录

## 问题
默认情况下，`ultimate_batch_cracker.py` 和 `batch_hash_extractor.py` 会自动使用 `certificate` 目录。如何指定其他目录？

## 解决方案

### 方法1：命令行参数（推荐）

现在两个脚本都支持命令行参数来指定证书目录：

#### ultimate_batch_cracker.py

```bash
# 使用默认的certificate目录
python ultimate_batch_cracker.py

# 使用自定义目录
python ultimate_batch_cracker.py my_certificates

# 使用相对路径
python ultimate_batch_cracker.py ../other_certs

# 使用绝对路径
python ultimate_batch_cracker.py "G:\certs\android_keystores"

# 查看帮助
python ultimate_batch_cracker.py --help
```

#### batch_hash_extractor.py

```bash
# 使用默认的certificate目录
python batch_hash_extractor.py

# 使用自定义目录
python batch_hash_extractor.py my_certificates

# 使用相对路径
python batch_hash_extractor.py ../other_certs

# 查看帮助
python batch_hash_extractor.py --help
```

### 方法2：修改默认值

如果您希望永久更改默认目录，可以编辑文件：

#### ultimate_batch_cracker.py

找到第21行：
```python
def __init__(self, certificate_dir="certificate"):
```

修改为您想要的默认目录：
```python
def __init__(self, certificate_dir="my_default_dir"):
```

#### batch_hash_extractor.py

找到第22行：
```python
def __init__(self, certificate_dir="certificate"):
```

修改为您想要的默认目录：
```python
def __init__(self, certificate_dir="my_default_dir"):
```

## 目录结构要求

无论使用哪个目录，都需要遵循以下结构：

```
your_certificate_dir/
├── [UUID-1]/
│   └── apk.keystore
├── [UUID-2]/
│   └── apk.keystore
├── [UUID-3]/
│   └── apk.keystore
└── ...
```

每个keystore文件都应该：
1. 放在以UUID命名的子目录中
2. 文件名为 `apk.keystore`（或其他 .jks/.p12/.pfx 格式）

## 示例场景

### 场景1：临时测试少量证书

```bash
# 创建测试目录
mkdir test_certs

# 将测试证书复制进去（保持UUID目录结构）
cp -r certificate/uuid-1 test_certs/
cp -r certificate/uuid-2 test_certs/

# 运行破解
python ultimate_batch_cracker.py test_certs
```

### 场景2：多个项目分别管理

```bash
# 项目A的证书
python ultimate_batch_cracker.py project_a_certs

# 项目B的证书
python ultimate_batch_cracker.py project_b_certs
```

### 场景3：使用外部存储

```bash
# 从外部磁盘运行破解
python ultimate_batch_cracker.py "E:\forensic_cases\case_001\keystores"
```

## 常见问题

### Q: 为什么找不到keystore文件？
**A:** 检查以下几点：
1. 目录路径是否正确
2. 是否有UUID子目录
3. keystore文件名是否正确（apk.keystore）

### Q: 可以使用其他文件名吗？
**A:** 目前脚本默认查找 `apk.keystore`。如需使用其他文件名，需要修改代码中的扫描逻辑。

### Q: 支持直接放置keystore文件而不用UUID目录吗？
**A:** 目前需要UUID目录结构。这是为了：
- 唯一标识每个证书
- 在导出结果时提供清晰的ID
- 方便批量管理

## 技术实现

### 参数传递流程

```
命令行 → main() → UltimateBatchCracker(certificate_dir) → BatchHashExtractor(certificate_dir)
```

1. 用户在命令行指定目录（或使用默认值）
2. `main()` 函数解析参数
3. 创建 `UltimateBatchCracker` 实例时传入目录
4. 在hash提取步骤，将目录参数传递给 `BatchHashExtractor`
5. 所有模块使用统一的证书目录

### 兼容性

- ✅ 相对路径
- ✅ 绝对路径
- ✅ Windows路径（带反斜杠）
- ✅ 包含空格的路径（使用引号）

## 更新日志

**v1.1.0 (2024-12-17)**
- 添加命令行参数支持
- 支持自定义证书目录
- 保持向后兼容（默认仍为certificate目录）
