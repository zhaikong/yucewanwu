"""
Obsidian Vault 读取服务
从 Obsidian 本地仓库中读取知识图谱数据
"""

import os
import re
import hashlib
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.obsidian_reader')

# Wikilink 正则: [[链接]] 或 [[链接|别名]]
WIKILINK_PATTERN = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')

# 内部链接正则: [文本](路径)
INTERNAL_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+\.md)\)')

# 属性正则: field:: value
ATTRIBUTE_PATTERN = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*::\s*(.+)$', re.MULTILINE)


@dataclass
class ObsidianEntityNode:
    """Obsidian 实体节点数据结构"""
    uuid: str  # 使用文件路径的 hash 作为 uuid
    name: str
    labels: List[str]  # 对应 frontmatter 中的 type
    summary: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)
    file_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
            "related_edges": self.related_edges,
            "related_nodes": self.related_nodes,
            "file_path": self.file_path,
        }

    def get_entity_type(self) -> Optional[str]:
        """获取实体类型"""
        for label in self.labels:
            if label not in ["Entity", "Node"]:
                return label
        return None


@dataclass
class FilteredEntities:
    """过滤后的实体集合"""
    entities: List[ObsidianEntityNode]
    entity_types: Set[str]
    total_count: int
    filtered_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "entity_types": list(self.entity_types),
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
        }


