#!/usr/bin/env python3
"""
RAG检索系统启动脚本
"""

import uvicorn
import sys
import os

def main():
    print("🚀 启动RAG检索系统...")
    print("📍 访问地址: http://localhost:8000")
    print("📖 API文档: http://localhost:8000/docs")
    print("⚡ 按Ctrl+C停止服务")
    print("-" * 50)
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()