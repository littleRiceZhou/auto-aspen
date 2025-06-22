#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASPEN Plus 自动化测试脚本
测试 PyASPENPlus 类的各种功能
"""

import os
import sys
import json
import time
from pathlib import Path
from loguru import logger

# 添加项目路径
sys.path.insert(0, os.path.abspath('.'))

from auto_aspen import PyASPENPlus

# 配置日志
logger.remove()  # 移除默认处理器
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")


def main():
    """主函数"""
    logger.info("PyASPENPlus 测试脚本启动")

    pyaspen = PyASPENPlus()
    
    result = pyaspen.run("./models/test.bkp", return_json=True, visible=False)
    print(result)


if __name__ == "__main__":
    exit(main())
