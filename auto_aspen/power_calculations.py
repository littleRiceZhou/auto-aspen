"""
电力机组参数计算模块
根据主机参数计算过程、公用功耗计算过程、经济性分析和机组选型的计算流程封装功能函数
"""

import math
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from loguru import logger


@dataclass
class MainEngineParams:
    """主机参数"""
    # 前一步输入值（从ASPEN计算得来）
    main_power: float  # 主机功率 (kW)
    
    # 系统效率参数
    isentropic_efficiency: float = 0.85  # 叶轮等熵效率
    gap_leakage_factor: float = 0.98  # 间隙泄露系数
    volute_loss_factor: float = 0.98  # 蜗壳损失系数
    wheel_resistance_factor: float = 0.98  # 轮阻损失系数
    gearbox_loss_factor: float = 1.0  # 齿轮箱损失系数 (恢复为1.0)
    generator_efficiency: float = 0.92  # 发电机效率


@dataclass
class UtilityParams:
    """公用功耗参数"""
    # 冷却系统参数
    lubrication_oil_flow_rate: float = 79.578716  # 润滑油流量 (基于表格Input Value)
    oil_cooler_temp_rise: float = 8  # 油冷器水侧温升 (℃)
    cooling_water_pressure_ratio: float = 4.2  # 冷却水定压比热容 (kJ/kg·℃)
    mechanical_loss_ratio: float = 0.04  # 机械损失比例
    lubrication_oil_density: float = 850  # 润滑油流量密度
    lubrication_oil_heat_capacity: float = 2  # 润滑油定压比热容
    
    # 基于表格的组件功率参数 (单位: kW) - 恢复匹配54kW的参数
    lubrication_pump_power: float = 3  # 润滑油泵功率 (对应流量79.578716)
    lubrication_heater_power: float = 0.6  # 润滑油加热器功率 (恢复优化值)
    generator_heater_power: float = 0.2  # 发电机加热器功率 (恢复优化值)
    valve_power: float = 0.5  # 轮失阀功率
    plc_power: float = 0.3  # PLC控制系统功率 (恢复优化值)
    bearing_power: float = 0  # 电磁轴承功率
    
    # 流体需求参数
    air_demand_nm3: float = 4  # 空气需求量 (Nm³/h)
    air_demand_nm3_per_h: float = 40  # 氮气需求量 (Nm³/h)
    
    # 其他参数
    oil_cooler_flow_temp_rise: float = 8  # 油冷器循环冷却水温升 (℃)
    cooling_water_flow_temp_rise: float = 0.32205315  # 油冷器循环冷却水 (t/h)


@dataclass
class EconomicParams:
    """经济性分析参数"""
    # 经济参数
    annual_operating_hours: float = 8000  # 年运行时间 (小时)
    electricity_price: float = 0.6  # 电价 (元/kWh)
    standard_coal_coefficient: float = 0.35  # 标煤换算系数
    standard_coal_price: float = 500  # 标煤价格 (元/吨)
    co2_emission_factor: float = 0.96  # CO2排放系数


@dataclass
class UnitSelectionParams:
    """机组选型参数"""
    # 机组尺寸系数
    dimensions: Tuple[float, float, float] = (3, 2.5, 2.5)  # 尺寸 (m)
    weight_per_unit: float = 15  # 重量 (t/台)


