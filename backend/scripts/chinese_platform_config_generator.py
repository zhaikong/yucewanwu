#!/usr/bin/env python3
"""
中国社交平台配置文件生成器
为微信公众号、微博、抖音、快手、小红书、微信视频号生成配置文件
"""

import json
import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime


# 平台配置模板
PLATFORM_TEMPLATES = {
    "wechat": {
        "name": "微信公众号",
        "name_en": "WeChat Official Account",
        "profile_suffix": "wechat_profiles.json",
        "platform_type": "Media",
        "post_format": "article",
        "features": ["图文消息", "评论", "自动回复"],
        "typical_length": "500-2000字",
    },
    "weibo": {
        "name": "微博",
        "name_en": "Weibo",
        "profile_suffix": "weibo_profiles.json",
        "platform_type": "Social",
        "post_format": "short_text",
        "features": ["文字", "图片", "视频", "话题", "@提及"],
        "typical_length": "140-2000字",
    },
    "douyin": {
        "name": "抖音",
        "name_en": "Douyin",
        "profile_suffix": "douyin_profiles.json",
        "platform_type": "Video",
        "post_format": "video",
        "features": ["短视频", "直播", "弹幕", "评论"],
        "typical_length": "15秒-3分钟",
    },
    "kuaishou": {
        "name": "快手",
        "name_en": "Kuaishou",
        "profile_suffix": "kuaishou_profiles.json",
        "platform_type": "Video",
        "post_format": "video",
        "features": ["短视频", "直播", "老铁文化", "评论"],
        "typical_length": "10秒-10分钟",
    },
    "xiaohongshu": {
        "name": "小红书",
        "name_en": "Xiaohongshu",
        "profile_suffix": "xiaohongshu_profiles.json",
        "platform_type": "Lifestyle",
        "post_format": "note",
        "features": ["图文笔记", "短视频", "种草", "测评"],
        "typical_length": "300-1000字",
    },
    "shipinhao": {
        "name": "微信视频号",
        "name_en": "WeChat Video Account",
        "profile_suffix": "shipinhao_profiles.json",
        "platform_type": "Video",
        "post_format": "video",
        "features": ["短视频", "直播", "朋友圈转发", "公众号联动"],
        "typical_length": "1分钟-10分钟",
    },
}


