#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API服务启动脚本
用于启动ASPEN & Power Calculation API服务
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def create_logs_directory():
    """创建日志目录"""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logs_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ 创建日志目录: {logs_dir.absolute()}")
    else:
        print(f"📁 日志目录已存在: {logs_dir.absolute()}")

def check_dependencies():
    """检查依赖是否安装"""
    try:
        import fastapi
        import uvicorn
        import pydantic
        import loguru
        print("✅ 所有必要依赖已安装")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        return False

def start_api_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = True, workers=1):
    """启动API服务器"""
    try:
        # 显示环境配置
        apwz_file_path = os.getenv("ASPEN_APWZ_FILE_PATH", "./models/RE-Expander.apwz")
        
        print(f"🚀 启动API服务器...")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Reload: {reload}")
        print(f"   APWZ文件: {apwz_file_path}")
        print(f"   API文档: http://{host}:{port}/docs")
        print(f"   健康检查: http://{host}:{port}/health")
        
        # 检查APWZ文件是否存在
        if not Path(apwz_file_path).exists():
            print(f"⚠️  警告: APWZ文件不存在: {apwz_file_path}")
            print("   请确保文件存在或设置正确的环境变量 ASPEN_APWZ_FILE_PATH")
        else:
            print(f"✅ APWZ文件存在: {apwz_file_path}")
        
        print("\n按 Ctrl+C 停止服务\n")
        
        # 使用uvicorn启动服务
        import uvicorn
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
            workers=workers
        )
        
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="启动ASPEN & Power Calculation API服务")
    parser.add_argument("--host", default="0.0.0.0", help="服务器主机地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口 (默认: 8000)")
    parser.add_argument("--no-reload", action="store_true", help="禁用自动重载")
    parser.add_argument("--workers", type=int, default=10, help="工作进程数 (默认: 10)")
    parser.add_argument("--apwz-file", help="APWZ文件路径 (会设置环境变量ASPEN_APWZ_FILE_PATH)")
    
    args = parser.parse_args()
    
    # 如果提供了apwz-file参数，设置环境变量
    if args.apwz_file:
        os.environ["ASPEN_APWZ_FILE_PATH"] = args.apwz_file
        print(f"🔧 设置环境变量 ASPEN_APWZ_FILE_PATH = {args.apwz_file}")
    
    print("=" * 60)
    print("       ASPEN & Power Calculation API 启动器")
    print("=" * 60)
    
    # 创建日志目录
    create_logs_directory()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查main.py是否存在
    if not Path("main.py").exists():
        print("❌ 找不到main.py文件")
        sys.exit(1)
    
    print("\n" + "-" * 60 + "\n")
    
    # 启动服务器
    start_api_server(
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        workers=args.workers
    )

if __name__ == "__main__":
    main() 