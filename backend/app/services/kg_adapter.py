"""
知识图谱适配器
统一接口，支持 ZEP 和 Obsidian 两种数据源
"""

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.kg_adapter')


class KnowledgeGraphAdapter(ABC):
    """知识图谱适配器抽象基类"""

    @abstractmethod
    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """获取所有节点"""
        pass

    @abstractmethod
    def get_all_edges(self) -> List[Dict[str, Any]]:
        """获取所有边"""
        pass

    @abstractmethod
    def filter_defined_entities(
        self,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True
    ) -> Any:
        """筛选符合条件的实体"""
        pass

    @abstractmethod
    def get_entity_with_context(self, entity_uuid: str) -> Optional[Any]:
        """获取单个实体及其上下文"""
        pass

    @abstractmethod
    def get_entities_by_type(
        self,
        entity_type: str,
        enrich_with_edges: bool = True
    ) -> List[Any]:
        """获取指定类型的所有实体"""
        pass

    @abstractmethod
    def get_graph_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        pass


class ZepAdapter(KnowledgeGraphAdapter):
    """ZEP 知识图谱适配器"""

    def __init__(self, graph_id: str = "default"):
        from .zep_entity_reader import ZepEntityReader

        self.graph_id = graph_id
        self.reader = ZepEntityReader()
        logger.info(f"初始化 ZEP 适配器，图谱ID: {graph_id}")

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        return self.reader.get_all_nodes(self.graph_id)

    def get_all_edges(self) -> List[Dict[str, Any]]:
        return self.reader.get_all_edges(self.graph_id)

    def filter_defined_entities(
        self,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True
    ):
        return self.reader.filter_defined_entities(
            self.graph_id,
            defined_entity_types,
            enrich_with_edges
        )

    def get_entity_with_context(self, entity_uuid: str):
        return self.reader.get_entity_with_context(self.graph_id, entity_uuid)

    def get_entities_by_type(
        self,
        entity_type: str,
        enrich_with_edges: bool = True
    ) -> List[Any]:
        return self.reader.get_entities_by_type(
            self.graph_id,
            entity_type,
            enrich_with_edges
        )

    def get_graph_statistics(self) -> Dict[str, Any]:
        """ZEP 统计信息需要通过 API 获取"""
        # ZEP 没有直接的统计接口，返回基本信息
        nodes = self.get_all_nodes()
        edges = self.get_all_edges()
        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "source": "zep"
        }


class ObsidianAdapter(KnowledgeGraphAdapter):
    """Obsidian 本地知识库适配器"""

    def __init__(self):
        from .obsidian_reader import ObsidianVaultReader

        self.reader = ObsidianVaultReader()
        logger.info("初始化 Obsidian 适配器")

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        return self.reader.get_all_nodes()

    def get_all_edges(self) -> List[Dict[str, Any]]:
        return self.reader.get_all_edges()

    def filter_defined_entities(
        self,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True
    ):
        return self.reader.filter_defined_entities(
            defined_entity_types,
            enrich_with_edges
        )

    def get_entity_with_context(self, entity_uuid: str):
        return self.reader.get_entity_with_context(entity_uuid)

    def get_entities_by_type(
        self,
        entity_type: str,
        enrich_with_edges: bool = True
    ) -> List[Any]:
        return self.reader.get_entities_by_type(
            entity_type,
            enrich_with_edges
        )

    def get_graph_statistics(self) -> Dict[str, Any]:
        stats = self.reader.get_graph_statistics()
        stats["source"] = "obsidian"
        return stats


class KnowledgeGraphFactory:
    """知识图谱工厂类，自动选择数据源"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._adapter = None
        return cls._instance

    def get_adapter(self, graph_id: str = "default") -> KnowledgeGraphAdapter:
        """
        获取知识图谱适配器

        优先级：
        1. 如果配置了 OBSIDIAN_VAULT_PATH，使用 Obsidian
        2. 否则使用 ZEP

        Args:
            graph_id: ZEP 图谱ID（仅 ZEP 需要）

        Returns:
            KnowledgeGraphAdapter 实例
        """
        if self._adapter is not None:
            return self._adapter

        # 优先使用 Obsidian
        if Config.OBSIDIAN_VAULT_PATH:
            logger.info("使用 Obsidian 作为知识图谱数据源")
            self._adapter = ObsidianAdapter()
        elif Config.ZEP_API_KEY:
            logger.info("使用 ZEP 作为知识图谱数据源")
            self._adapter = ZepAdapter(graph_id)
        else:
            raise ValueError("未配置知识图谱数据源，请配置 ZEP_API_KEY 或 OBSIDIAN_VAULT_PATH")

        return self._adapter

    def reset(self):
        """重置适配器实例（用于切换数据源）"""
        self._adapter = None


def get_knowledge_graph(graph_id: str = "default") -> KnowledgeGraphAdapter:
    """
    获取知识图谱适配器的便捷函数

    Args:
        graph_id: ZEP 图谱ID（仅 ZEP 需要）

    Returns:
        KnowledgeGraphAdapter 实例
    """
    factory = KnowledgeGraphFactory()
    return factory.get_adapter(graph_id)
