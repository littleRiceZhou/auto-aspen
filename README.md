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


# 电力机组参数计算模块

## 概述

本模块根据图片中的计算流程封装了电力机组参数计算的功能函数，包括以下四个主要计算阶段：

1. **主机参数计算过程** - 计算主机损失功率、输出功率和总发电量
2. **公用功耗计算过程** - 计算润滑油量、冷却水、净发电功率等
3. **经济性分析** - 计算年发电量、收益、节煤效益等
4. **机组选型** - 根据功率确定机组尺寸和重量

## 文件结构

```
auto_aspen/
├── power_calculations.py      # 主要计算模块
├── test_power_calculations.py # 测试脚本
└── README_power_calculations.md # 本文档
```

## 主要类和函数

### 数据类 (DataClass)

#### MainEngineParams
主机参数配置类
```python
@dataclass
class MainEngineParams:
    main_power: float              # 主机功率 (kW) - 从ASPEN计算得来
    wheel_loss_factor: float = 0.85       # 叶轮损失系数
    generator_efficiency: float = 0.85    # 发电机效率
    main_loss_factor: float = 0.80        # 主机损失系数
    cooling_loss_factor: float = 0.98     # 回路冷却系数
    frequency_loss_factor: float = 0.98   # 频率损失系数
    wheel_resistance_factor: float = 0.98 # 轮阻损失系数
```

#### UtilityParams
公用功耗参数配置类
```python
@dataclass
class UtilityParams:
    lubrication_oil_flow_rate: float = 1.5     # 润滑油流量密度
    oil_cooler_temp_rise: float = 8            # 油冷器水侧温升 (℃)
    cooling_water_pressure_ratio: float = 4.2  # 冷却水定压比热容
    lubrication_power_factor: float = 1.5      # 润滑油泵功率 (kW)
    utility_power_factor: float = 5.75         # 公用功耗自耗电 (kW)
    air_demand_nm3: float = 4                  # 空气需求量 (Nm³/s)
    air_demand_nm3_per_h: float = 40           # 氮气需求量 (Nm³/h)
```

#### EconomicParams
经济性分析参数配置类
```python
@dataclass
class EconomicParams:
    annual_operating_hours: float = 8000    # 年运行时间 (小时)
    electricity_price: float = 0.6          # 电价 (元/kWh)
    standard_coal_coefficient: float = 0.35 # 标煤换算系数
    standard_coal_price: float = 500        # 标煤价格 (元/吨)
    co2_emission_factor: float = 0.96       # CO2排放系数
```

#### UnitSelectionParams
机组选型参数配置类
```python
@dataclass
class UnitSelectionParams:
    dimensions: Tuple[float, float, float] = (3, 2.5, 2.5)  # 尺寸 (m)
    weight_per_unit: float = 15                              # 重量 (t/台)
```

### 主要计算类

#### PowerCalculations
电力机组计算的主类，包含所有计算方法。

##### 主要方法：

1. **calculate_main_engine_params(params: MainEngineParams) -> Dict[str, Any]**
   
   计算主机参数过程，包括：
   - 主机损失功率 = 叶轮等损失率 × 回路冷却系数 × 频率损失系数 × 轮阻损失系数
   - 主机输出功率 = 主机功率 × 回路冷却系数 × 频率损失系数 × 轮阻损失系数  
   - 机组总发电量 = 主机输出功率 × 齿轮箱损失系数 × 发电机效率

2. **calculate_utility_power_consumption(main_engine_results, params: UtilityParams) -> Dict[str, Any]**
   
   计算公用功耗过程，包括：
   - 润滑油量计算
   - 油冷器循环冷却水计算
   - 公用功耗自耗电计算
   - 净发电功率计算
   - 空气和氮气需求量

3. **calculate_economic_analysis(utility_results, params: EconomicParams) -> Dict[str, Any]**
   
   计算经济性分析，包括：
   - 年发电量 = 净发电功率 × 年运行时间 / 10000
   - 年发电收益 = 年发电量 × 电价
   - 年节约标煤 = 年发电量 × 标煤换算系数
   - 年节煤效益 = 年节约标煤 × 煤价
   - 年CO2减排量 = 年发电量 × 二氧化碳排放系数

4. **calculate_unit_selection(utility_results, params: UnitSelectionParams) -> Dict[str, Any]**
   
   计算机组选型，包括：
   - 机组选择(装机功率) = ROUND(机组总发电量 × 1.1 / 100.0) × 100
   - 机组尺寸和重量查表

5. **calculate_all_stages(...) -> Dict[str, Any]**
   
   执行所有计算阶段的完整流程

### 查表功能函数

#### lookup_oil_pump_power(lubrication_oil_amount: float) -> float
根据润滑油量查询对应的油泵功率

#### lookup_unit_dimensions_weight(unit_power: float) -> Tuple[Tuple[float, float, float], float]
根据机组功率查询对应的机组尺寸和重量

## 使用示例

### 基本使用方法

```python
from power_calculations import (
    PowerCalculations, 
    MainEngineParams, 
    UtilityParams, 
    EconomicParams, 
    UnitSelectionParams
)

# 1. 创建计算器实例
calculator = PowerCalculations()

# 2. 设置参数
main_params = MainEngineParams(main_power=66.53419)  # 从ASPEN计算得来的主机功率
utility_params = UtilityParams()
economic_params = EconomicParams()
unit_selection_params = UnitSelectionParams()

# 3. 执行完整计算流程
results = calculator.calculate_all_stages(
    main_params, 
    utility_params, 
    economic_params, 
    unit_selection_params
)

# 4. 获取结果
print(f"净发电功率: {results['utility_power']['net_power_output']:.2f} kW")
print(f"年发电收益: {results['economic_analysis']['annual_power_income']:.2f} 万元")
```

