#!/usr/bin/env python3
"""
中国社交平台并行模拟预设脚本
同时运行多个中国社交平台模拟，读取相同的配置文件

支持平台:
- 微信公众号 (wechat)
- 微博 (weibo)
- 抖音 (douyin)
- 快手 (kuaishou)
- 小红书 (xiaohongshu)
- 微信视频号 (shipinhao)

使用方式:
    python run_chinese_parallel_simulation.py --config simulation_config.json
    python run_chinese_parallel_simulation.py --config simulation_config.json --max-rounds 40

日志结构:
    sim_xxx/
    ├── wechat/
    │   └── actions.jsonl    # 微信公众号平台动作日志
    ├── weibo/
    │   └── actions.jsonl    # 微博平台动作日志
    ├── douyin/
    │   └── actions.jsonl    # 抖音平台动作日志
    ├── kuaishou/
    │   └── actions.jsonl    # 快手平台动作日志
    ├── xiaohongshu/
    │   └── actions.jsonl    # 小红书平台动作日志
    ├── shipinhao/
    │   └── actions.jsonl    # 微信视频号平台动作日志
    ├── simulation.log       # 主模拟进程日志
    └── run_state.json       # 运行状态（API 查询用）
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


def get_enabled_platforms(config: dict) -> list:
    """从配置中获取启用的平台列表"""
    platform_config = config.get("platform_config", {})

    enabled = []
    for platform_name in CHINESE_PLATFORMS.keys():
        # 检查是否启用
        if platform_config.get(f"enable_{platform_name}", False):
            enabled.append(platform_name)
        # 也检查通用配置
        if platform_config.get(platform_name, {}).get("enabled", False):
            enabled.append(platform_name)

    # 如果没有明确启用，默认启用所有中国平台
    if not enabled:
        enabled = list(CHINESE_PLATFORMS.keys())

    return enabled


def create_platform_simulators(config: dict, simulation_dir: str, enabled_platforms: list):
    """创建平台模拟器实例"""
    simulators = {}

    for platform_name in enabled_platforms:
        simulator_class = CHINESE_PLATFORMS.get(platform_name)
        if simulator_class:
            try:
                simulator = simulator_class(config, simulation_dir)
                simulators[platform_name] = simulator
                logger.info(f"已创建 {platform_name} 模拟器")
            except Exception as e:
                logger.error(f"创建 {platform_name} 模拟器失败: {e}")

    return simulators


async def run_platform_simulator(
    platform_name: str,
    simulator,
    action_logger: ActionLogger,
    max_rounds: int,
    simulation_dir: str
):
    """运行单个平台模拟"""
    platform_dir = os.path.join(simulation_dir, platform_name)
    os.makedirs(platform_dir, exist_ok=True)

    # 创建平台专用的动作日志
    platform_action_logger = ActionLogger(log_path=platform_dir)

    def platform_logger(msg):
        logger.info(f"[{platform_name.upper()}] {msg}")

    try:
        platform_logger("开始模拟...")
        result = await simulator.run_simulation(
            action_logger=platform_action_logger,
            main_logger=type('Log', (), {'info': platform_logger})(),
            max_rounds=max_rounds
        )
        platform_logger(f"模拟完成: {result.total_actions} 个动作")
        return result
    except Exception as e:
        platform_logger(f"模拟出错: {e}")
        import traceback
        traceback.print_exc()
        return None


async def run_parallel_simulation(config_path: str, max_rounds: int = None):
    """运行并行模拟"""
    # 加载配置
    config = load_config(config_path)
    simulation_dir = os.path.dirname(config_path)

    logger.info("=" * 60)
    logger.info("中国社交平台并行模拟")
    logger.info("=" * 60)

    # 获取启用的平台
    enabled_platforms = get_enabled_platforms(config)
    logger.info(f"启用的平台: {enabled_platforms}")

    if not enabled_platforms:
        logger.warning("没有启用的中国平台，将使用默认配置")
        enabled_platforms = list(CHINESE_PLATFORMS.keys())

    # 创建平台模拟器
    simulators = create_platform_simulators(config, simulation_dir, enabled_platforms)

    if not simulators:
        logger.error("没有成功创建任何模拟器")
        return

    # 创建主动作日志
    main_action_logger = ActionLogger(log_path=simulation_dir)

    # 启动IPC服务器
    ipc_server = SimulationIPCServer(simulation_dir)
    ipc_server.start()

    # 初始化状态文件
    state = SimulationState(simulation_dir=simulation_dir)
    state.init(
        simulation_id=os.path.basename(simulation_dir).replace("sim_", ""),
        total_rounds=max_rounds or 100,
        platforms=list(simulators.keys())
    )

    # 注册清理函数
    def cleanup():
        logger.info("清理资源...")
        ipc_server.stop()
        state.update_status("stopped")

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda s, f: cleanup())
    signal.signal(signal.SIGTERM, lambda s, f: cleanup())

    # 并行运行所有平台模拟
    logger.info("开始并行模拟...")

    tasks = []
    for platform_name, simulator in simulators.items():
        task = run_platform_simulator(
            platform_name=platform_name,
            simulator=simulator,
            action_logger=main_action_logger,
            max_rounds=max_rounds,
            simulation_dir=simulation_dir
        )
        tasks.append(task)

    # 等待所有平台完成
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 统计结果
    total_actions = 0
    for platform_name, result in zip(simulators.keys(), results):
        if result and hasattr(result, 'total_actions'):
            total_actions += result.total_actions
            logger.info(f"{platform_name}: {result.total_actions} 个动作")
        else:
            logger.warning(f"{platform_name}: 模拟失败或无结果")

    # 更新状态
    state.update_status("completed")
    state.update_stats(
        total_actions=total_actions,
        platforms_completed=list(simulators.keys())
    )

    logger.info("=" * 60)
    logger.info(f"所有平台模拟完成! 总动作数: {total_actions}")
    logger.info("=" * 60)

    # 保持运行，等待命令
    logger.info("模拟完成，进入命令等待模式...")
    ipc_server.wait_for_commands()


def main():
    parser = argparse.ArgumentParser(description="中国社交平台并行模拟")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--max-rounds", type=int, default=None, help="最大模拟轮数")
    parser.add_argument("--no-wait", action="store_true", help="完成后立即退出")

    args = parser.parse_args()

    # 运行模拟
    asyncio.run(run_parallel_simulation(args.config, args.max_rounds))


if __name__ == "__main__":
    main()