class PowerCalculations:
    """电力机组计算类"""
    
    def __init__(self):
        self.logger = logger
    
    def calculate_main_engine_params(self, params: MainEngineParams) -> Dict[str, Any]:
        """
        计算主机参数过程
        """
        try:
            # 1. 主机损失功率计算
            # 公式：主机损失功率 = 叶轮等熵效率×间隙泄露系数×蜗壳损失系数×轮阻损失系数
            main_loss_power = (params.main_power * 
                             params.isentropic_efficiency * 
                             params.gap_leakage_factor * 
                             params.volute_loss_factor * 
                             params.wheel_resistance_factor)
            
            # 2. 主机输出功率计算
            # 公式：主机输出功率 = 主机功率×间隙泄露系数×蜗壳损失系数×轮阻损失系数
            main_output_power = (params.main_power * 
                                params.gap_leakage_factor * 
                                params.volute_loss_factor * 
                                params.wheel_resistance_factor)
            
            # 3. 机组总发电量计算
            # 公式：机组总发电量 = 主机输出功率×齿轮箱损失系数×发电机效率
            total_power_generation = (main_output_power * 
                                    params.gearbox_loss_factor * 
                                    params.generator_efficiency)
            
            results = {
                "main_loss_power": main_loss_power,  # 主机损失功率
                "main_output_power": main_output_power,  # 主机输出功率
                "total_power_generation": total_power_generation,  # 机组总发电量
                "input_power": params.main_power  # 输入的主机功率
            }
            
            self.logger.info(f"主机参数计算完成: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"主机参数计算错误: {str(e)}")
            raise
    
    def calculate_utility_power_consumption(self, main_engine_results: Dict[str, Any], 
                                          params: UtilityParams) -> Dict[str, Any]:
        """
        计算公用功耗过程
        """
        try:
            # 从主机计算结果获取主机输出功率
            main_output_power = main_engine_results["main_output_power"]
            # 1. 润滑油量计算
            # 公式：润滑油量 = 1.2×主机输出功率×机械损失比例/(润滑油流量密度×润滑油定压比热容×润滑油温升)*60*1000
            lubrication_oil_amount = (1.2 * main_output_power * params.mechanical_loss_ratio / 
                                    (params.lubrication_oil_density * params.lubrication_oil_heat_capacity * 
                                     params.oil_cooler_temp_rise)*60*1000)
            
            # 2. 油冷器循环冷却水计算  
            # 公式：油冷器循环冷却水 = 1.2×主机输出功率×机械损失比例/冷却水定压比热容×冷却水温升×3.6
            oil_cooler_circulation_water = (1.2 * main_output_power * params.mechanical_loss_ratio / 
                                          params.cooling_water_pressure_ratio / params.oil_cooler_temp_rise * 3.6)
            
            
            # 3. 油泵功率 (查表，根据润滑油量查取)
            oil_pump_power = lookup_oil_pump_power(lubrication_oil_amount)
            
            # 4. 公用功耗自耗电计算 (按照正确公式)
            # 公式：公用功耗自耗电 = 润滑油泵功率+润滑油加热器功率（0.5油泵功率）+发电机加热器功率（固定1）+快关阀功率（固定0.5）+PLC控制柜功率（固定2）
            lubrication_heater_power = 0.5 * oil_pump_power  # 润滑油加热器功率（0.5油泵功率）
            generator_heater_power = 1.0  # 发电机加热器功率（固定1kW）
            valve_power = 0.5  # 快关阀功率（固定0.5kW）
            plc_power = 2.0  # PLC控制柜功率（固定2kW）
            
            utility_self_consumption = (
                oil_pump_power +                    # 润滑油泵功率（查表获得）
                lubrication_heater_power +          # 润滑油加热器功率（0.5×油泵功率）
                generator_heater_power +            # 发电机加热器功率（固定1kW）
                valve_power +                       # 快关阀功率（固定0.5kW）
                plc_power                          # PLC控制柜功率（固定2kW）
            )
            
            # 6. 净发电功率计算
            # 公式：净发电功率 = 机组总发电量-公用功耗自耗电
            net_power_output = (main_engine_results["total_power_generation"] - 
                              utility_self_consumption)
            
            # 7. 空气需求量计算
            air_demand_nm3_s = params.air_demand_nm3
            
            # 8. 氮气需求量计算  
            nitrogen_demand_nm3_h = params.air_demand_nm3_per_h
            
            results = {
                "lubrication_oil_amount": lubrication_oil_amount,  # 润滑油量
                "oil_cooler_circulation_water": oil_cooler_circulation_water,  # 油冷器循环冷却水
                "oil_pump_power": oil_pump_power,  # 油泵功率(查表)
                "utility_self_consumption": utility_self_consumption,  # 公用功耗自耗电
                "net_power_output": net_power_output,  # 净发电功率
                "air_demand_nm3_s": air_demand_nm3_s,  # 空气需求量(Nm³/s)
                "nitrogen_demand_nm3_h": nitrogen_demand_nm3_h,  # 氮气需求量(Nm³/h)
                # 各组件功耗详情
                "component_powers": {
                    "lubrication_pump": oil_pump_power,          # 润滑油泵功率（查表）
                    "lubrication_heater": lubrication_heater_power,  # 润滑油加热器功率（0.5×油泵功率）
                    "generator_heater": generator_heater_power,   # 发电机加热器功率（固定1kW）
                    "valve": valve_power,                        # 快关阀功率（固定0.5kW）
                    "plc": plc_power                            # PLC控制柜功率（固定2kW）
                }
            }
            
            self.logger.info(f"公用功耗计算完成: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"公用功耗计算错误: {str(e)}")
            raise
    
    def calculate_economic_analysis(self, utility_results: Dict[str, Any], 
                                  params: EconomicParams) -> Dict[str, Any]:
        """
        计算经济性分析
        """
        try:
            net_power_output = utility_results["net_power_output"]
            
            # 1. 年发电量计算
            # 公式：年发电量 = 净发电功率×年运行时间/10000
            annual_power_generation = (net_power_output * params.annual_operating_hours / 10000)
            
            # 2. 年发电收益计算
            # 公式：年发电收益 = 年发电量×电价
            annual_power_income = annual_power_generation * params.electricity_price
            
            # 3. 年节约标煤计算
            # 公式：年节约标煤 = 年发电量×标煤换算系数 * 10
            annual_coal_savings = annual_power_generation * params.standard_coal_coefficient * 10
            
            # 4. 年节煤效益计算
            # 公式：年节煤效益 = 年节约标煤×煤价/10000
            annual_coal_cost_savings = annual_coal_savings * params.standard_coal_price / 10000
            
            # 5. 年CO2减排量计算
            # 公式：年CO2减排量 = 年发电量×二氧化碳排放系数 * 10
            annual_co2_reduction = annual_power_generation * params.co2_emission_factor * 10
            
            results = {
                "annual_power_generation": annual_power_generation,  # 年发电量(万kWh)
                "annual_power_income": annual_power_income,  # 年发电收益(万元)
                "annual_coal_savings": annual_coal_savings,  # 年节约标煤(万吨)
                "annual_coal_cost_savings": annual_coal_cost_savings,  # 年节煤效益(万元)
                "annual_co2_reduction": annual_co2_reduction,  # 年CO2减排量(万吨)
            }
            
            self.logger.info(f"经济性分析计算完成: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"经济性分析计算错误: {str(e)}")
            raise
    
    def calculate_unit_selection(self, main_engine_results: Dict[str, Any], 
                               utility_results: Dict[str, Any], 
                               params: UnitSelectionParams) -> Dict[str, Any]:
        """
        计算机组选型
        """
        try:
            # 从主机计算结果获取机组总发电量
            total_power_generation = main_engine_results.get("total_power_generation", 0)
            
            # 1. 机组选择（装机功率）计算
            # 公式：机组选择 = ROUND(机组总发电量*1.1/100, 0)*100
            unit_selection = round(total_power_generation * 1.1 / 100, 0) * 100
            
            # 2. 根据装机功率查表获取机组尺寸和重量
            unit_dimensions, unit_weight = lookup_unit_dimensions_weight(unit_selection)
            
            # 3. 如果查表失败，使用默认参数
            if unit_dimensions is None:
                unit_dimensions = params.dimensions
                unit_weight = params.weight_per_unit
            
            results = {
                "unit_selection": unit_selection,  # 机组选择(装机功率)
                "unit_dimensions": unit_dimensions,  # 机组尺寸(长×宽×高) - 查表获取
                "unit_weight": unit_weight,  # 机组重量(t/台) - 查表获取
                "lookup_power": unit_selection,  # 用于查表的功率值
            }
            
            self.logger.info(f"机组选型计算完成: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"机组选型计算错误: {str(e)}")
            raise
    
    def calculate_all_stages(self, 
                           main_engine_params: MainEngineParams,
                           utility_params: UtilityParams,
                           economic_params: EconomicParams,
                           unit_selection_params: UnitSelectionParams) -> Dict[str, Any]:
        """
        执行所有计算阶段的完整流程
        
        :param main_engine_params: 主机参数
        :param utility_params: 公用功耗参数
        :param economic_params: 经济性分析参数
        :param unit_selection_params: 机组选型参数
        :return: 所有计算结果
        """
        try:
            self.logger.info("开始执行完整的计算流程...")
            
            # 1. 主机参数计算
            main_engine_results = self.calculate_main_engine_params(main_engine_params)
            
            # 2. 公用功耗计算
            utility_results = self.calculate_utility_power_consumption(
                main_engine_results, utility_params)
            
            # 3. 经济性分析计算
            economic_results = self.calculate_economic_analysis(
                utility_results, economic_params)
            
            # 4. 机组选型计算
            unit_selection_results = self.calculate_unit_selection(
                main_engine_results, utility_results, unit_selection_params)
            
            # 汇总所有结果
            all_results = {
                "main_engine": main_engine_results,
                "utility_power": utility_results,
                "economic_analysis": economic_results,
                "unit_selection": unit_selection_results,
                "calculation_summary": {
                    "input_main_power": main_engine_params.main_power,
                    "final_net_power": utility_results["net_power_output"],
                    "annual_income": economic_results["annual_power_income"],
                    "selected_unit_power": unit_selection_results["unit_selection"]
                }
            }
            
            self.logger.info("完整计算流程执行完成")
            return all_results
            
        except Exception as e:
            self.logger.error(f"完整计算流程执行错误: {str(e)}")
            raise


def lookup_oil_pump_power(lubrication_oil_amount: float) -> float:
    """
    根据润滑油量查询油泵功率
    基于用户提供的油耗表格数据
    """
    # 基于图片中的油耗表格数据
    # Input Value 79.578716 对应 Return Value 3
    # 流量-功率对照表
    flow_power_table = [
        (28.4, 1.5),   # 润滑油加热器
        (37.9, 1.5),   # 发电机加热器  
        (60, 2.2),     # 轮失阀
        (80, 3),       # PLC
        (108, 4),
        (157, 5.5),
        (189, 7.5),
        (225, 7.5),
        (277, 11),
        (319, 11),
        (401, 15),
        (471, 15),
        (536, 15),
        (596, 18.5),
        (662, 22),
        (846, 30),
        (1035, 30)
    ]
    
    # 根据润滑油量查找对应的油泵功率
    for flow, power in flow_power_table:
        if lubrication_oil_amount <= flow:
            return power
    
    # 如果超出范围，返回最大功率
    return flow_power_table[-1][1]


def lookup_unit_dimensions_weight(unit_power: float) -> Tuple[Tuple[float, float, float], float]:
    """
    根据机组功率查询机组尺寸和重量
    基于用户提供的机组选型表格数据
    """
    # 基于图片中的机组选型表格数据
    # 功率(kW) -> (尺寸(长×宽×高), 重量(t))


    unit_lookup_table = [
        (0, (3, 2.5, 2.5), "14t/5t"),
        (250, (3, 2.5, 2.5), "15t/5t"),      # 对应表格中250功率
        (400, (3.5, 2.5, 2.5), "16t/5t"),   # Input Value 400对应的数据
        (450, (4, 2.5, 2.5), "17t/5t"),
        (500, (4.5, 2.5, 2.5), "17t/6t"),
        (560, (4.5, 3, 2.5), "18t/8t"),
        (630, (5, 3, 2.5), "20t/9t"),
        (710, (5.5, 3, 2.5), "22t/10t"),
        (800, (6, 3, 2.5), "24t/11t"),
        (900, (6.5, 3, 2.5), "25t/12t"),
        (1120, (6.5, 3, 2.5), "26t/12t"),
        (1250, (6.5, 3, 2.5), "27t/13t"),
        (1400, (7, 3, 2.5), "28t/13t"),
        (1600, (7.5, 3, 2.5), "29t/14t"),
        (1800, (8, 3.5, 2.5), "30t/15t"),
        (2000, (8.5, 3.5, 2.5), "31t/16t"),
        (2240, (9, 3.5, 2.5), "32t/16t"),
        (2500, (9.5, 4, 2.5), "33t/16t"),
        (2800, (9.5, 4, 2.5), "34t/17t"),
        (3150, (10.5, 4, 2.5), "35t/17t"),
        (3550, (11, 4, 2.5), "38t/18t"),
        (4000, (12, 4, 2.5), "40t/18t"),
        (7000, (12, 6, 4), "50t/20t")
    ]
    
    # 查找最接近的功率等级
    for power, dimensions, weight in unit_lookup_table:
        if unit_power <= power:
            return dimensions, weight
    
    # 如果超出范围，返回最大规格
    return unit_lookup_table[-1][1], unit_lookup_table[-1][2]


def get_utility_component_power(component_type: str) -> float:
    """
    获取公用设备组件功率
    """
    # 基于图片中的设备功率表
    component_power_map = {
        "润滑油泵": 3,         # 对应流量79.578716的功率3
        "润滑油加热器": 1.5,    # 对应流量28.4的功率1.5
        "发电机加热器": 1,      # 发电机加热器
        "轮失阀": 0.5,         # 轮失阀
        "PLC": 2,              # PLC控制系统
        "电磁轴承": 0          # 电磁轴承
    }
    
    return component_power_map.get(component_type, 0)


def calculate_utility_power_with_lookup(main_output_power: float, oil_flow_rate: float) -> Dict[str, float]:
    """
    使用查表方式计算公用功耗
    """
    # 1. 根据油流量查询油泵功率
    oil_pump_power = lookup_oil_pump_power(oil_flow_rate)
    
    # 2. 获取各组件功率
    lubrication_heater_power = get_utility_component_power("润滑油加热器")
    generator_heater_power = get_utility_component_power("发电机加热器")  
    valve_power = get_utility_component_power("轮失阀")
    plc_power = get_utility_component_power("PLC")
    bearing_power = get_utility_component_power("电磁轴承")
    
    # 3. 计算总公用功耗
    total_utility_power = (oil_pump_power + lubrication_heater_power + 
                          generator_heater_power + valve_power + 
                          plc_power + bearing_power)
    
    return {
        "oil_pump_power": oil_pump_power,
        "lubrication_heater_power": lubrication_heater_power,
        "generator_heater_power": generator_heater_power,
        "valve_power": valve_power,
        "plc_power": plc_power,
        "bearing_power": bearing_power,
        "total_utility_power": total_utility_power
    }


# 使用示例
if __name__ == "__main__":
    # 创建计算器实例
    calculator = PowerCalculations()
    
    # 设置参数
    main_params = MainEngineParams(main_power=66.53419)  # 从ASPEN计算得来的主机功率
    utility_params = UtilityParams()
    economic_params = EconomicParams()
    unit_selection_params = UnitSelectionParams()
    
    # 执行完整计算流程
    results = calculator.calculate_all_stages(
        main_params, utility_params, economic_params, unit_selection_params)
    
    # 输出结果
    print("=== 电力机组参数计算结果 ===")
    for stage, stage_results in results.items():
        print(f"\n{stage}:")
        if isinstance(stage_results, dict):
            for key, value in stage_results.items():
                print(f"  {key}: {value}")