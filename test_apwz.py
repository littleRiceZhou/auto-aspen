#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APWZ文件仿真测试器 - 面向对象版本
提供APWZ文件加载、参数设置和仿真运行的完整功能
"""

import os
import sys
from auto_aspen import PyASPENPlus, SimulationParameters, SimulationResult, APWZSimulator
from loguru import logger


def main():
    """主函数"""
    logger.info("开始面向对象的 APWZ 文件仿真测试")
    
    # 设置日志级别
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # 检查文件是否存在
    apwz_file = "./models/RE-Expander.apwz"
    if not os.path.exists(apwz_file):
        logger.error(f"文件 {apwz_file} 不存在")
        return False
    
    try:
        # 加载参数
        parameters = SimulationParameters(**{
            'gas_flow_rate': 33333.333333,  # scmh
            'inlet_pressure': 0.80,         # MPaA (8.0 bara, 与图片匹配)
            'inlet_temperature': 20.0,      # °C (与图片中显示的20°C匹配，不是30°C)
            'outlet_pressure': 0.30,        # MPaA (3.0 bara, 与图片匹配)
            'gas_composition': {             # 与图片中100% CH4匹配
                'CH4': 100,
                'C2H6': 0,
                'C3H8': 0,
                'C4H10': 0,
                'N2': 0,
                'CO2': 0,
                'H2S': 0,
            },
            'efficiency': 85,               # % (与图片中0.85效率匹配)
        })
        parameters.log_parameters()
        
        # 使用上下文管理器运行仿真
        with APWZSimulator(apwz_file) as simulator:
            # 运行完整仿真
            result = simulator.run_full_simulation(parameters)
            
            # 输出结果
            result.log_results()
            
            # 保存到JSON文件
            # result.save_to_json()
            
            success = result.success
            if success:
                logger.info("✅ 面向对象仿真测试成功完成")
            else:
                logger.error("❌ 面向对象仿真测试失败")
            
            return success
            
    except Exception as e:
        logger.error(f"主函数执行失败: {str(e)}")
        return False


if __name__ == "__main__":
    main() 