class ObsidianVaultReader:
    """
    Obsidian Vault 读取服务

    功能：
    1. 扫描 Vault 中的所有 Markdown 文件
    2. 解析 frontmatter (YAML) 提取实体属性
    3. 从 wikilinks [[]] 提取关系边
    4. 提供与 ZepEntityReader 兼容的接口
    """

    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = vault_path or Config.OBSIDIAN_VAULT_PATH
        if not self.vault_path:
            raise ValueError("OBSIDIAN_VAULT_PATH 未配置")

        if not os.path.isdir(self.vault_path):
            raise ValueError(f"OBSIDIAN_VAULT_PATH 目录不存在: {self.vault_path}")

        self._nodes: Dict[str, ObsidianEntityNode] = {}
        self._edges: List[Dict[str, Any]] = []
        self._name_to_uuid: Dict[str, str] = {}  # 文件名到 uuid 的映射

        logger.info(f"初始化 Obsidian Vault 读取器: {self.vault_path}")

    def _generate_uuid(self, file_path: str) -> str:
        """生成稳定的 UUID"""
        return hashlib.md5(file_path.encode()).hexdigest()

    def _parse_frontmatter(self, content: str) -> tuple[Dict[str, Any], str]:
        """
        解析 frontmatter

        Returns:
            (frontmatter_dict, body_content)
        """
        if not content.startswith('---'):
            return {}, content

        # 找到第二个 ---
        lines = content.split('\n')
        if len(lines) < 3:
            return {}, content

        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end_idx = i
                break

        if end_idx is None:
            return {}, content

        # 解析 YAML
        fm = {}
        for line in lines[1:end_idx]:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                fm[key] = value

        body = '\n'.join(lines[end_idx + 1:])
        return fm, body

    def _extract_wikilinks(self, content: str, current_file: str) -> List[Dict[str, Any]]:
        """
        从内容中提取 wikilinks

        Returns:
            边列表，每条边包含 source, target, fact
        """
        links = []

        # 提取 [[wikilinks]]
        for match in WIKILINK_PATTERN.finditer(content):
            target = match.group(1).strip()
            # 移除锚点 #
            target = target.split('#')[0].strip()
            if not target:
                continue

            # 构建事实描述
            fact = f"与 [[{target}]] 相关"

            links.append({
                "source": current_file,
                "target": target,
                "fact": fact,
                "type": "wikilink"
            })

        # 提取 [text](file.md) 内部链接
        for match in INTERNAL_LINK_PATTERN.finditer(content):
            text = match.group(1).strip()
            target = match.group(2).strip()
            # 移除 .md 后缀
            if target.endswith('.md'):
                target = target[:-3]

            links.append({
                "source": current_file,
                "target": target,
                "fact": f"与 {text} 相关",
                "type": "internal_link"
            })

        return links

    def _scan_vault(self):
        """扫描整个 Vault，构建节点和边"""
        logger.info("开始扫描 Obsidian Vault...")

        nodes = {}
        edges = []
        name_to_uuid = {}

        # 扫描所有 .md 文件
        for root, dirs, files in os.walk(self.vault_path):
            # 跳过隐藏目录和 _templates
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '_templates']

            for filename in files:
                if not filename.endswith('.md'):
                    continue

                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, self.vault_path)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    logger.warning(f"读取文件失败 {file_path}: {e}")
                    continue

                # 解析 frontmatter
                fm, body = self._parse_frontmatter(content)

                # 生成 UUID
                uuid = self._generate_uuid(rel_path)

                # 提取实体名称（优先用 name 字段，否则用文件名）
                name = fm.get('name', filename[:-3])  # 移除 .md

                # 提取实体类型
                entity_type = fm.get('type', 'Entity')
                labels = ['Entity', entity_type] if entity_type else ['Entity']

                # 提取摘要（summary 字段或第一段）
                summary = fm.get('summary', '')
                if not summary:
                    # 取第一段非空内容作为摘要
                    paragraphs = body.split('\n\n')
                    for p in paragraphs:
                        p = p.strip()
                        if p and not p.startswith('#'):
                            summary = p[:200]  # 截取前200字符
                            break

                # 提取属性（除保留字段外的其他 frontmatter 字段）
                reserved = {'name', 'type', 'summary'}
                attributes = {k: v for k, v in fm.items() if k not in reserved}

                # 提取 wikilinks
                file_links = self._extract_wikilinks(body, rel_path)

                node = ObsidianEntityNode(
                    uuid=uuid,
                    name=name,
                    labels=labels,
                    summary=summary,
                    attributes=attributes,
                    file_path=rel_path
                )

                nodes[uuid] = node
                name_to_uuid[name] = uuid
                edges.extend(file_links)

        # 第二遍：解析边关系（需要等所有节点加载完成）
        resolved_edges = []
        for edge in edges:
            source_uuid = name_to_uuid.get(edge['source'])
            target_uuid = name_to_uuid.get(edge['target'])

            if source_uuid and target_uuid:
                resolved_edges.append({
                    "uuid": self._generate_uuid(f"{edge['source']}->{edge['target']}"),
                    "name": "related",
                    "fact": edge['fact'],
                    "source_node_uuid": source_uuid,
                    "target_node_uuid": target_uuid,
                    "type": edge['type']
                })

        self._nodes = nodes
        self._edges = resolved_edges
        self._name_to_uuid = name_to_uuid

        logger.info(f"Vault 扫描完成: {len(nodes)} 个节点, {len(resolved_edges)} 条边")

    def _ensure_loaded(self):
        """确保数据已加载"""
        if not self._nodes:
            self._scan_vault()

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """
        获取所有节点

        Returns:
            节点列表
        """
        self._ensure_loaded()

        nodes_data = []
        for node in self._nodes.values():
            nodes_data.append({
                "uuid": node.uuid,
                "name": node.name,
                "labels": node.labels,
                "summary": node.summary,
                "attributes": node.attributes,
                "file_path": node.file_path,
            })

        logger.info(f"共获取 {len(nodes_data)} 个节点")
        return nodes_data

    def get_all_edges(self) -> List[Dict[str, Any]]:
        """
        获取所有边

        Returns:
            边列表
        """
        self._ensure_loaded()

        edges_data = []
        for edge in self._edges:
            edges_data.append({
                "uuid": edge["uuid"],
                "name": edge["name"],
                "fact": edge["fact"],
                "source_node_uuid": edge["source_node_uuid"],
                "target_node_uuid": edge["target_node_uuid"],
                "attributes": {"type": edge.get("type", "wikilink")},
            })

        logger.info(f"共获取 {len(edges_data)} 条边")
        return edges_data

    def filter_defined_entities(
        self,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True
    ) -> FilteredEntities:
        """
        筛选符合条件的实体节点

        Args:
            defined_entity_types: 预定义的实体类型列表
            enrich_with_edges: 是否包含边信息

        Returns:
            FilteredEntities
        """
        self._ensure_loaded()

        all_nodes = list(self._nodes.values())
        total_count = len(all_nodes)

        # 构建 UUID 到节点的映射
        node_map = {n.uuid: n for n in all_nodes}

        filtered_entities = []
        entity_types_found = set()

        for node in all_nodes:
            # 获取实体类型
            custom_labels = [l for l in node.labels if l not in ["Entity", "Node"]]

            if not custom_labels:
                continue

            # 检查是否匹配预定义类型
            if defined_entity_types:
                matching_labels = [l for l in custom_labels if l in defined_entity_types]
                if not matching_labels:
                    continue

            entity_types_found.add(custom_labels[0])

            # 获取相关边和节点
            if enrich_with_edges:
                related_edges = []
                related_node_uuids = set()

                for edge in self._edges:
                    if edge["source_node_uuid"] == node.uuid:
                        related_edges.append({
                            "direction": "outgoing",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "target_node_uuid": edge["target_node_uuid"],
                        })
                        related_node_uuids.add(edge["target_node_uuid"])
                    elif edge["target_node_uuid"] == node.uuid:
                        related_edges.append({
                            "direction": "incoming",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "source_node_uuid": edge["source_node_uuid"],
                        })
                        related_node_uuids.add(edge["source_node_uuid"])

                node.related_edges = related_edges

                # 获取关联节点
                related_nodes = []
                for related_uuid in related_node_uuids:
                    if related_uuid in node_map:
                        related_node = node_map[related_uuid]
                        related_nodes.append({
                            "uuid": related_node.uuid,
                            "name": related_node.name,
                            "labels": related_node.labels,
                            "summary": related_node.summary,
                        })

                node.related_nodes = related_nodes

            filtered_entities.append(node)

        logger.info(f"筛选完成: 总节点 {total_count}, 符合条件 {len(filtered_entities)}, "
                   f"实体类型: {entity_types_found}")

        return FilteredEntities(
            entities=filtered_entities,
            entity_types=entity_types_found,
            total_count=total_count,
            filtered_count=len(filtered_entities),
        )

    def get_entity_with_context(self, entity_uuid: str) -> Optional[ObsidianEntityNode]:
        """
        获取单个实体及其完整上下文

        Args:
            entity_uuid: 实体 UUID

        Returns:
            ObsidianEntityNode 或 None
        """
        self._ensure_loaded()

        if entity_uuid not in self._nodes:
            return None

        node = self._nodes[entity_uuid]
        all_nodes = list(self._nodes.values())
        node_map = {n.uuid: n for n in all_nodes}

        # 获取相关边
        related_edges = []
        related_node_uuids = set()

        for edge in self._edges:
            if edge["source_node_uuid"] == entity_uuid:
                related_edges.append({
                    "direction": "outgoing",
                    "edge_name": edge["name"],
                    "fact": edge["fact"],
                    "target_node_uuid": edge["target_node_uuid"],
                })
                related_node_uuids.add(edge["target_node_uuid"])
            elif edge["target_node_uuid"] == entity_uuid:
                related_edges.append({
                    "direction": "incoming",
                    "edge_name": edge["name"],
                    "fact": edge["fact"],
                    "source_node_uuid": edge["source_node_uuid"],
                })
                related_node_uuids.add(edge["source_node_uuid"])

        node.related_edges = related_edges

        # 获取关联节点
        related_nodes = []
        for related_uuid in related_node_uuids:
            if related_uuid in node_map:
                related_node = node_map[related_uuid]
                related_nodes.append({
                    "uuid": related_node.uuid,
                    "name": related_node.name,
                    "labels": related_node.labels,
                    "summary": related_node.summary,
                })

        node.related_nodes = related_nodes

        return node

    def get_entities_by_type(
        self,
        entity_type: str,
        enrich_with_edges: bool = True
    ) -> List[ObsidianEntityNode]:
        """
        获取指定类型的所有实体

        Args:
            entity_type: 实体类型
            enrich_with_edges: 是否包含边信息

        Returns:
            实体列表
        """
        result = self.filter_defined_entities(
            defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges
        )
        return result.entities

    def search_entities(self, query: str) -> List[ObsidianEntityNode]:
        """
        搜索实体（名称或摘要包含关键词）

        Args:
            query: 搜索关键词

        Returns:
            匹配的实体列表
        """
        self._ensure_loaded()

        query_lower = query.lower()
        results = []

        for node in self._nodes.values():
            # 搜索名称、摘要、属性
            if (query_lower in node.name.lower() or
                query_lower in node.summary.lower() or
                any(query_lower in str(v).lower() for v in node.attributes.values())):
                results.append(node)

        return results

    def search_nodes(self, query: str, limit: int = 10) -> List[ObsidianEntityNode]:
        """
        搜索节点（search_entities的别名，支持limit参数）

        Args:
            query: 搜索关键词
            limit: 返回结果数量限制

        Returns:
            匹配的实体列表
        """
        results = self.search_entities(query)
        return results[:limit]

    def get_entity_by_name(self, name: str) -> Optional[ObsidianEntityNode]:
        """
        根据名称获取实体

        Args:
            name: 实体名称

        Returns:
            匹配的实体，如果未找到则返回None
        """
        self._ensure_loaded()

        # 精确匹配
        for node in self._nodes.values():
            if node.name == name:
                return node

        # 忽略大小写匹配
        name_lower = name.lower()
        for node in self._nodes.values():
            if node.name.lower() == name_lower:
                return node

        return None

    def get_graph_statistics(self) -> Dict[str, Any]:
        """
        获取图谱统计信息

        Returns:
            统计信息字典
        """
        self._ensure_loaded()

        # 按类型统计节点
        type_counts: Dict[str, int] = {}
        for node in self._nodes.values():
            entity_type = node.get_entity_type()
            if entity_type:
                type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

        # 统计边
        edge_types: Dict[str, int] = {}
        for edge in self._edges:
            edge_type = edge.get("type", "unknown")
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "nodes_by_type": type_counts,
            "edges_by_type": edge_types,
        }
