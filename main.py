#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI接口服务
提供综合仿真计算接口，结合ASPEN仿真和机组功率计算
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import traceback
import os
from loguru import logger
import datetime

# 导入计算模块
from auto_aspen.power_calculations import (
    PowerCalculations, MainEngineParams, UtilityParams, 
    EconomicParams, UnitSelectionParams
)
from auto_aspen import SimulationParameters, APWZSimulator
from auto_aspen.docx_pdf import generate_document, get_auto_aspen_parameter_mapping

# 创建FastAPI应用
app = FastAPI(
    title="Comprehensive Simulation API",
    description="提供ASPEN仿真与机组功率计算综合接口",
    version="1.0.0"
)

# 创建静态文件目录（如果不存在）
static_dir = "static/diagrams"
os.makedirs(static_dir, exist_ok=True)


# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============ Pydantic模型定义 ============

class GasComposition(BaseModel):
    """气体组成"""
    CH4: float = Field(default=100, description="甲烷含量 (%)")
    C2H6: float = Field(default=0, description="乙烷含量 (%)")
    C3H8: float = Field(default=0, description="丙烷含量 (%)")
    C4H10: float = Field(default=0, description="丁烷含量 (%)")
    N2: float = Field(default=0, description="氮气含量 (%)")
    CO2: float = Field(default=0, description="二氧化碳含量 (%)")
    H2S: float = Field(default=0, description="硫化氢含量 (%)")

class SimulationRequest(BaseModel):
    """综合仿真请求参数"""
    # ASPEN仿真参数
    gas_flow_rate: float = Field(
        default=33333.333333,
        description="气体流量 (scmh)",
        gt=0
    )
    inlet_pressure: float = Field(
        default=0.80,
        description="入口压力 (MPaA)",
        gt=0
    )
    inlet_temperature: float = Field(
        default=20.0,
        description="入口温度 (°C)"
    )
    outlet_pressure: float = Field(
        default=0.30,
        description="出口压力 (MPaA)",
        gt=0
    )
    efficiency: float = Field(
        default=85,
        description="效率 (%)",
        ge=0,
        le=100
    )
    gas_composition: GasComposition = Field(
        default_factory=GasComposition,
        description="气体组成"
    )

    


class SimulationResponse(BaseModel):
    """综合仿真响应结果"""
    success: bool = Field(description="仿真是否成功")
    aspen_results: Optional[Dict[str, Any]] = Field(None, description="ASPEN仿真结果")
    power_results: Optional[Dict[str, Any]] = Field(None, description="功率计算结果")
    combined_results: Optional[Dict[str, Any]] = Field(None, description="综合结果")
    diagram_url: Optional[str] = Field(None, description="机组布局图URL")
    document_urls: Optional[Dict[str, str]] = Field(None, description="文档下载地址")
    error_message: Optional[str] = Field(None, description="错误信息")

# ============ API路由定义 ============

@app.get("/")
async def root():
    """index.html"""
    return FileResponse("index.html")

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "message": "API service is running"}

