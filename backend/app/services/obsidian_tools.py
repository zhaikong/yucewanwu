#!/usr/bin/env python3
"""
Obsidian 工具服务
为 ReportAgent 提供基于 Obsidian 本地知识库的工具函数
"""

import json
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.obsidian_tools')


@dataclass
class SearchResult:
    """搜索结果"""
    query: str
    results: List[Dict[str, Any]]
    total: int
    source: str = "obsidian"

    def to_text(self) -> str:
        """转换为易读的文本格式"""
        if not self.results:
            return f"未找到与「{self.query}」相关的知识。"

        lines = [f"找到 {self.total} 个相关结果：\n"]

        for i, result in enumerate(self.results[:10], 1):
            name = result.get("name", "未知")
            summary = result.get("summary", "")[:200]

            lines.append(f"{i}. **{name}**")
            if summary:
                lines.append(f"   {summary}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class EntityInfo:
    """实体信息"""
    uuid: str
    name: str
    entity_type: str
    summary: str
    attributes: Dict[str, Any]
    related_entities: List[Dict[str, Any]]
    source: str = "obsidian"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_text(self) -> str:
        """转换为易读的文本格式"""
        lines = [f"## {self.name}"]
        lines.append(f"**类型**: {self.entity_type}\n")

        if self.summary:
            lines.append(f"**摘要**: {self.summary}\n")

        if self.attributes:
            lines.append("**属性**:")
            for key, value in self.attributes.items():
                lines.append(f"- {key}: {value}")
            lines.append("")

        if self.related_entities:
            lines.append("**相关实体**:")
            for entity in self.related_entities[:5]:
                name = entity.get("name", "未知")
                rel_type = entity.get("relation", "")
                lines.append(f"- {name} ({rel_type})")
            lines.append("")

        return "\n".join(lines)


class ObsidianToolsService:
    """
    Obsidian 工具服务
    提供与 ZepToolsService 类似接口的工具函数
    """

    def __init__(self):
        """初始化 Obsidian 工具服务"""
        if not Config.OBSIDIAN_VAULT_PATH:
            raise ValueError("OBSIDIAN_VAULT_PATH 未配置")

        from .obsidian_reader import ObsidianVaultReader
        from .kg_adapter import get_knowledge_graph

        self.reader = ObsidianVaultReader()
        self.kg = get_knowledge_graph()
        logger.info("ObsidianToolsService 初始化完成")

    def get_graph_statistics(self, graph_id: str = None) -> Dict[str, Any]:
        """获取图谱统计信息

        Args:
            graph_id: 图谱ID（可选，用于兼容）
        """
        stats = self.reader.get_graph_statistics()
        stats["source"] = "obsidian"
        # 添加 entity_types 字段以兼容 report_agent
        stats["entity_types"] = stats.get("nodes_by_type", {})
        return stats

    def quick_search(self, query: str, limit: int = 10) -> SearchResult:
        """快速搜索"""
        # 使用Obsidian reader的搜索功能
        nodes = self.reader.search_nodes(query, limit=limit)

        results = []
        for node in nodes:
            results.append({
                "name": node.name,
                "summary": node.summary[:200] if node.summary else "",
                "type": node.get_entity_type() or "Entity",
                "uuid": node.uuid
            })

        return SearchResult(
            query=query,
            results=results,
            total=len(results)
        )

    def panorama_search(self, query: str, include_expired: bool = True) -> SearchResult:
        """广度搜索 - 获取更全面的结果"""
        # 在Obsidian中进行更广泛的搜索
        nodes = self.reader.search_nodes(query, limit=30)

        results = []
        for node in nodes:
            results.append({
                "name": node.name,
                "summary": node.summary[:300] if node.summary else "",
                "type": node.get_entity_type() or "Entity",
                "uuid": node.uuid,
                "file_path": node.file_path
            })

        return SearchResult(
            query=query,
            results=results,
            total=len(results)
        )

    def get_entity_summary(self, entity_name: str) -> Dict[str, Any]:
        """获取实体摘要"""
        node = self.reader.get_entity_by_name(entity_name)

        if not node:
            return {"error": f"未找到实体: {entity_name}"}

        related = []
        for rel in node.related_nodes[:10]:
            related.append({
                "name": rel.get("name", ""),
                "relation": rel.get("relation", ""),
                "type": rel.get("type", "")
            })

        return {
            "uuid": node.uuid,
            "name": node.name,
            "entity_type": node.get_entity_type() or "Entity",
            "summary": node.summary,
            "attributes": node.attributes,
            "related_entities": related
        }

    def get_entities_by_type(self, entity_type: str) -> List[Any]:
        """获取指定类型的所有实体"""
        try:
            result = self.reader.filter_defined_entities(
                defined_entity_types=[entity_type],
                enrich_with_edges=True
            )
            return result.entities if result else []
        except Exception as e:
            logger.warning(f"获取实体类型失败: {entity_type}, 错误: {e}")
            return []

    def get_entity_with_context(self, entity_uuid: str) -> Optional[EntityInfo]:
        """获取实体及其上下文"""
        node = self.reader.get_entity_with_context(entity_uuid)

        if not node:
            return None

        related = []
        for rel in node.related_nodes[:10]:
            related.append({
                "name": rel.get("name", ""),
                "relation": rel.get("relation", ""),
                "type": rel.get("type", "")
            })

        return EntityInfo(
            uuid=node.uuid,
            name=node.name,
            entity_type=node.get_entity_type() or "Entity",
            summary=node.summary,
            attributes=node.attributes,
            related_entities=related
        )

    def insight_forge(
        self,
        query: str,
        simulation_requirement: str = "",
        report_context: str = ""
    ) -> SearchResult:
        """
        深度分析 - 生成针对查询的深入分析结果
        这是一个高级搜索，结合多个来源的信息
        """
        # 构建综合查询
        combined_query = query
        if simulation_requirement:
            combined_query = f"{query} {simulation_requirement}"

        # 搜索相关实体
        nodes = self.reader.search_nodes(combined_query, limit=20)

        results = []
        for node in nodes:
            # 提取更多信息
            entity_info = self.get_entity_summary(node.name)

            results.append({
                "name": node.name,
                "summary": node.summary[:500] if node.summary else "",
                "type": node.get_entity_type() or "Entity",
                "uuid": node.uuid,
                "attributes": node.attributes,
                "related_entities": entity_info.get("related_entities", [])[:5]
            })

        return SearchResult(
            query=query,
            results=results,
            total=len(results)
        )

    def interview_agents(
        self,
        simulation_id: str,
        interview_requirement: str,
        simulation_requirement: str = "",
        max_agents: int = 5
    ) -> SearchResult:
        """
        模拟Agent采访 - 从模拟结果中获取Agent的观点
        注意：这是从模拟数据中获取，不是从知识图谱
        """
        # 这个功能需要访问模拟数据，暂时返回提示信息
        results = [{
            "name": "模拟数据查询",
            "summary": f"interview_agents 功能需要访问模拟数据。当前查询: {interview_requirement}",
            "type": "System",
            "uuid": "system"
        }]

        return SearchResult(
            query=interview_requirement,
            results=results,
            total=1
        )

    def get_simulation_context(
        self,
        graph_id: str = None,
        simulation_requirement: str = "",
        limit: int = 30
    ) -> Dict[str, Any]:
        """获取模拟上下文

        Args:
            graph_id: 图谱ID
            simulation_requirement: 模拟需求描述
            limit: 每类信息的数量限制（Obsidian模式下暂未使用）
        """
        # 尝试从graph_id提取simulation_id
        simulation_id = None
        if graph_id:
            # graph_id格式通常是 obsidian_xxx 或 sim_xxx
            # 尝试找到对应的模拟目录
            for sim_dir_name in os.listdir(Config.OASIS_SIMULATION_DATA_DIR):
                sim_dir_path = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, sim_dir_name)
                state_file = os.path.join(sim_dir_path, "state.json")
                if os.path.exists(state_file):
                    try:
                        with open(state_file, 'r', encoding='utf-8') as f:
                            state = json.load(f)
                            if state.get("graph_id") == graph_id:
                                simulation_id = sim_dir_name
                                break
                    except Exception:
                        continue

        context = {
            "data_source": "obsidian",
            "graph_statistics": self.get_graph_statistics(graph_id) if graph_id else {},
            "total_entities": 0,
            "related_facts": [],
            "simulation_requirement": simulation_requirement
        }

        # 检查模拟目录是否存在
        if simulation_id:
            sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)

            if os.path.exists(sim_dir):
                # 尝试读取配置
                config_path = os.path.join(sim_dir, "simulation_config.json")
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                            context["config"] = {
                                "simulation_requirement": config.get("simulation_requirement", simulation_requirement),
                                "total_simulation_hours": config.get("time_config", {}).get("total_simulation_hours", 0),
                                "agent_count": len(config.get("agent_configs", []))
                            }
                            context["simulation_requirement"] = config.get("simulation_requirement", simulation_requirement)
                    except Exception as e:
                        logger.warning(f"读取模拟配置失败: {e}")

                # 获取实体数量
                try:
                    stats = context.get("graph_statistics", {})
                    context["total_entities"] = stats.get("total_nodes", 0)
                except Exception:
                    pass

        return context


def create_tools_service():
    """
    工厂函数：根据配置创建适当的工具服务

    优先使用 Obsidian，ZEP 已弃用
    """
    if Config.OBSIDIAN_VAULT_PATH:
        logger.info("创建 ObsidianToolsService")
        return ObsidianToolsService()
    else:
        raise ValueError("未配置知识图谱数据源，请配置 OBSIDIAN_VAULT_PATH")


__all__ = [
    "ObsidianToolsService",
    "SearchResult",
    "EntityInfo",
    "create_tools_service",
]
