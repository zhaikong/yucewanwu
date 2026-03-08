#!/usr/bin/env python3
"""
中国社交平台模拟器
支持: 微信公众号、微博、抖音、快手、小红书、微信视频号
"""

import asyncio
import json
import os
import sqlite3
import random
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

# 平台配置
CHINESE_PLATFORMS = {
    "wechat": {
        "name": "微信公众号",
        "name_en": "WeChat Official Account",
        "profile_suffix": "wechat_profiles.json",
        "db_suffix": "wechat_simulation.db",
        "features": ["文章发布", "评论", "转发"],
        "post_format": "图文文章",
        "max_content_length": 20000,
    },
    "weibo": {
        "name": "微博",
        "name_en": "Weibo",
        "profile_suffix": "weibo_profiles.json",
        "db_suffix": "weibo_simulation.db",
        "features": ["发布微博", "评论", "点赞", "转发"],
        "post_format": "短文本+图片/视频",
        "max_content_length": 2000,
    },
    "douyin": {
        "name": "抖音",
        "name_en": "Douyin",
        "profile_suffix": "douyin_profiles.json",
        "db_suffix": "douyin_simulation.db",
        "features": ["发布视频", "评论", "点赞", "转发"],
        "post_format": "短视频",
        "max_content_length": 500,
    },
    "kuaishou": {
        "name": "快手",
        "name_en": "Kuaishou",
        "profile_suffix": "kuaishou_profiles.json",
        "db_suffix": "kuaishou_simulation.db",
        "features": ["发布视频", "评论", "点赞", "转发"],
        "post_format": "短视频",
        "max_content_length": 500,
    },
    "xiaohongshu": {
        "name": "小红书",
        "name_en": "Xiaohongshu",
        "profile_suffix": "xiaohongshu_profiles.json",
        "db_suffix": "xiaohongshu_simulation.db",
        "features": ["发布笔记", "评论", "点赞", "收藏"],
        "post_format": "图文笔记",
        "max_content_length": 5000,
    },
    "shipinhao": {
        "name": "微信视频号",
        "name_en": "WeChat Video Account",
        "profile_suffix": "shipinhao_profiles.json",
        "db_suffix": "shipinhao_simulation.db",
        "features": ["发布视频", "评论", "点赞", "转发"],
        "post_format": "短视频",
        "max_content_length": 1000,
    },
}


@dataclass
class PlatformSimulation:
    """平台模拟结果"""
    env: Any = None
    agent_graph: Any = None
    total_actions: int = 0