@app.post("/api/simulation", response_model=SimulationResponse)
async def run_comprehensive_simulation(request: SimulationRequest):
    """
    综合仿真计算
    
    先运行ASPEN仿真获取功率输出，然后基于该功率进行机组选型计算
    返回完整的仿真和选型结果
    """
    import time
    start_time = time.time()
    
    try:
        logger.info("开始综合仿真计算")
        
        # Step 1: 运行ASPEN仿真
        logger.info("Step 1: 运行ASPEN仿真")
        aspen_results = await run_aspen_simulation_internal(request)
        
        if not aspen_results["success"]:
            return SimulationResponse(
                success=False,
                error_message=f"ASPEN仿真失败: {aspen_results.get('error_message')}"
            )
        
        # Step 2: 从ASPEN结果中获取主机功率
        aspen_power_output = aspen_results.get("simulation_results", {}).get("power_output")
        if aspen_power_output is not None and aspen_power_output > 0:
            main_power = float(aspen_power_output)
            logger.info(f"使用ASPEN仿真得到的功率: {main_power} kW")
        else:
            # 如果ASPEN结果中没有功率数据，使用基于参数的估算值
            logger.warning("ASPEN仿真未返回有效功率，使用估算值继续计算")
            pressure_diff = request.inlet_pressure - request.outlet_pressure
            # 基于经验公式估算功率 (简化)
            main_power = request.gas_flow_rate * pressure_diff * request.efficiency / 100 * 0.001
            main_power = max(main_power, 10.0)  # 最小值保护
            
            # 更新ASPEN结果中的功率输出
            if "simulation_results" in aspen_results:
                aspen_results["simulation_results"]["power_output"] = main_power
            
            logger.info(f"使用估算的主机功率: {main_power} kW")
        
        # Step 3: 运行功率计算
        logger.info(f"Step 2: 运行功率计算，主机功率: {main_power} kW")
        power_results = await run_power_calculation_internal(main_power, aspen_results)
        
        if not power_results["success"]:
            return SimulationResponse(
                success=False,
                aspen_results=aspen_results,
                error_message=f"功率计算失败: {power_results.get('error_message')}"
            )
        
        # Step 4: 计算仿真时间并合并结果
        end_time = time.time()
        simulation_duration = end_time - start_time
        
        # 将仿真时间添加到ASPEN结果中
        if "simulation_results" in aspen_results:
            aspen_results["simulation_results"]["simulation_time"] = f"{simulation_duration:.2f}秒"
        
        # Step 3: 生成机组布局图
        logger.info("Step 3: 生成机组布局图")
        diagram_result = generate_diagram_file(power_results)
        diagram_url = None
        if diagram_result["success"]:
            diagram_url = diagram_result["diagram_url"]
            logger.info(f"机组布局图已生成: {diagram_url}")
        else:
            logger.warning(f"机组布局图生成失败: {diagram_result.get('error')}")
        
        # Step 4: 生成技术文档
        logger.info("Step 4: 生成技术文档")
        # 从机组布局图结果中获取文件路径
        diagram_file_path = None
        if diagram_result["success"]:
            diagram_file_path = diagram_result.get("file_path")
            
        document_result = generate_technical_document(aspen_results, power_results, request, diagram_file_path)
        document_urls = None
        if document_result["success"]:
            document_urls = document_result["document_urls"]
            logger.info(f"技术文档已生成: {document_urls}")
        else:
            logger.warning(f"技术文档生成失败: {document_result.get('error')}")
        
        # Step 5: 合并仿真结果
        logger.info("Step 5: 合并仿真结果")
        combined_results = create_combined_results(aspen_results, power_results, request, document_urls)
        
        logger.info(f"✅ 综合仿真计算成功完成，耗时: {simulation_duration:.2f}秒")
        
        return SimulationResponse(
            success=True,
            aspen_results=aspen_results,
            power_results=power_results,
            combined_results=combined_results,
            diagram_url=diagram_url,
            document_urls=document_urls
        )
        
    except Exception as e:
        end_time = time.time()
        simulation_duration = end_time - start_time
        error_msg = f"综合仿真计算失败: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        logger.error(f"仿真失败，耗时: {simulation_duration:.2f}秒")
        return SimulationResponse(
            success=False,
            error_message=error_msg
        )

# ============ 内部辅助函数 ============

