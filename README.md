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

## demo
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
面向对象APWZ仿真器使用示例
"""

import sys
from loguru import logger
from auto_aspen import PyASPENPlus, SimulationParameters, SimulationResult, APWZSimulator


def example_basic_usage():
    """基本使用示例"""
    logger.info("=== 基本使用示例 ===")
    
    # 创建仿真参数
    params = SimulationParameters(
        gas_flow_rate=15000.0,  # scmh
        inlet_pressure=0.8,     # MPaA
        inlet_temperature=30.0, # °C
        outlet_pressure=2.5,    # MPaA
        efficiency=85.0,        # %
        gas_composition={
            'CH4': 90.0,
            'C2H6': 5.0,
            'C3H8': 2.0,
            'N2': 2.0,
            'CO2': 1.0
        }
    )
    
    # 使用上下文管理器
    with APWZSimulator("RE-Expander.apwz") as simulator:
        result = simulator.run_full_simulation(params)
        
        if result.success:
            logger.info("✅ 仿真成功完成")
            result.save_to_json("basic_example_results.json")
        else:
            logger.error("❌ 仿真失败")
            for error in result.errors:
                logger.error(f"错误: {error}")


def example_step_by_step():
    """分步骤执行示例"""
    logger.info("=== 分步骤执行示例 ===")
    
    # 从文件加载参数
    params = SimulationParameters.from_file()
    params.log_parameters()
    
    # 创建仿真器
    simulator = APWZSimulator("RE-Expander.apwz", aspen_version="14.0")
    
    try:
        # 步骤1: 初始化
        if not simulator.initialize(visible=True, dialogs=False):
            logger.error("初始化失败")
            return
        
        # 步骤2: 设置参数
        if simulator.set_parameters(params):
            logger.info("参数设置成功")
        else:
            logger.warning("参数设置可能不完整")
        
        # 步骤3: 运行仿真
        if simulator.run_simulation():
            logger.info("仿真运行成功")
        else:
            logger.error("仿真运行失败")
            return
        
        # 步骤4: 获取结果
        result = simulator.get_results()
        result.log_results()
        result.save_to_json("step_by_step_results.json")
        
    finally:
        # 步骤5: 清理资源
        simulator.close()


def example_batch_simulation():
    """批量仿真示例"""
    logger.info("=== 批量仿真示例 ===")
    
    # 定义多组参数
    parameter_sets = [
        {
            'name': '低压工况',
            'params': SimulationParameters(
                gas_flow_rate=8000.0,
                inlet_pressure=0.3,
                outlet_pressure=2.0,
                efficiency=75.0
            )
        },
        {
            'name': '标准工况',
            'params': SimulationParameters(
                gas_flow_rate=10000.0,
                inlet_pressure=0.5,
                outlet_pressure=3.0,
                efficiency=80.0
            )
        },
        {
            'name': '高压工况',
            'params': SimulationParameters(
                gas_flow_rate=12000.0,
                inlet_pressure=0.8,
                outlet_pressure=4.0,
                efficiency=85.0
            )
        }
    ]
    
    results = []
    
    for i, param_set in enumerate(parameter_sets):
        logger.info(f"开始仿真: {param_set['name']}")
        
        with APWZSimulator("RE-Expander.apwz") as simulator:
            result = simulator.run_full_simulation(param_set['params'])
            
            # 保存结果
            output_file = f"batch_results_{i+1}_{param_set['name']}.json"
            result.save_to_json(output_file)
            results.append({
                'name': param_set['name'],
                'success': result.success,
                'errors': len(result.errors),
                'warnings': len(result.warnings)
            })
    
    # 汇总结果
    logger.info("批量仿真汇总:")
    for result in results:
        status = "✅ 成功" if result['success'] else "❌ 失败"
        logger.info(f"  {result['name']}: {status} (错误: {result['errors']}, 警告: {result['warnings']})")


def example_custom_parameters():
    """自定义参数示例"""
    logger.info("=== 自定义参数示例 ===")
    
    # 创建自定义参数
    custom_params = SimulationParameters()
    
    # 修改特定参数
    custom_params.gas_flow_rate = 20000.0
    custom_params.inlet_temperature = 15.0
    custom_params.gas_composition = {
        'CH4': 95.0,   # 高甲烷含量
        'C2H6': 3.0,
        'N2': 2.0
    }
    
    logger.info("使用自定义参数:")
    custom_params.log_parameters()
    
    with APWZSimulator("RE-Expander.apwz") as simulator:
        result = simulator.run_full_simulation(custom_params)
        
        if result.success:
            logger.info("✅ 自定义参数仿真成功")
            
            # 输出关键结果
            if result.streams:
                logger.info("关键物料流参数:")
                for stream_name, stream_data in result.streams.items():
                    logger.info(f"  {stream_name}: {stream_data}")
            
            result.save_to_json("custom_params_results.json")
        else:
            logger.error("❌ 自定义参数仿真失败")


def main():
    """主函数"""
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    logger.info("🚀 开始面向对象APWZ仿真器使用示例")
    
    try:
        # 运行各种示例
        example_basic_usage()
        example_step_by_step()
        example_batch_simulation()
        example_custom_parameters()
        
        logger.info("🎉 所有示例执行完成")
        
    except Exception as e:
        logger.error(f"示例执行失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 
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