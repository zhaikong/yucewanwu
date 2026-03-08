"""
Obsidian 图谱构建服务
从文档和本体定义中提取实体，保存到 Obsidian Vault
"""

import os
import uuid
import json
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.obsidian_graph')


@dataclass
class ObsidianGraphInfo:
    """图谱信息"""
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]
    vault_path: str
    nodes: List[Dict[str, Any]] = None
    edges: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.nodes is None:
            self.nodes = []
        if self.edges is None:
            self.edges = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
            "vault_path": self.vault_path,
            "nodes": self.nodes,
            "edges": self.edges,
        }


class ObsidianGraphBuilder:
    """
    Obsidian 图谱构建服务

    功能：
    1. 根据 ontology 和文档创建实体文件
    2. 根据 edge_types 创建关系
    3. 保存到配置的 OBSIDIAN_VAULT_PATH
    """

    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = vault_path or Config.OBSIDIAN_VAULT_PATH
        if not self.vault_path:
            raise ValueError("OBSIDIAN_VAULT_PATH 未配置")

        # 如果路径不存在，创建它
        os.makedirs(self.vault_path, exist_ok=True)

        self.graph_id = f"obsidian_{uuid.uuid4().hex[:16]}"
        self.entities_dir = os.path.join(self.vault_path, "_entities")
        os.makedirs(self.entities_dir, exist_ok=True)

        logger.info(f"初始化 Obsidian 图谱构建器: {self.vault_path}")

    def create_graph(self, name: str) -> str:
        """创建图谱（返回 graph_id）"""
        logger.info(f"创建 Obsidian 图谱: {name}")
        return self.graph_id

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        """设置本体定义

        Args:
            graph_id: 图谱ID
            ontology: 本体定义字典
        """
        # 保存 ontology 到图谱目录
        ontology_file = os.path.join(self.vault_path, "_ontology.json")
        with open(ontology_file, 'w', encoding='utf-8') as f:
            json.dump(ontology, f, ensure_ascii=False, indent=2)
        logger.info(f"本体定义已保存到: {ontology_file}")

    def add_text_batches(
        self,
        text: str,
        ontology: Dict[str, Any],
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        """
        从文本中提取实体并保存到 Obsidian

        Args:
            text: 输入文本
            ontology: 本体定义
            chunk_size: 文本块大小
            chunk_overlap: 块重叠大小
            progress_callback: 进度回调
        """
        from ..services.text_processor import TextProcessor

        # 分块
        if progress_callback:
            progress_callback("文本分块中...", 0.1)

        chunks = TextProcessor.split_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
        total_chunks = len(chunks)
        logger.info(f"文本已分块为 {total_chunks} 个片段")

        # 提取实体类型
        entity_types = ontology.get("entity_types", [])
        edge_types = ontology.get("edge_types", [])

        # 创建实体目录
        entities_created = 0

        # 从 ontology 中的 examples 提取实体
        if progress_callback:
            progress_callback("从本体示例中提取实体...", 0.3)

        for entity_def in entity_types:
            entity_name = entity_def.get("name", "")
            examples = entity_def.get("examples", [])

            for example in examples:
                # 创建实体文件
                self._create_entity_file(
                    name=example,
                    entity_type=entity_name,
                    description=entity_def.get("description", ""),
                    attributes=entity_def.get("attributes", [])
                )
                entities_created += 1

        # 保存 edge_types 关系定义
        edges_file = os.path.join(self.vault_path, "_relationships.md")
        with open(edges_file, 'w', encoding='utf-8') as f:
            f.write("# 关系类型定义\n\n")
            for edge in edge_types:
                f.write(f"## {edge.get('name', '')}\n")
                f.write(f"- 描述: {edge.get('description', '')}\n")
                f.write(f"- 来源→目标: {edge.get('source_targets', [])}\n\n")

        if progress_callback:
            progress_callback(f"已创建 {entities_created} 个实体文件", 1.0)

        logger.info(f"图谱构建完成: {entities_created} 个实体")

    def _create_entity_file(
        self,
        name: str,
        entity_type: str,
        description: str,
        attributes: List[Dict[str, Any]]
    ):
        """创建单个实体文件"""
        # 文件名（移除非法字符）
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
        file_path = os.path.join(self.entities_dir, f"{safe_name}.md")

        # 如果文件已存在，跳过
        if os.path.exists(file_path):
            return

        # 构建 frontmatter
        attr_dict = {attr["name"]: "" for attr in attributes}

        content = f"""---
type: {entity_type}
name: {name}
summary: {description}
attributes:
{json.dumps(attr_dict, ensure_ascii=False, indent=2)}
---

# {name}

{description}

## 属性
{chr(10).join(f"- {attr['name']}: {attr.get('description', '')}" for attr in attributes)}

## 相关关系

（从图谱构建自动生成）
"""

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def get_graph_data(self) -> Dict[str, Any]:
        """获取图谱数据（包含节点和边的详细信息）"""
        # 读取实体文件作为节点
        entity_files = [f for f in os.listdir(self.entities_dir) if f.endswith('.md')]
        node_count = len(entity_files)

        nodes_data = []
        for filename in entity_files:
            file_path = os.path.join(self.entities_dir, filename)
            entity_name = filename.replace('.md', '')
            entity_uuid = filename.replace('.md', '')

            # 读取实体内容
            summary = ""
            labels = ["Entity"]
            attributes = {}

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 解析frontmatter
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            frontmatter = parts[1]
                            body = parts[2].strip()
                            # 解析frontmatter
                            for line in frontmatter.split('\n'):
                                if ':' in line:
                                    key = line.split(':', 1)[0].strip()
                                    value = line.split(':', 1)[1].strip()
                                    if key == 'type':
                                        labels.append(value)
                                    elif key == 'name':
                                        entity_name = value
                                    elif key == 'summary':
                                        summary = value
                                    elif key == 'attributes':
                                        # 解析attributes
                                        if value.startswith('{') and value.endswith('}'):
                                            import re
                                            # 解析简单的key: value格式
                                            attr_match = re.findall(r'(\w+):\s*([^,\n]+)', value[1:-1])
                                            attributes = {k: v.strip() for k, v in attr_match}
                                    elif key == 'related':
                                        # related字段是引用，保留为attributes
                                        attributes['related'] = value
            except Exception as e:
                print(f"读取实体文件失败 {filename}: {e}")

            nodes_data.append({
                "uuid": entity_uuid,
                "name": entity_name,
                "labels": labels,
                "summary": summary,
                "attributes": attributes,
                "created_at": None,
            })

        # 为每个节点建立类型映射（labels列表）
        node_type_map = {}  # node_uuid -> entity_type
        for node in nodes_data:
            # 找到非Entity的类型作为实体类型
            for label in node['labels']:
                if label != 'Entity':
                    node_type_map[node['uuid']] = label
                    break

        # 读取edge定义并创建具体的边实例
        edges_file = os.path.join(self.vault_path, "_relationships.md")
        edge_count = 0
        edges_data = []

        if os.path.exists(edges_file):
            with open(edges_file, 'r', encoding='utf-8') as f:
                content = f.read()

                # 解析markdown中的关系
                import re
                # 匹配 ## 关系名 格式的标题
                edge_sections = re.split(r'^#{2,3}\s+', content, flags=re.MULTILINE)

                for section in edge_sections[1:]:  # 跳过第一个空部分
                    lines = section.strip().split('\n')
                    if lines:
                        edge_name = lines[0].strip()

                        # 查找源和目标实体类型
                        source_target_line = ""
                        for line in lines:
                            if '来源→目标' in line or '来源->目标' in line:
                                source_target_line = line
                                break

                        # 解析source->target列表
                        if source_target_line:
                            # 提取列表内容 [{'source': ..., 'target': ...}, ...]
                            match = re.search(r'\[(.*)\]', source_target_line)
                            if match:
                                list_str = match.group(1)

                                # 解析每个source-target对
                                pair_matches = re.findall(r"'source':\s*'([^']+)',\s*'target':\s*'([^']+)'", list_str)

                                for source_type, target_type in pair_matches:
                                    # 找出所有属于source_type类型的节点
                                    source_nodes = [n for n in nodes_data if source_type in n['labels']]
                                    # 找出所有属于target_type类型的节点
                                    target_nodes = [n for n in nodes_data if target_type in n['labels']]

                                    # 为每对节点创建边
                                    for src_node in source_nodes:
                                        for tgt_node in target_nodes:
                                            edges_data.append({
                                                "uuid": f"{src_node['uuid']}_{edge_name}_{tgt_node['uuid']}",
                                                "name": edge_name,
                                                "fact": f"{src_node['name']} -> {tgt_node['name']}: {edge_name}",
                                                "fact_type": edge_name,
                                                "source_node_uuid": src_node['uuid'],
                                                "target_node_uuid": tgt_node['uuid'],
                                                "source_node_name": src_node['name'],
                                                "target_node_name": tgt_node['name'],
                                                "created_at": None,
                                            })
                                            edge_count += 1

        # 读取 ontology 获取实体类型
        entity_types = []
        ontology_file = os.path.join(self.vault_path, "_ontology.json")
        if os.path.exists(ontology_file):
            try:
                with open(ontology_file, 'r', encoding='utf-8') as f:
                    ontology = json.load(f)
                    entity_types = [e.get("name", "") for e in ontology.get("entity_types", [])]
            except Exception as e:
                print(f"读取ontology失败: {e}")

        return ObsidianGraphInfo(
            graph_id=self.graph_id,
            node_count=node_count,
            edge_count=edge_count,
            entity_types=entity_types,
            vault_path=self.vault_path,
            nodes=nodes_data,
            edges=edges_data
        ).to_dict()

    def delete_graph(self):
        """删除图谱（删除实体文件）"""
        import shutil

        if os.path.exists(self.entities_dir):
            shutil.rmtree(self.entities_dir)
            logger.info(f"已删除图谱实体目录: {self.entities_dir}")

        # 删除 ontology 文件
        ontology_file = os.path.join(self.vault_path, "_ontology.json")
        if os.path.exists(ontology_file):
            os.remove(ontology_file)

        edges_file = os.path.join(self.vault_path, "_relationships.md")
        if os.path.exists(edges_file):
            os.remove(edges_file)