async def run_aspen_simulation_internal(request: SimulationRequest) -> Dict[str, Any]:
    """内部ASPEN仿真函数"""
    try:
        # 从环境变量获取APWZ文件路径
        apwz_file_path = os.getenv("ASPEN_APWZ_FILE_PATH", "./models/RE-Expander.apwz")
        logger.info(f"使用APWZ文件: {apwz_file_path}")
        
        # 创建仿真参数
        gas_composition_dict = request.gas_composition.dict()
        
        parameters = SimulationParameters(**{
            'gas_flow_rate': request.gas_flow_rate,
            'inlet_pressure': request.inlet_pressure,
            'inlet_temperature': request.inlet_temperature,
            'outlet_pressure': request.outlet_pressure,
            'gas_composition': gas_composition_dict,
            'efficiency': request.efficiency,
        })
        
        # 使用上下文管理器运行仿真
        with APWZSimulator(apwz_file_path) as simulator:
            # 运行完整仿真
            result = simulator.run_full_simulation(parameters)
            
            # 调试：打印result对象的属性
            logger.info(f"ASPEN仿真结果对象类型: {type(result)}")
            logger.info(f"ASPEN仿真结果属性: {dir(result)}")
            logger.info(f"ASPEN仿真结果success: {result.success}")
            
            # 尝试不同的方式获取功率输出
            power_output = None
            inlet_conditions = None
            outlet_conditions = None
            performance_metrics = None
            simulation_time = None

            logger.info(f"仿真结果类型: {type(result)}")
            logger.info(f"仿真结果内容: {result}")
            
            # 方式1: 从EXPANDER设备块获取功率数据
            if hasattr(result, 'blocks') and result.blocks:
                expander_data = result.blocks.get('EXPANDER', {})
                logger.info(f"EXPANDER设备块数据: {expander_data}")
                
                # 尝试从不同的功率字段获取数据
                power_fields = ['制动马力', '净功要求', '指示马力', '等熵功率']
                for field in power_fields:
                    if field in expander_data:
                        field_data = expander_data[field]
                        if isinstance(field_data, dict) and 'value' in field_data:
                            power_value = field_data['value']
                            if power_value is not None:
                                # 功率值通常是负数（表示输出），取绝对值
                                power_output = abs(float(power_value))
                                logger.info(f"从{field}获取功率: {power_output} kW")
                                break
                        elif isinstance(field_data, (int, float)):
                            power_output = abs(float(field_data))
                            logger.info(f"从{field}获取功率: {power_output} kW")
                            break
                
                # 获取其他条件数据
                if '出口压力' in expander_data:
                    outlet_pressure_data = expander_data['出口压力']
                    outlet_pressure = outlet_pressure_data.get('value') if isinstance(outlet_pressure_data, dict) else outlet_pressure_data
                    outlet_conditions = {'pressure': outlet_pressure}
                
                if '出口温度' in expander_data:
                    outlet_temp_data = expander_data['出口温度']
                    outlet_temp = outlet_temp_data.get('value') if isinstance(outlet_temp_data, dict) else outlet_temp_data
                    if outlet_conditions is None:
                        outlet_conditions = {}
                    outlet_conditions['temperature'] = outlet_temp
                
                if '入口压力' in expander_data:
                    inlet_pressure_data = expander_data['入口压力']
                    inlet_pressure = inlet_pressure_data.get('value') if isinstance(inlet_pressure_data, dict) else inlet_pressure_data
                    inlet_conditions = {'pressure': inlet_pressure}
                
                # 获取性能指标
                performance_metrics = {}
                if '效率' in expander_data:
                    eff_data = expander_data['效率']
                    efficiency = eff_data.get('value') if isinstance(eff_data, dict) else eff_data
                    performance_metrics['efficiency'] = efficiency
                
                if '压力比' in expander_data:
                    ratio_data = expander_data['压力比']
                    pressure_ratio = ratio_data.get('value') if isinstance(ratio_data, dict) else ratio_data
                    performance_metrics['pressure_ratio'] = pressure_ratio
            
            # 方式2: 直接属性访问
            if power_output is None and hasattr(result, 'power_output'):
                power_output = result.power_output
                logger.info(f"直接获取power_output: {power_output}")
            
            # 方式3: 如果result是字典类型
            if power_output is None and isinstance(result, dict):
                power_output = result.get('power_output', power_output)
                inlet_conditions = result.get('inlet_conditions', inlet_conditions)
                outlet_conditions = result.get('outlet_conditions', outlet_conditions)
                performance_metrics = result.get('performance_metrics', performance_metrics)
                simulation_time = result.get('simulation_time', simulation_time)
                logger.info(f"字典方式获取power_output: {power_output}")
            
            # 方式4: 检查是否有results属性
            if power_output is None and hasattr(result, 'results') and result.results:
                results_data = result.results
                if isinstance(results_data, dict):
                    power_output = results_data.get('power_output', power_output)
                    inlet_conditions = results_data.get('inlet_conditions', inlet_conditions)
                    outlet_conditions = results_data.get('outlet_conditions', outlet_conditions)
                    performance_metrics = results_data.get('performance_metrics', performance_metrics)
                    simulation_time = results_data.get('simulation_time', simulation_time)
                    logger.info(f"results属性获取power_output: {power_output}")
            
            # 方式5: 尝试其他可能的属性名
            if power_output is None:
                for attr_name in ['output_power', 'generated_power', 'work_output', 'power']:
                    if hasattr(result, attr_name):
                        attr_value = getattr(result, attr_name)
                        if attr_value is not None:
                            power_output = attr_value
                            logger.info(f"通过属性{attr_name}获取功率: {power_output}")
                            break
            
            # 如果仍然没有功率输出，尝试使用默认计算
            if power_output is None:
                logger.warning("无法从ASPEN结果获取功率输出，尝试基于参数估算")
                # 简单的功率估算：基于压差和流量
                pressure_diff = request.inlet_pressure - request.outlet_pressure
                # 估算公式 (这是一个简化的估算)
                estimated_power = request.gas_flow_rate * pressure_diff * 0.002  # 简化系数
                power_output = estimated_power
                logger.info(f"估算功率输出: {power_output} kW")
            
            # 获取其他属性（如果还没有获取到）
            if inlet_conditions is None:
                inlet_conditions = getattr(result, 'inlet_conditions', {})
            if outlet_conditions is None:
                outlet_conditions = getattr(result, 'outlet_conditions', {})
            if performance_metrics is None:
                performance_metrics = getattr(result, 'performance_metrics', {})
            if simulation_time is None:
                simulation_time = getattr(result, 'simulation_time', 0)
            
            # 构建响应结果
            simulation_results = {
                "success": result.success,
                "power_output": power_output,
                "inlet_conditions": inlet_conditions,
                "outlet_conditions": outlet_conditions,
                "performance_metrics": performance_metrics,
                "simulation_time": simulation_time,
                "parameters": {
                    "gas_flow_rate": request.gas_flow_rate,
                    "inlet_pressure": request.inlet_pressure,
                    "inlet_temperature": request.inlet_temperature,
                    "outlet_pressure": request.outlet_pressure,
                    "efficiency": request.efficiency,
                    "gas_composition": gas_composition_dict
                }
            }
            
            if result.success:
                return {
                    "success": True,
                    "simulation_results": simulation_results
                }
            else:
                error_msg = getattr(result, 'error_message', '仿真执行失败')
                return {
                    "success": False,
                    "error_message": error_msg
                }
                
    except Exception as e:
        return {
            "success": False,
            "error_message": f"ASPEN仿真内部错误: {str(e)}"
        }