class ChinesePlatformProfileGenerator:
    """中国平台配置文件生成器"""

    def __init__(self, config: Dict[str, Any], simulation_dir: str):
        self.config = config
        self.simulation_dir = simulation_dir

    def generate_all_profiles(self) -> Dict[str, bool]:
        """为所有启用的中国平台生成配置文件"""
        results = {}

        # 检测需要生成哪些平台
        platforms_to_generate = self._detect_required_platforms()

        for platform in platforms_to_generate:
            success = self.generate_platform_profile(platform)
            results[platform] = success

        return results

    def _detect_required_platforms(self) -> List[str]:
        """检测需要生成配置文件的平台"""
        # 可以从配置中读取，或者默认生成所有
        enabled = self.config.get("enabled_chinese_platforms", [])

        if not enabled:
            # 默认生成所有平台
            return list(PLATFORM_TEMPLATES.keys())

        return enabled

    def generate_platform_profile(self, platform: str) -> bool:
        """为单个平台生成配置文件"""
        if platform not in PLATFORM_TEMPLATES:
            print(f"[{platform}] 不支持的平台")
            return False

        template = PLATFORM_TEMPLATES[platform]
        profile_path = os.path.join(
            self.simulation_dir,
            template["profile_suffix"]
        )

        # 从实体生成配置文件
        profiles = self._generate_profiles_from_entities(platform)

        try:
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profiles, f, ensure_ascii=False, indent=2)

            print(f"[{template['name']}] 已生成配置文件: {profile_path}")
            return True

        except Exception as e:
            print(f"[{template['name']}] 生成配置文件失败: {e}")
            return False

    def _generate_profiles_from_entities(self, platform: str) -> List[Dict[str, Any]]:
        """从实体配置生成平台配置文件"""
        profiles = []
        agent_configs = self.config.get("agent_configs", [])

        for agent in agent_configs:
            agent_id = agent.get("agent_id")
            entity_name = agent.get("entity_name")
            entity_type = agent.get("entity_type", "Person")
            activity_level = agent.get("activity_level", 0)

            # 根据实体类型生成适当的配置
            profile = self._create_profile_for_entity(
                agent_id, entity_name, entity_type,
                activity_level, platform
            )

            if profile:
                profiles.append(profile)

        return profiles

    def _create_profile_for_entity(
        self,
        agent_id: int,
        entity_name: str,
        entity_type: str,
        activity_level: float,
        platform: str
    ) -> Optional[Dict[str, Any]]:
        """为实体创建平台配置"""

        # 跳过无活动的实体
        if activity_level <= 0:
            return None

        base_profile = {
            "agent_id": agent_id,
            "name": entity_name,
            "platform": platform,
            "entity_type": entity_type,
        }

        # 根据平台和实体类型添加特定字段
        if platform == "wechat":
            base_profile.update(self._get_wechat_profile(entity_name, entity_type))
        elif platform == "weibo":
            base_profile.update(self._get_weibo_profile(entity_name, entity_type))
        elif platform == "douyin":
            base_profile.update(self._get_douyin_profile(entity_name, entity_type))
        elif platform == "kuaishou":
            base_profile.update(self._get_kuaishou_profile(entity_name, entity_type))
        elif platform == "xiaohongshu":
            base_profile.update(self._get_xiaohongshu_profile(entity_name, entity_type))
        elif platform == "shipinhao":
            base_profile.update(self._get_shipinhao_profile(entity_name, entity_type))

        return base_profile

    def _get_wechat_profile(self, entity_name: str, entity_type: str) -> Dict[str, Any]:
        """微信公众号配置"""
        is_org = entity_type in ["Organization", "GovernmentAgency", "MediaOutlet", "Platform"]

        return {
            "username": f"gh_{hash(entity_name) % 1000000000:08x}",
            "display_name": entity_name,
            "bio": self._generate_bio(entity_name, entity_type, "微信公众号"),
            "account_type": "企业" if is_org else "个人",
            "verification": "已认证" if is_org else "未认证",
            "followers": self._estimate_followers(entity_type),
            "post_frequency": "daily" if entity_type == "MediaOutlet" else "weekly",
        }

    def _get_weibo_profile(self, entity_name: str, entity_type: str) -> Dict[str, Any]:
        """微博配置"""
        is_org = entity_type in ["Organization", "GovernmentAgency", "MediaOutlet", "Platform"]

        return {
            "username": entity_name,
            "display_name": entity_name,
            "bio": self._generate_bio(entity_name, entity_type, "微博"),
            "gender": "unknown",
            "verification": "蓝V" if is_org else "个人",
            "followers": self._estimate_followers(entity_type),
            "following": random.randint(50, 500),
            "posts_count": random.randint(100, 10000),
        }

    def _get_douyin_profile(self, entity_name: str, entity_type: str) -> Dict[str, Any]:
        """抖音配置"""
        is_org = entity_type in ["Organization", "GovernmentAgency", "MediaOutlet", "Platform"]

        return {
            "username": f"dy_{entity_name}",
            "display_name": entity_name,
            "bio": self._generate_bio(entity_name, entity_type, "抖音"),
            "verification": "企业认证" if is_org else "个人",
            "followers": self._estimate_followers(entity_type),
            "likes": random.randint(1000, 100000),
            "videos_count": random.randint(10, 500),
        }

    def _get_kuaishou_profile(self, entity_name: str, entity_type: str) -> Dict[str, Any]:
        """快手配置"""
        is_org = entity_type in ["Organization", "GovernmentAgency", "MediaOutlet", "Platform"]

        return {
            "username": f"ks_{entity_name}",
            "display_name": entity_name,
            "bio": self._generate_bio(entity_name, entity_type, "快手"),
            "verification": "认证" if is_org else "个人",
            "followers": self._estimate_followers(entity_type),
            "works_count": random.randint(10, 300),
        }

    def _get_xiaohongshu_profile(self, entity_name: str, entity_type: str) -> Dict[str, Any]:
        """小红书配置"""
        is_org = entity_type in ["Organization", "GovernmentAgency", "MediaOutlet", "Platform"]

        return {
            "username": f"xhs_{entity_name}",
            "display_name": entity_name,
            "bio": self._generate_bio(entity_name, entity_type, "小红书"),
            "verification": "企业号" if is_org else "个人号",
            "followers": self._estimate_followers(entity_type),
            "likes": random.randint(500, 50000),
            "notes_count": random.randint(20, 500),
        }

    def _get_shipinhao_profile(self, entity_name: str, entity_type: str) -> Dict[str, Any]:
        """微信视频号配置"""
        is_org = entity_type in ["Organization", "GovernmentAgency", "MediaOutlet", "Platform"]

        return {
            "username": f"sp_{entity_name}",
            "display_name": entity_name,
            "bio": self._generate_bio(entity_name, entity_type, "视频号"),
            "verification": "认证" if is_org else "个人",
            "followers": self._estimate_followers(entity_type),
            "videos_count": random.randint(10, 200),
        }

    def _generate_bio(self, entity_name: str, entity_type: str, platform: str) -> str:
        """生成简介"""
        bios = {
            "MediaOutlet": f"{entity_name}官方{platform}账号",
            "GovernmentAgency": f"{entity_name}政务{platform}",
            "Organization": f"{entity_name}官方{platform}",
            "Person": f"{entity_name}的{platform}主页",
            "SelfMedia": f"{entity_name} - 自媒体",
            "Citizen": f"普通网民{entity_name}",
        }
        return bios.get(entity_type, f"{entity_name}的{platform}")

    def _estimate_followers(self, entity_type: str) -> int:
        """估算粉丝数"""
        followers_map = {
            "MediaOutlet": random.randint(10000, 1000000),
            "GovernmentAgency": random.randint(5000, 500000),
            "Organization": random.randint(1000, 100000),
            "Platform": random.randint(50000, 5000000),
            "SelfMedia": random.randint(100, 50000),
            "LegalExpert": random.randint(1000, 100000),
            "Person": random.randint(10, 5000),
            "Citizen": random.randint(1, 1000),
            "Victim": 0,
            "Suspect": 0,
        }
        return followers_map.get(entity_type, random.randint(10, 1000))


import random  # 添加random导入


def generate_chinese_platform_configs(
    config: Dict[str, Any],
    simulation_dir: str,
    platforms: Optional[List[str]] = None
) -> Dict[str, bool]:
    """生成中国平台配置文件的入口函数"""
    generator = ChinesePlatformProfileGenerator(config, simulation_dir)

    if platforms:
        config["enabled_chinese_platforms"] = platforms

    return generator.generate_all_profiles()


__all__ = [
    "PLATFORM_TEMPLATES",
    "ChinesePlatformProfileGenerator",
    "generate_chinese_platform_configs",
]