### 分步计算示例

```python
calculator = PowerCalculations()

# 1. 主机参数计算
main_params = MainEngineParams(main_power=66.53419)
main_results = calculator.calculate_main_engine_params(main_params)

# 2. 基于主机结果计算公用功耗
utility_params = UtilityParams()
utility_results = calculator.calculate_utility_power_consumption(main_results, utility_params)

# 3. 经济性分析
economic_params = EconomicParams()
economic_results = calculator.calculate_economic_analysis(utility_results, economic_params)

# 4. 机组选型
unit_params = UnitSelectionParams()
unit_results = calculator.calculate_unit_selection(utility_results, unit_params)
```

### 自定义参数示例

```python
# 自定义经济参数
custom_economic_params = EconomicParams(
    annual_operating_hours=7500,  # 年运行7500小时
    electricity_price=0.65,       # 电价0.65元/kWh
    standard_coal_price=550       # 标煤价格550元/吨
)

# 自定义主机参数
custom_main_params = MainEngineParams(
    main_power=80.0,              # 主机功率80kW
    generator_efficiency=0.90,    # 发电机效率90%
    cooling_loss_factor=0.99      # 回路冷却系数99%
)
```

## 计算结果结构

完整流程计算返回的结果包含以下结构：

```python
{
    "main_engine": {
        "main_loss_power": float,        # 主机损失功率
        "main_output_power": float,      # 主机输出功率
        "total_power_generation": float, # 机组总发电量
        "input_power": float             # 输入的主机功率
    },
    "utility_power": {
        "lubrication_oil_amount": float,        # 润滑油量
        "oil_cooler_circulation_water": float,  # 油冷器循环冷却水
        "oil_pump_power": float,                # 油泵功率
        "utility_self_consumption": float,      # 公用功耗自耗电
        "net_power_output": float,              # 净发电功率
        "air_demand_nm3_s": float,              # 空气需求量(Nm³/s)
        "nitrogen_demand_nm3_h": float          # 氮气需求量(Nm³/h)
    },
    "economic_analysis": {
        "annual_power_generation": float,    # 年发电量(万kWh)
        "annual_power_income": float,        # 年发电收益(万元)
        "annual_coal_savings": float,        # 年节约标煤(万吨)
        "annual_coal_cost_savings": float,   # 年节煤效益(万元)
        "annual_co2_reduction": float        # 年CO2减排量(万吨)
    },
    "unit_selection": {
        "unit_selection": float,           # 机组选择(装机功率)
        "unit_dimensions": tuple,          # 机组尺寸(长×宽×高)
        "unit_weight": float               # 机组重量(t/台)
    },
    "calculation_summary": {
        "input_main_power": float,         # 输入主机功率
        "final_net_power": float,          # 最终净发电功率
        "annual_income": float,            # 年发电收益
        "selected_unit_power": float       # 选定机组功率
    }
}
```

## 运行测试

使用提供的测试脚本验证功能：

```bash
python test_power_calculations.py
```

测试脚本会验证：
- 所有计算函数是否正常工作
- 完整工作流程是否能顺利执行
- 结果结构是否正确

## 公式说明

### 1. 主机参数计算

- **主机损失功率** = 叶轮等损失率 × 回路冷却系数 × 频率损失系数 × 轮阻损失系数
- **主机输出功率** = 主机功率 × 回路冷却系数 × 频率损失系数 × 轮阻损失系数
- **机组总发电量** = 主机输出功率 × 齿轮箱损失系数 × 发电机效率

### 2. 公用功耗计算

- **润滑油量** = 1.2 × 主机输出功率 × 机械损失比例 / 润滑油流量密度 / 润滑油定压比热容 × 润滑油温升 × 60 × 1000
- **油冷器循环冷却水** = 1.2 × 主机输出功率 × 机械损失比例 / 冷却水定压比热容 × 冷却水温升 × 3.6
- **公用功耗自耗电** = 润滑油泵功率 + 润滑油加热功率(0.5油泵功率) + 定冷机器功率(回路1) + 水泵功率(回路2)
- **净发电功率** = 机组总发电量 - 公用功耗自耗电

### 3. 经济性分析

- **年发电量** = 净发电功率 × 年运行时间 / 10000
- **年发电收益** = 年发电量 × 电价
- **年节约标煤** = 年发电量 × 标煤换算系数
- **年节煤效益** = 年节约标煤 × 煤价
- **年CO2减排量** = 年发电量 × 二氧化碳排放系数

### 4. 机组选型

- **机组选择** = ROUND(机组总发电量 × 1.1 / 100.0) × 100

## 注意事项

1. **输入参数**：主机功率需要从ASPEN Plus计算结果中获取
2. **单位**：注意各参数的单位，确保计算结果的准确性
3. **查表功能**：油泵功率和机组尺寸重量基于预设表格，可根据实际需要调整
4. **日志记录**：所有计算过程都有详细的日志记录，便于调试

## 扩展功能

模块设计为可扩展的结构，可以方便地：
- 添加新的计算步骤
- 修改现有的公式和参数
- 集成更复杂的查表逻辑
- 添加数据验证和错误处理

## 依赖项

- Python 3.6+
- numpy
- loguru (日志记录)
- dataclasses (Python 3.7+, 或使用typing_extensions)

## 版本历史

- v1.0: 初始版本，实现基本的四阶段计算流程 