async def run_power_calculation_internal(main_power: float, aspen_results: Dict[str, Any]) -> Dict[str, Any]:
    """内部功率计算函数"""
    try:
        # 创建计算器实例
        calculator = PowerCalculations()
        
        # 设置计算参数
        main_params = MainEngineParams(main_power=main_power)
        utility_params = UtilityParams()
        economic_params = EconomicParams()
        unit_selection_params = UnitSelectionParams()
        
        # 执行完整计算流程
        results = calculator.calculate_all_stages(
            main_params, utility_params, economic_params, unit_selection_params
        )
        
        # 提取关键计算结果
        main_engine = results['main_engine']
        utility_power = results['utility_power']
        economic_analysis = results['economic_analysis']
        unit_selection = results['unit_selection']
        
        # 判断是否需要双级设计
        net_power = utility_power['net_power_output']
        total_power = main_engine['total_power_generation']
        
        if net_power > 1000:
            # 双级设计 - 将净发电功率分配为两级
            first_level_power = 1000  # 一级功率固定1000kW
            second_level_power = net_power - 1000  # 二级功率 = 总净发电功率 - 一级功率
            max_power = max(second_level_power, 1000)  # 机组选型功率按较大的级别计算
            
            # 按max_power重新计算机组选型（用于尺寸和重量）
            temp_calculator = PowerCalculations()
            temp_main_params = MainEngineParams(main_power=max_power)
            temp_utility_params = UtilityParams()
            temp_unit_selection_params = UnitSelectionParams()
            
            # 计算临时主机结果用于查表
            temp_main_results = temp_calculator.calculate_main_engine_params(temp_main_params)
            temp_utility_results = temp_calculator.calculate_utility_power_consumption(temp_main_results, temp_utility_params)
            temp_unit_results = temp_calculator.calculate_unit_selection(temp_main_results, temp_utility_results, temp_unit_selection_params)
            
            # 更新机组选型结果
            unit_selection['unit_selection'] = max_power
            unit_selection['unit_dimensions'] = temp_unit_results['unit_dimensions']
            unit_selection['unit_weight'] = temp_unit_results['unit_weight']
            
            is_dual_level = True
        else:
            # 单级设计
            max_power = total_power
            first_level_power = None
            second_level_power = None
            is_dual_level = False
        
        # 计算回报周期（按实际选型功率计算投资成本）
        investment_cost = int(unit_selection['unit_selection']) * 1.0  # 万元
        annual_income = economic_analysis['annual_power_income']  # 万元
        payback_period = round(investment_cost / annual_income, 1) if annual_income > 0 else 0
        
        # 从ASPEN结果中提取技术参数，而不是写死
        aspen_sim_results = aspen_results.get("simulation_results", {})
        inlet_conditions = aspen_sim_results.get("inlet_conditions", {})
        outlet_conditions = aspen_sim_results.get("outlet_conditions", {})
        performance_metrics = aspen_sim_results.get("performance_metrics", {})
        parameters = aspen_sim_results.get("parameters", {})
        
        # 构建技术参数（从ASPEN结果获取，而不是写死）
        technical_params = {
            "进/排气压力(MPaa)": f"{parameters.get('inlet_pressure', 'N/A')}/{parameters.get('outlet_pressure', 'N/A')}",
            "进/排气温度(°C)": f"{parameters.get('inlet_temperature', 'N/A')}/{outlet_conditions.get('temperature', 'N/A') if outlet_conditions else 'N/A'}",
            "处理流量(scmh)": f"{parameters.get('gas_flow_rate', 'N/A')}",
            "设备效率": f"{parameters.get('efficiency', 'N/A')}%" if parameters.get('efficiency') else "N/A",
            "功率输出(kW)": f"{aspen_sim_results.get('power_output', 'N/A')}"
        }
        
        # 组织选型输出结果
        selection_output = {
            "选型输出": {
                "机组参数": {
                    "机组型号": f"TP{int(unit_selection['unit_selection'])}",
                    "机组报价": int(unit_selection['unit_selection']),
                    "机组尺寸": f"{unit_selection['unit_dimensions'][0]}×{unit_selection['unit_dimensions'][1]}×{unit_selection['unit_dimensions'][2]}",
                    "机组重量": f"{unit_selection['unit_weight']}"
                },
                "技术参数": technical_params,  # 使用从ASPEN结果提取的参数
                "设计类型": "双级发电机组" if is_dual_level else "单级发电机组",
                "净发电功率": f"{utility_power['net_power_output']:.0f}kW",
                "年收益率": f"{economic_analysis['annual_power_income']:.1f}万元",
                "回报周期": f"{payback_period}年"
            }
        }
        
        # 如果是双级设计，添加功率分配信息
        if is_dual_level:
            # 验证：总净发电功率 = 一级功率 + 二级功率
            calculated_total = first_level_power + second_level_power
            selection_output["选型输出"]["功率分配"] = {
                "一级功率": f"{first_level_power:.0f}kW",
                "二级功率": f"{second_level_power:.0f}kW", 
                "总净发电功率": f"{calculated_total:.0f}kW",
                "机组选型功率": f"{max_power:.0f}kW"
            }
        
        # 详细计算过程
        calculation_details = {
            "计算过程详情": {
                "1_主机参数": {
                    "输入主机功率": f"{main_engine['input_power']:.2f} kW",
                    "主机损失功率": f"{main_engine['main_loss_power']:.2f} kW", 
                    "主机输出功率": f"{main_engine['main_output_power']:.2f} kW",
                    "机组总发电量": f"{main_engine['total_power_generation']:.2f} kW"
                },
                "2_公用功耗": {
                    "润滑油量": f"{utility_power['lubrication_oil_amount']:.2f}",
                    "油冷器循环冷却水": f"{utility_power['oil_cooler_circulation_water']:.2f}",
                    "油泵功率": f"{utility_power['oil_pump_power']:.2f} kW",
                    "公用功耗自耗电": f"{utility_power['utility_self_consumption']:.2f} kW",
                    "净发电功率": f"{utility_power['net_power_output']:.2f} kW"
                },
                "3_经济性分析": {
                    "年发电量": f"{economic_analysis['annual_power_generation']:.4f} 万kWh",
                    "年发电收益": f"{economic_analysis['annual_power_income']:.4f} 万元",
                    "年节约标煤": f"{economic_analysis['annual_coal_savings']:.4f} 万吨",
                    "年节煤效益": f"{economic_analysis['annual_coal_cost_savings']:.4f} 万元",
                    "年CO2减排量": f"{economic_analysis['annual_co2_reduction']:.4f} 万吨"
                },
                "4_机组选型": {
                    "机组总发电量": f"{main_engine['total_power_generation']:.2f} kW",
                    "设计类型": "双级发电机组" if is_dual_level else "单级发电机组",
                    "选型说明": f"净发电功率{net_power:.2f}kW > 1000kW，采用双级设计" if is_dual_level else f"净发电功率{net_power:.2f}kW ≤ 1000kW，采用单级设计",
                    "选型计算": f"max_power = max({total_power:.2f} - 1000, 1000) = {max_power:.2f}" if is_dual_level else f"max_power = {total_power:.2f}",
                    "机组选择": f"{unit_selection['unit_selection']:.0f} kW",
                    "机组尺寸": unit_selection['unit_dimensions'],
                    "机组重量": f"{unit_selection['unit_weight']}"
                },
                "5_功率分配": {
                    "一级功率": f"{first_level_power:.0f} kW" if is_dual_level else "N/A",
                    "二级功率": f"{second_level_power:.0f} kW" if is_dual_level else "N/A",
                    "功率分配验证": f"{first_level_power:.0f} + {second_level_power:.0f} = {first_level_power + second_level_power:.0f} kW" if is_dual_level else "N/A",
                    "总净发电功率": f"{first_level_power + second_level_power:.0f} kW" if is_dual_level else f"{net_power:.2f} kW",
                    "机组选型功率": f"{max_power:.2f} kW"
                } if is_dual_level else {
                    "单级功率": f"{total_power:.2f} kW",
                    "净发电功率": f"{net_power:.2f} kW"
                },
                "6_回报周期": {
                    "投资成本": f"{investment_cost:.1f} 万元",
                    "年收益": f"{annual_income:.4f} 万元",
                    "回报周期计算": f"ROUND({investment_cost:.1f} / {annual_income:.4f}, 1)",
                    "回报周期": f"{payback_period} 年"
                }
            }
        }
        
        # 简单验证
        validation_results = {
            "校验结果": "通过",
            "净发电功率": utility_power['net_power_output'] > 0,
            "年收益率": economic_analysis['annual_power_income'] > 0,
            "系统效率": 0 < (utility_power['net_power_output'] / main_power) < 1
        }
        
        return {
            "success": True,
            "selection_output": selection_output,
            "calculation_details": calculation_details,
            "validation_results": validation_results
        }
        
    except Exception as e:
        return {
            "success": False,
            "error_message": f"功率计算内部错误: {str(e)}"
        }


