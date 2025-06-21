# ASPEN Plus .apwz 文件支持

本项目现在支持加载和运行 ASPEN Plus 的 `.apwz` 文件格式。

## 功能特性

- ✅ 支持 `.apwz` 文件自动解压和加载
- ✅ 兼容原有的 `.bkp` 文件格式
- ✅ 自动识别解压后的文件类型（`.apw`, `.bkp`, `.backup`）
- ✅ 智能选择合适的加载方法
- ✅ 完整的仿真结果获取和分析
- ✅ 临时文件自动清理

## 支持的文件格式

| 格式 | 描述 | 加载方法 |
|------|------|----------|
| `.bkp` | ASPEN Plus 备份文件 | `InitFromArchive2` |
| `.apwz` | ASPEN Plus 压缩工作文件 | 解压后根据内容选择 |
| `.apw` | ASPEN Plus 工作文件 | `InitFromTemplate2` |
| `.backup` | ASPEN Plus 备份文件 | `InitFromArchive2` |

## 使用方法

### 方法1: 一键运行

```python
from auto_aspen import PyASPENPlus

aspen = PyASPENPlus()

# 运行 .apwz 文件
result = aspen.run(
    file_name="RE-Expander.apwz",
    ap_version="14.0",
    visible=True,
    return_json=True
)

print(f"仿真成功: {result['success']}")
print(f"物料流数量: {result['summary']['stream_count']}")
print(f"设备块数量: {result['summary']['block_count']}")
```

### 方法2: 分步运行

```python
from auto_aspen import PyASPENPlus

aspen = PyASPENPlus()

# 初始化
aspen.init_app(ap_version="14.0")

# 加载文件
aspen.load_ap_file("RE-Expander.apwz", visible=True)

# 运行仿真
aspen.run_simulation()

# 检查状态
status = aspen.check_simulation_status()
print(f"仿真状态: {'成功' if status[0] else '失败'}")

# 获取结果
results = aspen.get_simulation_results()

# 关闭应用
aspen.close_app()
```

## 工作原理

当加载 `.apwz` 文件时，系统会：

1. **检测文件格式**: 识别 `.apwz` 是 ZIP 压缩文件
2. **创建临时目录**: 在系统临时目录创建工作空间
3. **解压文件**: 将 `.apwz` 文件解压到临时目录
4. **查找主文件**: 按优先级查找 `.apw` > `.bkp` > `.backup` 文件
5. **选择加载方法**: 
   - `.apw` 文件使用 `InitFromTemplate2`
   - `.bkp`/`.backup` 文件使用 `InitFromArchive2`
6. **运行仿真**: 正常执行仿真流程
7. **清理资源**: 自动清理临时文件

## 示例文件

项目包含以下示例脚本：

- `run_apwz.py` - 简单的运行脚本
- `run_apwz_debug.py` - 调试版本，显示详细信息
- `test_apwz.py` - 完整的测试脚本
- `example_apwz_usage.py` - 功能演示脚本

## 运行示例

```bash
# 简单运行
python run_apwz.py

# 调试模式
python run_apwz_debug.py

# 完整示例
python example_apwz_usage.py
```

## 注意事项

1. **ASPEN Plus 版本**: 确保指定正确的 ASPEN Plus 版本号
2. **文件路径**: 支持相对路径和绝对路径
3. **权限**: 确保有足够的权限创建临时目录和访问文件
4. **资源清理**: 系统会自动清理临时文件，但在某些情况下可能需要手动清理

## 错误处理

系统包含完善的错误处理机制：

- 文件格式验证
- 解压过程异常处理
- 多种加载方法尝试
- 资源清理保障
- 详细的错误信息输出

## 系统要求

- Python 3.6+
- ASPEN Plus (推荐 V10.0 或更高版本)
- Windows 操作系统
- pywin32 库

## 更新日志

- **v1.1.0**: 添加 `.apwz` 文件支持
- **v1.0.0**: 基础 `.bkp` 文件支持 