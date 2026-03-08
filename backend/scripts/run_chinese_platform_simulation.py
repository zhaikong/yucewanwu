#!/usr/bin/env python3
"""
中国社交平台模拟脚本
运行单个中国社交平台的模拟

支持平台:
- 微信公众号 (wechat)
- 微博 (weibo)
- 抖音 (douyin)
- 快手 (kuaishou)
- 小红书 (xiaohongshu)
- 微信视频号 (shipinhao)

使用方式:
    python run_chinese_platform_simulation.py --config simulation_config.json --platform wechat
    python run_chinese_platform_simulation.py --config simulation_config.json --platform douyin --max-rounds 40
"""

import sys
import os
import argparse
import asyncio
import json
import signal
import atexit
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入中国平台模拟器
from scripts.chinese_platform_simulator import (
    WechatSimulator,
    WeiboSimulator,
    DouyinSimulator,
    KuaishouSimulator,
    XiaohongshuSimulator,
    ShipinhaoSimulator,
)

# 导入日志和动作记录
from scripts.action_logger import ActionLogger
from app.services.simulation_ipc import SimulationIPCServer
from app.services.simulation_manager import SimulationState

# 配置日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# 平台配置
CHINESE_PLATFORMS = {
    "wechat": WechatSimulator,
    "weibo": WeiboSimulator,
    "douyin": DouyinSimulator,
    "kuaishou": KuaishouSimulator,
    "xiaohongshu": XiaohongshuSimulator,
    "shipinhao": ShipinhaoSimulator,
}


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def run_single_platform(
    platform_name: str,
    config: dict,
    simulation_dir: str,
    max_rounds: int = None
):
    """运行单个平台模拟"""
    logger.info("=" * 60)
    logger.info(f"中国社交平台模拟: {platform_name}")
    logger.info("=" * 60)

    # 获取模拟器类
    simulator_class = CHINESE_PLATFORMS.get(platform_name)
    if not simulator_class:
        logger.error(f"未知平台: {platform_name}")
        return None

    # 创建平台目录
    platform_dir = os.path.join(simulation_dir, platform_name)
    os.makedirs(platform_dir, exist_ok=True)

    # 创建模拟器
    try:
        simulator = simulator_class(config, simulation_dir)
        logger.info(f"已创建 {platform_name} 模拟器")
    except Exception as e:
        logger.error(f"创建模拟器失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    # 创建动作日志
    action_logger = ActionLogger(log_path=platform_dir)

    def platform_logger(msg):
        logger.info(f"[{platform_name.upper()}] {msg}")

    # 日志包装器
    class LogWrapper:
        def info(self, msg):
            platform_logger(msg)

    try:
        platform_logger("开始模拟...")
        result = await simulator.run_simulation(
            action_logger=action_logger,
            main_logger=LogWrapper(),
            max_rounds=max_rounds
        )
        platform_logger(f"模拟完成: {result.total_actions} 个动作")
        return result
    except Exception as e:
        platform_logger(f"模拟出错: {e}")
        import traceback
        traceback.print_exc()
        return None


async def run_simulation(config_path: str, platform_name: str, max_rounds: int = None):
    """运行模拟"""
    # 加载配置
    config = load_config(config_path)
    simulation_dir = os.path.dirname(config_path)

    logger.info(f"配置文件: {config_path}")
    logger.info(f"平台: {platform_name}")

    # 验证平台
    if platform_name not in CHINESE_PLATFORMS:
        logger.error(f"未知平台: {platform_name}")
        logger.info(f"支持的平台: {list(CHINESE_PLATFORMS.keys())}")
        return

    # 启动IPC服务器
    ipc_server = SimulationIPCServer(simulation_dir)
    ipc_server.start()

    # 初始化状态文件
    state = SimulationState(simulation_dir=simulation_dir)
    state.init(
        simulation_id=os.path.basename(simulation_dir).replace("sim_", ""),
        total_rounds=max_rounds or 100,
        platforms=[platform_name]
    )

    # 注册清理函数
    def cleanup():
        logger.info("清理资源...")
        ipc_server.stop()
        state.update_status("stopped")

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda s, f: cleanup())
    signal.signal(signal.SIGTERM, lambda s, f: cleanup())

    # 运行模拟
    logger.info("开始模拟...")
    result = await run_single_platform(
        platform_name=platform_name,
        config=config,
        simulation_dir=simulation_dir,
        max_rounds=max_rounds
    )

    if result:
        total_actions = result.total_actions
        logger.info("=" * 60)
        logger.info(f"模拟完成! 总动作数: {total_actions}")
        logger.info("=" * 60)

        # 更新状态
        state.update_status("completed")
        state.update_stats(
            total_actions=total_actions,
            platforms_completed=[platform_name]
        )
    else:
        logger.error("模拟失败")
        state.update_status("failed")

    # 保持运行，等待命令
    logger.info("模拟完成，进入命令等待模式...")
    ipc_server.wait_for_commands()


def main():
    parser = argparse.ArgumentParser(description="中国社交平台模拟")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--platform", required=True, help="平台名称: wechat, weibo, douyin, kuaishou, xiaohongshu, shipinhao")
    parser.add_argument("--max-rounds", type=int, default=None, help="最大模拟轮数")
    parser.add_argument("--no-wait", action="store_true", help="完成后立即退出")

    args = parser.parse_args()

    # 运行模拟
    asyncio.run(run_simulation(args.config, args.platform, args.max_rounds))


if __name__ == "__main__":
    main()