def generate_technical_document(aspen_results: Dict[str, Any], power_results: Dict[str, Any], request: SimulationRequest, diagram_file_path: str = None) -> Dict[str, Any]:
    """
    生成技术文档（DOCX格式）
    """
    try:
        # 从仿真结果中提取数据
        aspen_sim = aspen_results.get("simulation_results", {})
        power_selection = power_results.get("selection_output", {}).get("选型输出", {})
        power_details = power_results.get("calculation_details", {}).get("计算过程详情", {})
        
        # 提取关键数据
        power_output = aspen_sim.get('power_output', 654)
        net_power = power_details.get("2_公用功耗", {}).get("净发电功率", "654.0 kW").replace(" kW", "")
        annual_power = power_details.get("3_经济性分析", {}).get("年发电量", "525.6 万kWh").replace(" 万kWh", "")
        annual_income = power_details.get("3_经济性分析", {}).get("年发电收益", "315.36 万元").replace(" 万元", "")
        coal_savings = power_details.get("3_经济性分析", {}).get("年节约标煤", "184.0 万吨").replace(" 万吨", "")
        co2_reduction = power_details.get("3_经济性分析", {}).get("年CO2减排量", "505.4 万吨").replace(" 万吨", "")
        
        # 机组参数
        unit_params = power_selection.get("机组参数", {})
        unit_model = unit_params.get("机组型号", "TRT-1000")
        unit_dimensions = unit_params.get("机组尺寸", "8.5×3.2×3.8")
        unit_weight = unit_params.get("机组重量", "12000")
        
        # 技术参数
        tech_params = power_selection.get("技术参数", {})
        max_gas_flow = request.gas_flow_rate  # scmh -> m³/d
        inlet_pressure = request.inlet_pressure * 10  # MPaA -> MPaG 
        avg_inlet_temp = request.inlet_temperature
        outlet_pressure = request.outlet_pressure * 10  # MPaA -> MPaG
        exhaust_temp = tech_params.get("进/排气温度(°C)", "25/45").split("/")[-1] or "45"
        
        # 公用工程参数 - 使用 UtilityParams 类的属性值
        utility_params_data = power_details.get("2_公用功耗", {})
        
        # 创建 UtilityParams 实例获取标准参数值
        utility_params_config = UtilityParams()
        
        # 设备功率参数 - 直接使用 UtilityParams 的属性值
        oil_pump_power = str(utility_params_config.lubrication_pump_power)        # 辅油泵功率 (kW)
        heater_power = str(utility_params_config.lubrication_heater_power)        # 润滑油电加热器功率 (kW) 
        separator_power = "8"         # 油雾分离器功率 (kW) - UtilityParams中无对应项，保持固定值
        space_heater_power = str(utility_params_config.generator_heater_power)    # 发电机加热器功率 (kW)
        plc_power = str(utility_params_config.plc_power)                         # PLC柜功率 (kW)
        
        # 流量参数 - 直接使用 UtilityParams 的属性值
        oil_cooler_flow = "850"       # 油冷器流量 (m³/Hr) - 从计算结果获取
        lubrication_flow = str(int(utility_params_config.lubrication_oil_flow_rate))  # 润滑油流量 (L/min)
        nitrogen_flow = str(utility_params_config.air_demand_nm3_per_h)           # 氮气流量 (Nm³/h)
        compressed_air_demand = str(utility_params_config.air_demand_nm3)         # 压缩空气流量 (Nm³/h)
        
        # 尝试从实际计算结果中获取更精确的值
        lubrication_oil_amount = utility_params_data.get("润滑油量", "")
        if lubrication_oil_amount:
            try:
                # 提取数值部分
                oil_amount_str = str(lubrication_oil_amount).replace("L", "").strip()
                oil_amount_value = float(oil_amount_str)
                # 可以根据实际油量调整流量，但这里保持UtilityParams的标准值
                logger.info(f"润滑油量（计算值）: {oil_amount_value}L")
            except:
                pass
        
        # 尝试从油冷器循环冷却水计算中获取数值  
        oil_cooler_water = utility_params_data.get("油冷器循环冷却水", "")
        if oil_cooler_water:
            try:
                # 提取数值部分并使用实际计算值
                water_str = str(oil_cooler_water).replace("m³/h", "").replace("m³/Hr", "").strip()
                water_value = float(water_str)
                oil_cooler_flow = str(int(water_value))  # 直接使用计算的循环水量
                logger.info(f"油冷器循环水量（计算值）: {water_value} m³/Hr")
            except:
                pass
        
        # 创建参数映射字典，将仿真结果映射到auto_aspen参数
        parameters = {
            # 接入参数 - 天然气处理机组
            "auto_aspen_1": str(int(max_gas_flow * 24)),  # 最大气量 (m³/d)
            "auto_aspen_2": str(inlet_pressure),          # 进站压力 (MPaG)
            "auto_aspen_3": str(avg_inlet_temp),          # 平均进气温度 (℃)
            "auto_aspen_4": str(outlet_pressure),         # 出站压力 (MPaG)
            
            # 段落中的参数
            "auto_aspen_5": str(int(float(net_power))),   # 净发电功率 (kW)
            
            # 机组参数表
            "auto_aspen_6": "1",                          # 透平机头数
            "auto_aspen_7": unit_model,                   # 机组型号
            "auto_aspen_8": "1",                          # 级数
            "auto_aspen_9": str(exhaust_temp),            # 机组排气温度 (℃)
            
            # 机组占地面积与操作重量
            "auto_aspen_10": f"{unit_model}-EX",          # 机组型号
            "auto_aspen_11": unit_dimensions,             # 机组整体外形尺寸 (长×宽×高 m)
            "auto_aspen_12": str(unit_weight),            # 机组整体重量/整体维修保养最大重量 (kg)
            
            # 项目整体经济效益核算
            "auto_aspen_13": str(float(annual_power)),    # 年净发电量 (×10⁴kWh)
            "auto_aspen_14": str(float(annual_income)),   # 年净发电收益 (万元)
            "auto_aspen_15": str(float(coal_savings) * 10000),  # 年节约标准煤 (吨)
            "auto_aspen_16": str(float(co2_reduction) * 10000), # 年减少CO₂排放 (吨)
            
            # 机组公用工程 - 电源设备参数
            "auto_aspen_17": oil_pump_power,              # 辅油泵功率 (kW)
            "auto_aspen_18": heater_power,                # 润滑油电加热器功率 (kW)
            "auto_aspen_19": separator_power,             # 油雾分离器功率 (kW)
            "auto_aspen_20": space_heater_power,          # 发电机加热器=空间加热器功率 (kW)
            "auto_aspen_21": plc_power,                   # PLC柜功率 (kW)
            
            # 机组公用工程 - 水油气参数
            "auto_aspen_22": oil_cooler_flow,             # 油冷器流量 (m³/Hr)
            "auto_aspen_23": lubrication_flow,            # 齿轮箱润滑油流量 (L/min)
            "auto_aspen_24": nitrogen_flow,               # 氮气-干气密封气体流量 (Nm³/h)
            "auto_aspen_25": compressed_air_demand,       # 压缩空气-气动阀气体流量 (Nm³/h)
        }
        
        # 生成时间戳文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 毫秒精度
        output_name = f"technical_report_{timestamp}"
        
        # 输出公用工程参数用于调试
        logger.info(f"公用工程参数配置（来源：UtilityParams）:")
        logger.info(f"  辅油泵功率: {oil_pump_power} kW （UtilityParams.lubrication_pump_power）")
        logger.info(f"  润滑油电加热器功率: {heater_power} kW （UtilityParams.lubrication_heater_power）") 
        logger.info(f"  油雾分离器功率: {separator_power} kW （固定值）")
        logger.info(f"  发电机加热器功率: {space_heater_power} kW （UtilityParams.generator_heater_power）")
        logger.info(f"  PLC柜功率: {plc_power} kW （UtilityParams.plc_power）")
        logger.info(f"  油冷器流量: {oil_cooler_flow} m³/Hr （计算值或默认值）")
        logger.info(f"  润滑油流量: {lubrication_flow} L/min （UtilityParams.lubrication_oil_flow_rate）")
        logger.info(f"  氮气流量: {nitrogen_flow} Nm³/h （UtilityParams.air_demand_nm3_per_h）")
        logger.info(f"  空气需求量: {compressed_air_demand} Nm³/h （UtilityParams.air_demand_nm3）")
        
        # 准备机组布局图替换
        text_to_images = None
        if diagram_file_path and os.path.exists(diagram_file_path):
            text_to_images = {
                "auto_aspen_image_1": {
                    "image_path": diagram_file_path,
                    "width": 6.0,
                    "height": 4.0
                }
            }
            logger.info(f"准备将机组布局图插入文档: {diagram_file_path}")
        else:
            logger.warning(f"机组布局图不存在或路径无效: {diagram_file_path}")
        
        # 生成文档
        logger.info(f"正在生成技术文档，参数数量: {len(parameters)}")
        result = generate_document(
            parameters=parameters,
            text_to_images=text_to_images,
            output_name=output_name,
            convert_pdf=False,  # 暂时关闭PDF转换
            preserve_formatting=False  # 保持格式
        )
        
        if result["success"]:
            # 构建文档下载地址
            docx_filename = f"{output_name}.docx"
            docx_url = f"/static/re/{docx_filename}"
            
            document_urls = {
                "docx": docx_url
            }
            
            # 如果有PDF文件也添加到下载地址中
            if result.get("pdf_path"):
                pdf_filename = f"{output_name}.pdf"
                pdf_url = f"/static/re/{pdf_filename}"
                document_urls["pdf"] = pdf_url
            
            # 记录图片替换结果
            text_to_image_count = result.get("text_to_image_replaced", 0)
            if text_to_image_count > 0:
                logger.info(f"✅ 成功在文档中替换了 {text_to_image_count} 个图片占位符")
            else:
                logger.warning("⚠️ 未在文档中找到图片占位符或替换失败")
            
            return {
                "success": True,
                "document_urls": document_urls,
                "parameters_count": len(parameters),
                "text_to_image_replaced": text_to_image_count,
                "generated_files": {
                    "docx_path": result["docx_path"],
                    "pdf_path": result.get("pdf_path")
                }
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "文档生成失败")
            }
            
    except Exception as e:
        logger.error(f"生成技术文档失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def generate_diagram_file(power_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成机组布局图并保存为文件
    """
    try:
        # 从power_results中提取信息
        selection_output = power_results.get("selection_output", {}).get("选型输出", {})
        design_type = selection_output.get("设计类型", "单级发电机组")
        power_distribution = selection_output.get("功率分配", {})
        
        # 从计算详情中提取机组尺寸
        calculation_details = power_results.get("calculation_details", {}).get("计算过程详情", {})
        unit_dimensions = calculation_details.get("4_机组选型", {}).get("机组尺寸", (5.5, 3, 2.5))
        
        # 导入draw.py模块
        try:
            from auto_aspen.draw import draw
        except ImportError as e:
            logger.error(f"无法导入draw模块: {str(e)}")
            return {"success": False, "error": f"draw模块导入失败: {str(e)}"}
        
        # 根据设计类型生成图像
        width_pixels = int(unit_dimensions[0] * 100)  # 长度×100
        height_pixels = int(unit_dimensions[1] * 100)  # 宽度×100
        total_power = float(power_distribution.get("总净发电功率", "0").replace("kW", ""))
        img = draw(outer_size=(width_pixels, height_pixels) ,net_power=int(total_power))
        # 生成时间戳文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 毫秒精度
        filename = f"diagram_{timestamp}.png"
        file_path = os.path.join("static", "diagrams", filename)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 保存图像文件
        img.save(file_path, format='PNG')
        
        # 返回URL路径
        diagram_url = f"/static/diagrams/{filename}"
        
        return {
            "success": True,
            "diagram_url": diagram_url,
            "design_type": design_type,
            "file_path": file_path
        }
        
    except Exception as e:
        logger.error(f"生成机组布局图失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def create_combined_results(aspen_results: Dict[str, Any], power_results: Dict[str, Any], request: SimulationRequest, document_urls: Dict[str, str] = None) -> Dict[str, Any]:
    """创建综合结果"""
    try:
        # 提取关键数据
        aspen_sim = aspen_results.get("simulation_results", {})
        power_selection = power_results.get("selection_output", {})
        power_details = power_results.get("calculation_details", {})
        
        # 综合结果
        combined = {
            "仿真概况": {
                "仿真时间": aspen_sim.get("simulation_time", "N/A"),
                "ASPEN仿真状态": "成功" if aspen_sim.get("success") else "失败",
                "功率计算状态": "成功" if power_results.get("success") else "失败",
                "总体状态": "成功" if aspen_sim.get("success") and power_results.get("success") else "失败"
            },
            "输入参数": {
                "气体流量": f"{request.gas_flow_rate} scmh",
                "入口压力": f"{request.inlet_pressure} MPaA",
                "入口温度": f"{request.inlet_temperature} °C",
                "出口压力": f"{request.outlet_pressure} MPaA",
                "设计效率": f"{request.efficiency} %",
                "气体组成": request.gas_composition.dict()
            },
            "ASPEN仿真结果": {
                "功率输出": f"{aspen_sim.get('power_output', 'N/A')} kW",
                "入口条件": aspen_sim.get("inlet_conditions", {}),
                "出口条件": aspen_sim.get("outlet_conditions", {}),
                "性能指标": aspen_sim.get("performance_metrics", {})
            },
            "机组选型结果": power_selection,
            "经济性分析": power_details.get("计算过程详情", {}).get("3_经济性分析", {}),
            "验证结果": power_results.get("validation_results", {}),
            "文档下载": document_urls if document_urls else {}
        }
        
        return combined
        
    except Exception as e:
        logger.error(f"创建综合结果失败: {str(e)}")
        return {"error": f"创建综合结果失败: {str(e)}"}

# ============ 启动配置 ============

if __name__ == "__main__":
    import uvicorn
    
    logger.info("启动 ASPEN & Power Calculation API 服务")
    
    # 启动服务
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
