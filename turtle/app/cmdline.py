#!/usr/bin/env python3
"""
命令行入口点
用于启动 FastAPI 应用
"""
import argparse
import sys

try:
    import uvicorn
except ImportError:
    print("错误: 需要安装 uvicorn 库")
    print("请运行: pip install uvicorn[standard]")
    sys.exit(1)

from app.config import settings
from app.utils.logger import logger


def main():
    """主函数，解析命令行参数并启动应用"""
    parser = argparse.ArgumentParser(
        description="启动股票数据查询服务和量化选股系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  myturtle                    # 使用默认配置启动
  myturtle --host 0.0.0.0     # 指定主机地址
  myturtle --port 8000        # 指定端口
  myturtle --reload           # 开发模式，自动重载
  myturtle --workers 4        # 使用4个工作进程
        """
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="绑定主机地址 (默认: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="绑定端口号 (默认: 8000)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="开发模式：代码变更时自动重载 (默认: False)"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="工作进程数量，仅在生产模式有效 (默认: 1)"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="日志级别 (默认: info)"
    )
    
    parser.add_argument(
        "--access-log",
        action="store_true",
        default=True,
        help="启用访问日志 (默认: True)"
    )
    
    parser.add_argument(
        "--no-access-log",
        action="store_false",
        dest="access_log",
        help="禁用访问日志"
    )
    
    args = parser.parse_args()
    
    # 显示启动信息
    logger.info("=" * 60)
    logger.info(f"启动 {settings.APP_NAME}")
    logger.info("=" * 60)
    logger.info(f"主机: {args.host}")
    logger.info(f"端口: {args.port}")
    logger.info(f"重载模式: {args.reload}")
    if args.workers:
        logger.info(f"工作进程数: {args.workers}")
    logger.info(f"日志级别: {args.log_level}")
    logger.info("=" * 60)
    
    # 配置 uvicorn
    uvicorn_config = {
        "app": "app.main:app",
        "host": args.host,
        "port": args.port,
        "reload": args.reload,
        "log_level": args.log_level,
        "access_log": args.access_log,
    }
    
    # 如果指定了 workers，添加到配置中（reload 模式下不能使用 workers）
    if args.workers and not args.reload:
        uvicorn_config["workers"] = args.workers
    
    # 启动应用
    try:
        uvicorn.run(**uvicorn_config)
    except KeyboardInterrupt:
        logger.info("应用已停止")
    except Exception as e:
        logger.error(f"启动应用失败: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