class ChinesePlatformSimulator:
    """中国平台模拟器基类"""

    def __init__(self, platform: str, config: Dict[str, Any], simulation_dir: str):
        self.platform = platform
        self.platform_config = CHINESE_PLATFORMS.get(platform, {})
        self.config = config
        self.simulation_dir = simulation_dir
        self.agent_profiles = []
        self.db_path = None

    def load_profiles(self) -> bool:
        """加载平台配置文件"""
        profile_path = os.path.join(
            self.simulation_dir,
            self.platform_config["profile_suffix"]
        )

        if not os.path.exists(profile_path):
            print(f"[{self.platform_config['name']}] 错误: Profile文件不存在: {profile_path}")
            return False

        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                self.agent_profiles = json.load(f)
            print(f"[{self.platform_config['name']}] 已加载 {len(self.agent_profiles)} 个配置文件")
            return True
        except Exception as e:
            print(f"[{self.platform_config['name']}] 加载配置文件失败: {e}")
            return False

    def init_database(self):
        """初始化数据库"""
        self.db_path = os.path.join(
            self.simulation_dir,
            self.platform_config["db_suffix"]
        )

        if os.path.exists(self.db_path):
            os.remove(self.db_path)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建表结构
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                agent_name TEXT,
                content TEXT NOT NULL,
                post_type TEXT DEFAULT 'original',
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                agent_name TEXT,
                target_post_id INTEGER,
                interaction_type TEXT NOT NULL,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def save_post(self, agent_id: int, agent_name: str, content: str,
                   post_type: str = "original") -> int:
        """保存帖子到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO posts (agent_id, agent_name, content, post_type) VALUES (?, ?, ?, ?)",
            (agent_id, agent_name, content, post_type)
        )

        post_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return post_id

    def save_interaction(self, agent_id: int, agent_name: str,
                         target_post_id: int, interaction_type: str,
                         content: str = None) -> int:
        """保存互动到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO interactions (agent_id, agent_name, target_post_id, interaction_type, content) VALUES (?, ?, ?, ?, ?)",
            (agent_id, agent_name, target_post_id, interaction_type, content)
        )

        interaction_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return interaction_id

    def get_recent_posts(self, limit: int = 50) -> List[Dict]:
        """获取最近的帖子"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, agent_id, agent_name, content, likes, comments, shares, created_at FROM posts ORDER BY id DESC LIMIT ?",
            (limit,)
        )

        posts = []
        for row in cursor.fetchall():
            posts.append({
                "id": row[0],
                "agent_id": row[1],
                "agent_name": row[2],
                "content": row[3],
                "likes": row[4],
                "comments": row[5],
                "shares": row[6],
                "created_at": row[7]
            })

        conn.close()
        return posts


class WechatSimulator(ChinesePlatformSimulator):
    """微信公众号模拟器"""

    def __init__(self, config: Dict[str, Any], simulation_dir: str):
        super().__init__("wechat", config, simulation_dir)

    async def run_simulation(
        self,
        action_logger: Any = None,
        main_logger: Any = None,
        max_rounds: Optional[int] = None
    ) -> PlatformSimulation:
        """运行微信公众号模拟"""
        result = PlatformSimulation()

        def log_info(msg):
            if main_logger:
                main_logger.info(f"[微信公众号] {msg}")
            print(f"[微信公众号] {msg}")

        log_info("初始化...")

        # 加载配置
        if not self.load_profiles():
            return result

        self.init_database()

        # 获取配置
        event_config = self.config.get("event_config", {})
        initial_posts = event_config.get("initial_posts", [])
        time_config = self.config.get("time_config", {})
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 60)
        total_rounds = (total_hours * 60) // minutes_per_round

        if max_rounds:
            total_rounds = min(total_rounds, max_rounds)

        # 获取Agent名称映射
        agent_names = self._get_agent_names()

        total_actions = 0
        start_time = datetime.now()

        # 发布初始帖子
        if action_logger:
            action_logger.log_round_start(0, 0)

        for post in initial_posts:
            agent_id = post.get("poster_agent_id", 0)
            content = post.get("content", "")

            # 根据平台限制截断内容
            max_len = self.platform_config["max_content_length"]
            if len(content) > max_len:
                content = content[:max_len] + "..."

            agent_name = agent_names.get(agent_id, f"Agent_{agent_id}")
            post_id = self.save_post(agent_id, agent_name, content, "original")

            if action_logger:
                action_logger.log_action(
                    round_num=0,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    action_type="CREATE_POST",
                    action_args={"content": content}
                )
                total_actions += 1

        if action_logger:
            action_logger.log_round_end(0, len(initial_posts))

        log_info(f"已发布 {len(initial_posts)} 条初始文章")

        # 主模拟循环
        for round_num in range(total_rounds):
            simulated_minutes = round_num * minutes_per_round
            simulated_hour = (simulated_minutes // 60) % 24
            simulated_day = simulated_minutes // (60 * 24) + 1

            # 获取活跃Agent
            active_agents = self._get_active_agents(simulated_hour, round_num)

            if action_logger:
                action_logger.log_round_start(round_num + 1, simulated_hour)

            # 模拟发帖和互动
            round_actions = 0
            for agent_id, agent_name, activity_level in active_agents:
                if random.random() < activity_level:
                    # 决定动作类型
                    action_type = random.choices(
                        ["post", "comment", "none"],
                        weights=[0.3, 0.2, 0.5]
                    )[0]

                    if action_type == "post":
                        # 生成新帖子内容
                        content = await self._generate_post_content(
                            agent_id, agent_name, round_num
                        )
                        if content:
                            self.save_post(agent_id, agent_name, content, "original")
                            if action_logger:
                                action_logger.log_action(
                                    round_num=round_num + 1,
                                    agent_id=agent_id,
                                    agent_name=agent_name,
                                    action_type="CREATE_POST",
                                    action_args={"content": content[:100] + "..."}
                                )
                            total_actions += 1
                            round_actions += 1

                    elif action_type == "comment":
                        # 对帖子进行评论
                        recent_posts = self.get_recent_posts(limit=20)
                        if recent_posts:
                            target = random.choice(recent_posts)
                            comment_content = await self._generate_comment_content(
                                agent_id, agent_name, target["content"]
                            )
                            if comment_content:
                                self.save_interaction(
                                    agent_id, agent_name,
                                    target["id"], "comment",
                                    comment_content
                                )
                                if action_logger:
                                    action_logger.log_action(
                                        round_num=round_num + 1,
                                        agent_id=agent_id,
                                        agent_name=agent_name,
                                        action_type="CREATE_COMMENT",
                                        action_args={
                                            "content": comment_content[:100] + "...",
                                            "target_post": target["id"]
                                        }
                                    )
                                total_actions += 1
                                round_actions += 1

            if action_logger:
                action_logger.log_round_end(round_num + 1, round_actions)

            if (round_num + 1) % 10 == 0:
                progress = (round_num + 1) / total_rounds * 100
                log_info(f"Day {simulated_day}, {simulated_hour:02d}:00 - Round {round_num + 1}/{total_rounds} ({progress:.1f}%)")

        if action_logger:
            action_logger.log_simulation_end(total_rounds, total_actions)

        result.total_actions = total_actions
        elapsed = (datetime.now() - start_time).total_seconds()
        log_info(f"模拟完成! 耗时: {elapsed:.1f}秒, 总动作: {total_actions}")

        return result

    def _get_agent_names(self) -> Dict[int, str]:
        """从配置获取Agent名称"""
        names = {}
        agent_configs = self.config.get("agent_configs", [])
        for agent in agent_configs:
            agent_id = agent.get("agent_id", 0)
            entity_name = agent.get("entity_name", f"Agent_{agent_id}")
            names[agent_id] = entity_name
        return names

    def _get_active_agents(self, hour: int, round_num: int) -> List[Tuple[int, str, float]]:
        """获取当前小时的活跃Agent"""
        active = []
        agent_configs = self.config.get("agent_configs", [])

        for agent in agent_configs:
            agent_id = agent.get("agent_id")
            entity_name = agent.get("entity_name")
            activity_level = agent.get("activity_level", 0)
            active_hours = agent.get("active_hours", [])

            # 检查是否在活跃时间
            if hour in active_hours and activity_level > 0:
                active.append((agent_id, entity_name, activity_level))

        return active

    async def _generate_post_content(self, agent_id: int, agent_name: str,
                                      round_num: int) -> Optional[str]:
        """生成帖子内容（简化版，实际可接入LLM）"""
        # 这里可以接入LLM生成更真实的内容
        # 简化处理：返回None表示跳过
        return None

    async def _generate_comment_content(self, agent_id: int, agent_name: str,
                                        post_content: str) -> Optional[str]:
        """生成评论内容（简化版）"""
        return None


class WeiboSimulator(ChinesePlatformSimulator):
    """微博模拟器"""

    def __init__(self, config: Dict[str, Any], simulation_dir: str):
        super().__init__("weibo", config, simulation_dir)

    async def run_simulation(
        self,
        action_logger: Any = None,
        main_logger: Any = None,
        max_rounds: Optional[int] = None
    ) -> PlatformSimulation:
        """运行微博模拟"""
        result = PlatformSimulation()

        def log_info(msg):
            if main_logger:
                main_logger.info(f"[微博] {msg}")
            print(f"[微博] {msg}")

        log_info("初始化...")

        if not self.load_profiles():
            return result

        self.init_database()

        event_config = self.config.get("event_config", {})
        initial_posts = event_config.get("initial_posts", [])
        time_config = self.config.get("time_config", {})
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 60)
        total_rounds = (total_hours * 60) // minutes_per_round

        if max_rounds:
            total_rounds = min(total_rounds, max_rounds)

        agent_names = self._get_agent_names()
        total_actions = 0
        start_time = datetime.now()

        # 初始帖子
        if action_logger:
            action_logger.log_round_start(0, 0)

        for post in initial_posts:
            agent_id = post.get("poster_agent_id", 0)
            content = post.get("content", "")
            max_len = self.platform_config["max_content_length"]
            if len(content) > max_len:
                content = content[:max_len] + "..."

            agent_name = agent_names.get(agent_id, f"Agent_{agent_id}")
            self.save_post(agent_id, agent_name, content, "original")

            if action_logger:
                action_logger.log_action(
                    round_num=0,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    action_type="CREATE_POST",
                    action_args={"content": content}
                )
                total_actions += 1

        if action_logger:
            action_logger.log_round_end(0, len(initial_posts))

        log_info(f"已发布 {len(initial_posts)} 条微博")

        # 主循环
        for round_num in range(total_rounds):
            simulated_minutes = round_num * minutes_per_round
            simulated_hour = (simulated_minutes // 60) % 24
            simulated_day = simulated_minutes // (60 * 24) + 1

            active_agents = self._get_active_agents(simulated_hour, round_num)

            if action_logger:
                action_logger.log_round_start(round_num + 1, simulated_hour)

            round_actions = 0
            for agent_id, agent_name, activity_level in active_agents:
                if random.random() < activity_level:
                    action_type = random.choices(
                        ["post", "like", "comment", "repost", "none"],
                        weights=[0.25, 0.25, 0.2, 0.1, 0.2]
                    )[0]

                    if action_type == "post":
                        content = await self._generate_post_content(agent_id, agent_name, round_num)
                        if content:
                            self.save_post(agent_id, agent_name, content, "original")
                            if action_logger:
                                action_logger.log_action(
                                    round_num=round_num + 1,
                                    agent_id=agent_id,
                                    agent_name=agent_name,
                                    action_type="CREATE_POST",
                                    action_args={"content": content[:100] + "..."}
                                )
                            total_actions += 1
                            round_actions += 1
                    elif action_type in ["like", "comment", "repost"]:
                        recent_posts = self.get_recent_posts(limit=30)
                        if recent_posts:
                            target = random.choice(recent_posts)
                            self.save_interaction(
                                agent_id, agent_name, target["id"], action_type,
                                f"互动内容" if action_type == "comment" else None
                            )
                            if action_logger:
                                action_logger.log_action(
                                    round_num=round_num + 1,
                                    agent_id=agent_id,
                                    agent_name=agent_name,
                                    action_type=f"CREATE_{action_type.upper()}",
                                    action_args={"target_post": target["id"]}
                                )
                            total_actions += 1
                            round_actions += 1

            if action_logger:
                action_logger.log_round_end(round_num + 1, round_actions)

            if (round_num + 1) % 10 == 0:
                progress = (round_num + 1) / total_rounds * 100
                log_info(f"Day {simulated_day}, {simulated_hour:02d}:00 - Round {round_num + 1}/{total_rounds} ({progress:.1f}%)")

        if action_logger:
            action_logger.log_simulation_end(total_rounds, total_actions)

        result.total_actions = total_actions
        elapsed = (datetime.now() - start_time).total_seconds()
        log_info(f"模拟完成! 耗时: {elapsed:.1f}秒, 总动作: {total_actions}")

        return result

    def _get_agent_names(self) -> Dict[int, str]:
        names = {}
        for agent in self.config.get("agent_configs", []):
            names[agent.get("agent_id", 0)] = agent.get("entity_name", f"Agent_{agent.get('agent_id')}")
        return names

    def _get_active_agents(self, hour: int, round_num: int) -> List[Tuple[int, str, float]]:
        active = []
        for agent in self.config.get("agent_configs", []):
            if hour in agent.get("active_hours", []) and agent.get("activity_level", 0) > 0:
                active.append((
                    agent.get("agent_id"),
                    agent.get("entity_name"),
                    agent.get("activity_level")
                ))
        return active

    async def _generate_post_content(self, agent_id: int, agent_name: str, round_num: int) -> Optional[str]:
        return None


class DouyinSimulator(ChinesePlatformSimulator):
    """抖音模拟器"""

    def __init__(self, config: Dict[str, Any], simulation_dir: str):
        super().__init__("douyin", config, simulation_dir)

    async def run_simulation(
        self,
        action_logger: Any = None,
        main_logger: Any = None,
        max_rounds: Optional[int] = None
    ) -> PlatformSimulation:
        result = PlatformSimulation()

        def log_info(msg):
            if main_logger:
                main_logger.info(f"[抖音] {msg}")
            print(f"[抖音] {msg}")

        log_info("初始化...")

        if not self.load_profiles():
            return result

        self.init_database()

        event_config = self.config.get("event_config", {})
        initial_posts = event_config.get("initial_posts", [])
        time_config = self.config.get("time_config", {})
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 60)
        total_rounds = (total_hours * 60) // minutes_per_round

        if max_rounds:
            total_rounds = min(total_rounds, max_rounds)

        agent_names = self._get_agent_names()
        total_actions = 0
        start_time = datetime.now()

        # 初始帖子 - 抖音主要是视频，这里用文字描述视频内容
        if action_logger:
            action_logger.log_round_start(0, 0)

        for post in initial_posts:
            agent_id = post.get("poster_agent_id", 0)
            content = post.get("content", "")
            max_len = self.platform_config["max_content_length"]
            if len(content) > max_len:
                content = content[:max_len] + "..."

            agent_name = agent_names.get(agent_id, f"Agent_{agent_id}")
            # 抖音帖子标记为视频
            self.save_post(agent_id, agent_name, content, "video")

            if action_logger:
                action_logger.log_action(
                    round_num=0,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    action_type="UPLOAD_VIDEO",
                    action_args={"content": content}
                )
                total_actions += 1

        if action_logger:
            action_logger.log_round_end(0, len(initial_posts))

        log_info(f"已发布 {len(initial_posts)} 个视频")

        # 主循环 - 抖音互动更频繁
        for round_num in range(total_rounds):
            simulated_minutes = round_num * minutes_per_round
            simulated_hour = (simulated_minutes // 60) % 24
            simulated_day = simulated_minutes // (60 * 24) + 1

            active_agents = self._get_active_agents(simulated_hour, round_num)

            if action_logger:
                action_logger.log_round_start(round_num + 1, simulated_hour)

            round_actions = 0
            for agent_id, agent_name, activity_level in active_agents:
                if random.random() < activity_level:
                    action_type = random.choices(
                        ["video", "like", "comment", "share", "none"],
                        weights=[0.15, 0.35, 0.25, 0.05, 0.2]
                    )[0]

                    if action_type == "video":
                        content = f"视频内容 #{round_num}"
                        self.save_post(agent_id, agent_name, content, "video")
                        if action_logger:
                            action_logger.log_action(
                                round_num=round_num + 1,
                                agent_id=agent_id,
                                agent_name=agent_name,
                                action_type="UPLOAD_VIDEO",
                                action_args={"content": content[:50]}
                            )
                        total_actions += 1
                        round_actions += 1
                    elif action_type in ["like", "comment", "share"]:
                        recent_posts = self.get_recent_posts(limit=50)
                        if recent_posts:
                            target = random.choice(recent_posts)
                            self.save_interaction(
                                agent_id, agent_name, target["id"], action_type,
                                "评论内容" if action_type == "comment" else None
                            )
                            if action_logger:
                                action_logger.log_action(
                                    round_num=round_num + 1,
                                    agent_id=agent_id,
                                    agent_name=agent_name,
                                    action_type=f"CREATE_{action_type.upper()}",
                                    action_args={"target": target["id"]}
                                )
                            total_actions += 1
                            round_actions += 1

            if action_logger:
                action_logger.log_round_end(round_num + 1, round_actions)

            if (round_num + 1) % 10 == 0:
                progress = (round_num + 1) / total_rounds * 100
                log_info(f"Day {simulated_day}, {simulated_hour:02d}:00 - Round {round_num + 1}/{total_rounds} ({progress:.1f}%)")

        if action_logger:
            action_logger.log_simulation_end(total_rounds, total_actions)

        result.total_actions = total_actions
        elapsed = (datetime.now() - start_time).total_seconds()
        log_info(f"模拟完成! 耗时: {elapsed:.1f}秒, 总动作: {total_actions}")

        return result

    def _get_agent_names(self) -> Dict[int, str]:
        names = {}
        for agent in self.config.get("agent_configs", []):
            names[agent.get("agent_id", 0)] = agent.get("entity_name", f"Agent_{agent.get('agent_id')}")
        return names

    def _get_active_agents(self, hour: int, round_num: int) -> List[Tuple[int, str, float]]:
        active = []
        for agent in self.config.get("agent_configs", []):
            if hour in agent.get("active_hours", []) and agent.get("activity_level", 0) > 0:
                active.append((
                    agent.get("agent_id"),
                    agent.get("entity_name"),
                    agent.get("activity_level")
                ))
        return active


class KuaishouSimulator(ChinesePlatformSimulator):
    """快手模拟器 - 结构与抖音类似"""

    def __init__(self, config: Dict[str, Any], simulation_dir: str):
        super().__init__("kuaishou", config, simulation_dir)

    async def run_simulation(
        self,
        action_logger: Any = None,
        main_logger: Any = None,
        max_rounds: Optional[int] = None
    ) -> PlatformSimulation:
        result = PlatformSimulation()

        def log_info(msg):
            if main_logger:
                main_logger.info(f"[快手] {msg}")
            print(f"[快手] {msg}")

        log_info("初始化...")

        if not self.load_profiles():
            return result

        self.init_database()

        event_config = self.config.get("event_config", {})
        initial_posts = event_config.get("initial_posts", [])
        time_config = self.config.get("time_config", {})
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 60)
        total_rounds = (total_hours * 60) // minutes_per_round

        if max_rounds:
            total_rounds = min(total_rounds, max_rounds)

        agent_names = self._get_agent_names()
        total_actions = 0
        start_time = datetime.now()

        if action_logger:
            action_logger.log_round_start(0, 0)

        for post in initial_posts:
            agent_id = post.get("poster_agent_id", 0)
            content = post.get("content", "")
            max_len = self.platform_config["max_content_length"]
            if len(content) > max_len:
                content = content[:max_len] + "..."

            agent_name = agent_names.get(agent_id, f"Agent_{agent_id}")
            self.save_post(agent_id, agent_name, content, "video")

            if action_logger:
                action_logger.log_action(
                    round_num=0,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    action_type="UPLOAD_VIDEO",
                    action_args={"content": content}
                )
                total_actions += 1

        if action_logger:
            action_logger.log_round_end(0, len(initial_posts))

        log_info(f"已发布 {len(initial_posts)} 个视频")

        for round_num in range(total_rounds):
            simulated_minutes = round_num * minutes_per_round
            simulated_hour = (simulated_minutes // 60) % 24
            simulated_day = simulated_minutes // (60 * 24) + 1

            active_agents = self._get_active_agents(simulated_hour, round_num)

            if action_logger:
                action_logger.log_round_start(round_num + 1, simulated_hour)

            round_actions = 0
            for agent_id, agent_name, activity_level in active_agents:
                if random.random() < activity_level:
                    action_type = random.choices(
                        ["video", "like", "comment", "share", "none"],
                        weights=[0.15, 0.35, 0.25, 0.05, 0.2]
                    )[0]

                    if action_type == "video":
                        content = f"快手视频内容 #{round_num}"
                        self.save_post(agent_id, agent_name, content, "video")
                        if action_logger:
                            action_logger.log_action(
                                round_num=round_num + 1,
                                agent_id=agent_id,
                                agent_name=agent_name,
                                action_type="UPLOAD_VIDEO",
                                action_args={"content": content[:50]}
                            )
                        total_actions += 1
                        round_actions += 1
                    elif action_type in ["like", "comment", "share"]:
                        recent_posts = self.get_recent_posts(limit=50)
                        if recent_posts:
                            target = random.choice(recent_posts)
                            self.save_interaction(
                                agent_id, agent_name, target["id"], action_type,
                                "评论内容" if action_type == "comment" else None
                            )
                            total_actions += 1
                            round_actions += 1

            if action_logger:
                action_logger.log_round_end(round_num + 1, round_actions)

            if (round_num + 1) % 10 == 0:
                progress = (round_num + 1) / total_rounds * 100
                log_info(f"Day {simulated_day}, {simulated_hour:02d}:00 - Round {round_num + 1}/{total_rounds} ({progress:.1f}%)")

        if action_logger:
            action_logger.log_simulation_end(total_rounds, total_actions)

        result.total_actions = total_actions
        elapsed = (datetime.now() - start_time).total_seconds()
        log_info(f"模拟完成! 耗时: {elapsed:.1f}秒, 总动作: {total_actions}")

        return result


class XiaohongshuSimulator(ChinesePlatformSimulator):
    """小红书模拟器"""

    def __init__(self, config: Dict[str, Any], simulation_dir: str):
        super().__init__("xiaohongshu", config, simulation_dir)

    async def run_simulation(
        self,
        action_logger: Any = None,
        main_logger: Any = None,
        max_rounds: Optional[int] = None
    ) -> PlatformSimulation:
        result = PlatformSimulation()

        def log_info(msg):
            if main_logger:
                main_logger.info(f"[小红书] {msg}")
            print(f"[小红书] {msg}")

        log_info("初始化...")

        if not self.load_profiles():
            return result

        self.init_database()

        event_config = self.config.get("event_config", {})
        initial_posts = event_config.get("initial_posts", [])
        time_config = self.config.get("time_config", {})
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 60)
        total_rounds = (total_hours * 60) // minutes_per_round

        if max_rounds:
            total_rounds = min(total_rounds, max_rounds)

        agent_names = self._get_agent_names()
        total_actions = 0
        start_time = datetime.now()

        if action_logger:
            action_logger.log_round_start(0, 0)

        for post in initial_posts:
            agent_id = post.get("poster_agent_id", 0)
            content = post.get("content", "")
            max_len = self.platform_config["max_content_length"]
            if len(content) > max_len:
                content = content[:max_len] + "..."

            agent_name = agent_names.get(agent_id, f"Agent_{agent_id}")
            self.save_post(agent_id, agent_name, content, "note")

            if action_logger:
                action_logger.log_action(
                    round_num=0,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    action_type="CREATE_NOTE",
                    action_args={"content": content}
                )
                total_actions += 1

        if action_logger:
            action_logger.log_round_end(0, len(initial_posts))

        log_info(f"已发布 {len(initial_posts)} 篇笔记")

        for round_num in range(total_rounds):
            simulated_minutes = round_num * minutes_per_round
            simulated_hour = (simulated_minutes // 60) % 24
            simulated_day = simulated_minutes // (60 * 24) + 1

            active_agents = self._get_active_agents(simulated_hour, round_num)

            if action_logger:
                action_logger.log_round_start(round_num + 1, simulated_hour)

            round_actions = 0
            for agent_id, agent_name, activity_level in active_agents:
                if random.random() < activity_level:
                    action_type = random.choices(
                        ["note", "like", "comment", "collect", "none"],
                        weights=[0.2, 0.3, 0.2, 0.1, 0.2]
                    )[0]

                    if action_type == "note":
                        content = f"小红书笔记内容 #{round_num}"
                        self.save_post(agent_id, agent_name, content, "note")
                        if action_logger:
                            action_logger.log_action(
                                round_num=round_num + 1,
                                agent_id=agent_id,
                                agent_name=agent_name,
                                action_type="CREATE_NOTE",
                                action_args={"content": content[:50]}
                            )
                        total_actions += 1
                        round_actions += 1
                    elif action_type in ["like", "comment", "collect"]:
                        recent_posts = self.get_recent_posts(limit=30)
                        if recent_posts:
                            target = random.choice(recent_posts)
                            self.save_interaction(
                                agent_id, agent_name, target["id"], action_type,
                                "评论" if action_type == "comment" else None
                            )
                            if action_logger:
                                action_logger.log_action(
                                    round_num=round_num + 1,
                                    agent_id=agent_id,
                                    agent_name=agent_name,
                                    action_type=f"CREATE_{action_type.upper()}",
                                    action_args={"target": target["id"]}
                                )
                            total_actions += 1
                            round_actions += 1

            if action_logger:
                action_logger.log_round_end(round_num + 1, round_actions)

            if (round_num + 1) % 10 == 0:
                progress = (round_num + 1) / total_rounds * 100
                log_info(f"Day {simulated_day}, {simulated_hour:02d}:00 - Round {round_num + 1}/{total_rounds} ({progress:.1f}%)")

        if action_logger:
            action_logger.log_simulation_end(total_rounds, total_actions)

        result.total_actions = total_actions
        elapsed = (datetime.now() - start_time).total_seconds()
        log_info(f"模拟完成! 耗时: {elapsed:.1f}秒, 总动作: {total_actions}")

        return result

    def _get_agent_names(self) -> Dict[int, str]:
        names = {}
        for agent in self.config.get("agent_configs", []):
            names[agent.get("agent_id", 0)] = agent.get("entity_name", f"Agent_{agent.get('agent_id')}")
        return names

    def _get_active_agents(self, hour: int, round_num: int) -> List[Tuple[int, str, float]]:
        active = []
        for agent in self.config.get("agent_configs", []):
            if hour in agent.get("active_hours", []) and agent.get("activity_level", 0) > 0:
                active.append((
                    agent.get("agent_id"),
                    agent.get("entity_name"),
                    agent.get("activity_level")
                ))
        return active


class ShipinhaoSimulator(ChinesePlatformSimulator):
    """微信视频号模拟器"""

    def __init__(self, config: Dict[str, Any], simulation_dir: str):
        super().__init__("shipinhao", config, simulation_dir)

    async def run_simulation(
        self,
        action_logger: Any = None,
        main_logger: Any = None,
        max_rounds: Optional[int] = None
    ) -> PlatformSimulation:
        result = PlatformSimulation()

        def log_info(msg):
            if main_logger:
                main_logger.info(f"[微信视频号] {msg}")
            print(f"[微信视频号] {msg}")

        log_info("初始化...")

        if not self.load_profiles():
            return result

        self.init_database()

        event_config = self.config.get("event_config", {})
        initial_posts = event_config.get("initial_posts", [])
        time_config = self.config.get("time_config", {})
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 60)
        total_rounds = (total_hours * 60) // minutes_per_round

        if max_rounds:
            total_rounds = min(total_rounds, max_rounds)

        agent_names = self._get_agent_names()
        total_actions = 0
        start_time = datetime.now()

        if action_logger:
            action_logger.log_round_start(0, 0)

        for post in initial_posts:
            agent_id = post.get("poster_agent_id", 0)
            content = post.get("content", "")
            max_len = self.platform_config["max_content_length"]
            if len(content) > max_len:
                content = content[:max_len] + "..."

            agent_name = agent_names.get(agent_id, f"Agent_{agent_id}")
            self.save_post(agent_id, agent_name, content, "video")

            if action_logger:
                action_logger.log_action(
                    round_num=0,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    action_type="PUBLISH_VIDEO",
                    action_args={"content": content}
                )
                total_actions += 1

        if action_logger:
            action_logger.log_round_end(0, len(initial_posts))

        log_info(f"已发布 {len(initial_posts)} 个视频")

        for round_num in range(total_rounds):
            simulated_minutes = round_num * minutes_per_round
            simulated_hour = (simulated_minutes // 60) % 24
            simulated_day = simulated_minutes // (60 * 24) + 1

            active_agents = self._get_active_agents(simulated_hour, round_num)

            if action_logger:
                action_logger.log_round_start(round_num + 1, simulated_hour)

            round_actions = 0
            for agent_id, agent_name, activity_level in active_agents:
                if random.random() < activity_level:
                    action_type = random.choices(
                        ["video", "like", "comment", "share_wechat", "none"],
                        weights=[0.15, 0.3, 0.25, 0.1, 0.2]
                    )[0]

                    if action_type == "video":
                        content = f"视频号内容 #{round_num}"
                        self.save_post(agent_id, agent_name, content, "video")
                        if action_logger:
                            action_logger.log_action(
                                round_num=round_num + 1,
                                agent_id=agent_id,
                                agent_name=agent_name,
                                action_type="PUBLISH_VIDEO",
                                action_args={"content": content[:50]}
                            )
                        total_actions += 1
                        round_actions += 1
                    elif action_type in ["like", "comment", "share_wechat"]:
                        recent_posts = self.get_recent_posts(limit=40)
                        if recent_posts:
                            target = random.choice(recent_posts)
                            self.save_interaction(
                                agent_id, agent_name, target["id"], action_type,
                                "评论" if action_type == "comment" else None
                            )
                            if action_logger:
                                action_logger.log_action(
                                    round_num=round_num + 1,
                                    agent_id=agent_id,
                                    agent_name=agent_name,
                                    action_type=f"CREATE_{action_type.upper()}",
                                    action_args={"target": target["id"]}
                                )
                            total_actions += 1
                            round_actions += 1

            if action_logger:
                action_logger.log_round_end(round_num + 1, round_actions)

            if (round_num + 1) % 10 == 0:
                progress = (round_num + 1) / total_rounds * 100
                log_info(f"Day {simulated_day}, {simulated_hour:02d}:00 - Round {round_num + 1}/{total_rounds} ({progress:.1f}%)")

        if action_logger:
            action_logger.log_simulation_end(total_rounds, total_actions)

        result.total_actions = total_actions
        elapsed = (datetime.now() - start_time).total_seconds()
        log_info(f"模拟完成! 耗时: {elapsed:.1f}秒, 总动作: {total_actions}")

        return result


# 模拟器工厂函数
def create_chinese_platform_simulator(
    platform: str,
    config: Dict[str, Any],
    simulation_dir: str
) -> Optional[ChinesePlatformSimulator]:
    """创建中国平台模拟器"""

    simulators = {
        "wechat": WechatSimulator,
        "weibo": WeiboSimulator,
        "douyin": DouyinSimulator,
        "kuaishou": KuaishouSimulator,
        "xiaohongshu": XiaohongshuSimulator,
        "shipinhao": ShipinhaoSimulator,
    }

    simulator_class = simulators.get(platform.lower())
    if simulator_class:
        return simulator_class(config, simulation_dir)

    return None


# 导出
__all__ = [
    "CHINESE_PLATFORMS",
    "ChinesePlatformSimulator",
    "WechatSimulator",
    "WeiboSimulator",
    "DouyinSimulator",
    "KuaishouSimulator",
    "XiaohongshuSimulator",
    "ShipinhaoSimulator",
    "create_chinese_platform_simulator",
]
