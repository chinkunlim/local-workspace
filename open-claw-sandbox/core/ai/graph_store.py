"""
core/graph_store.py — Knowledge Graph Abstraction Layer (P3-1)
=============================================================
Provides a unified GraphStore interface over two backends:
  - NetworkX  (local / dev / test — zero external dependencies beyond networkx)
  - Neo4j     (production — requires neo4j Python driver + a running Neo4j instance)

The active backend is selected at runtime from config.yaml:
    graph:
      backend: "networkx"   # or "neo4j"
      neo4j:
        uri: "bolt://localhost:7687"
        user: "neo4j"
        password: "password"
      persist_path: "state/graph.gpickle"   # for NetworkX backend

Usage:
    from core.ai.graph_store import get_graph_store
    gs = get_graph_store(workspace_root, skill_name="knowledge_compiler")

    gs.upsert_entity("認知心理學", labels=["Concept", "Psychology"], props={"source": "notes.md"})
    gs.upsert_relation("認知心理學", "RELATED_TO", "工作記憶")
    neighbours = gs.get_neighbours("認知心理學", max_hops=1)
    # [{"name": "工作記憶", "relation": "RELATED_TO"}, ...]

Requirements (install only what you need):
    pip install networkx                      # always safe
    pip install neo4j                         # only for production backend
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

_logger = logging.getLogger("OpenClaw.GraphStore")


# ---------------------------------------------------------------------------
# Protocol (Interface)
# ---------------------------------------------------------------------------


@runtime_checkable
class GraphStore(Protocol):
    """Minimal graph store interface consumed by hybrid_retriever and graph pipelines."""

    def upsert_entity(
        self, name: str, labels: List[str], props: Optional[Dict[str, Any]] = None
    ) -> None: ...
    def upsert_relation(
        self, src: str, rel: str, dst: str, props: Optional[Dict[str, Any]] = None
    ) -> None: ...
    def get_neighbours(self, name: str, max_hops: int = 1) -> List[Dict[str, Any]]: ...
    def entity_exists(self, name: str) -> bool: ...
    def close(self) -> None: ...


# ---------------------------------------------------------------------------
# NetworkX Backend  (local / dev)
# ---------------------------------------------------------------------------


class NetworkXGraphStore:
    """In-process graph backed by NetworkX DiGraph.

    Entities → nodes with arbitrary attribute dicts.
    Relations → directed edges with a ``rel`` attribute.
    State is optionally persisted to disk via pickle on close().
    """

    def __init__(self, persist_path: Optional[str] = None):
        try:
            import networkx as nx  # type: ignore[import]

            self._nx = nx
        except ImportError as exc:
            raise ImportError(
                "networkx is required for the local GraphStore backend. Run: pip install networkx"
            ) from exc

        self._persist_path = persist_path
        self._lock = threading.RLock()
        self._G: Any = None
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._persist_path and os.path.exists(self._persist_path):
            try:
                import pickle

                with open(self._persist_path, "rb") as f:
                    self._G = pickle.load(f)
                _logger.info("[GraphStore/NX] Loaded graph from %s", self._persist_path)
                return
            except Exception as exc:
                _logger.warning("[GraphStore/NX] Failed to load graph: %s — starting fresh.", exc)
        self._G = self._nx.DiGraph()

    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            import pickle

            os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
            tmp = self._persist_path + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump(self._G, f)
            os.replace(tmp, self._persist_path)
        except Exception as exc:
            _logger.warning("[GraphStore/NX] Failed to persist graph: %s", exc)

    # ── Interface ─────────────────────────────────────────────────────────

    def upsert_entity(
        self, name: str, labels: List[str], props: Optional[Dict[str, Any]] = None
    ) -> None:
        with self._lock:
            attrs = dict(props or {})
            attrs["labels"] = labels
            if self._G.has_node(name):
                self._G.nodes[name].update(attrs)
            else:
                self._G.add_node(name, **attrs)
            self._persist()

    def upsert_relation(
        self, src: str, rel: str, dst: str, props: Optional[Dict[str, Any]] = None
    ) -> None:
        with self._lock:
            # Auto-create nodes if they don't exist
            for node in (src, dst):
                if not self._G.has_node(node):
                    self._G.add_node(node, labels=["Entity"])
            attrs = dict(props or {})
            attrs["rel"] = rel
            self._G.add_edge(src, dst, **attrs)
            self._persist()

    def get_neighbours(self, name: str, max_hops: int = 1) -> List[Dict[str, Any]]:
        """Return all nodes reachable within max_hops, with their relation labels."""
        with self._lock:
            if not self._G.has_node(name):
                return []
            results: List[Dict[str, Any]] = []
            visited = {name}
            frontier = {name}
            for _ in range(max_hops):
                next_frontier: set = set()
                for node in frontier:
                    for _, neighbour, edge_data in self._G.out_edges(node, data=True):
                        if neighbour not in visited:
                            visited.add(neighbour)
                            next_frontier.add(neighbour)
                            results.append(
                                {
                                    "name": neighbour,
                                    "relation": edge_data.get("rel", "RELATED_TO"),
                                    "props": {k: v for k, v in edge_data.items() if k != "rel"},
                                }
                            )
                    # Also traverse reverse edges (incoming)
                    for predecessor, _, edge_data in self._G.in_edges(node, data=True):
                        if predecessor not in visited:
                            visited.add(predecessor)
                            next_frontier.add(predecessor)
                            results.append(
                                {
                                    "name": predecessor,
                                    "relation": f"←{edge_data.get('rel', 'RELATED_TO')}",
                                    "props": {},
                                }
                            )
                frontier = next_frontier
            return results

    def entity_exists(self, name: str) -> bool:
        with self._lock:
            return self._G.has_node(name)

    def close(self) -> None:
        self._persist()

    @property
    def node_count(self) -> int:
        return self._G.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._G.number_of_edges()


# ---------------------------------------------------------------------------
# Neo4j Backend  (production)
# ---------------------------------------------------------------------------


class Neo4jGraphStore:
    """Production graph backed by a Neo4j Bolt connection.

    Requires: pip install neo4j
    Configure in config.yaml:
        graph:
          backend: neo4j
          neo4j:
            uri: "bolt://localhost:7687"
            user: "neo4j"
            password: "your_password"
    """

    def __init__(self, uri: str, user: str, password: str):
        try:
            from neo4j import GraphDatabase  # type: ignore[import]

            self._driver = GraphDatabase.driver(uri, auth=(user, password))
        except ImportError as exc:
            raise ImportError(
                "neo4j driver is required for the production GraphStore backend. "
                "Run: pip install neo4j"
            ) from exc
        _logger.info("[GraphStore/Neo4j] Connected to %s", uri)

    def upsert_entity(
        self, name: str, labels: List[str], props: Optional[Dict[str, Any]] = None
    ) -> None:
        label_str = ":".join(labels) if labels else "Entity"
        cypher = f"MERGE (n:{label_str} {{name: $name}}) SET n += $props"
        with self._driver.session() as s:
            s.run(cypher, name=name, props=props or {})

    def upsert_relation(
        self, src: str, rel: str, dst: str, props: Optional[Dict[str, Any]] = None
    ) -> None:
        # Sanitize rel to valid Cypher relationship type
        rel_safe = rel.replace(" ", "_").upper()
        cypher = (
            "MERGE (a {name: $src}) "
            "MERGE (b {name: $dst}) "
            f"MERGE (a)-[r:{rel_safe}]->(b) "
            "SET r += $props"
        )
        with self._driver.session() as s:
            s.run(cypher, src=src, dst=dst, props=props or {})

    def get_neighbours(self, name: str, max_hops: int = 1) -> List[Dict[str, Any]]:
        cypher = (
            f"MATCH (a {{name: $name}})-[r*1..{max_hops}]-(b) "
            "RETURN b.name AS name, type(r[-1]) AS relation"
        )
        with self._driver.session() as s:
            result = s.run(cypher, name=name)
            return [{"name": rec["name"], "relation": rec["relation"]} for rec in result]

    def entity_exists(self, name: str) -> bool:
        with self._driver.session() as s:
            result = s.run("MATCH (n {name: $name}) RETURN count(n) AS c", name=name)
            return result.single()["c"] > 0

    def close(self) -> None:
        self._driver.close()
        _logger.info("[GraphStore/Neo4j] Connection closed.")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_graph_store(workspace_root: str, skill_name: str = "knowledge_compiler") -> Any:
    """Instantiate and return the configured GraphStore backend.

    Reads config from skills/<skill_name>/config/config.yaml under the
    ``graph:`` section. Falls back to NetworkX if no config is present.

    Args:
        workspace_root: Absolute path to the sandbox root.
        skill_name:     Skill whose config.yaml is consulted.

    Returns:
        A GraphStore-compatible instance (NetworkXGraphStore or Neo4jGraphStore).
    """
    # Lazy import to avoid circular dependency
    import sys

    sys.path.insert(0, workspace_root)
    from core.config.config_manager import ConfigManager  # type: ignore[import]

    cfg_mgr = ConfigManager(workspace_root, skill_name)
    graph_cfg: Dict[str, Any] = cfg_mgr.get_section("graph") or {}
    backend = graph_cfg.get("backend", "networkx").lower()

    if backend == "neo4j":
        neo_cfg = graph_cfg.get("neo4j", {})
        return Neo4jGraphStore(
            uri=neo_cfg.get("uri", "bolt://localhost:7687"),
            user=neo_cfg.get("user", "neo4j"),
            password=neo_cfg.get("password", ""),
        )

    # Default: NetworkX
    persist_path = graph_cfg.get(
        "persist_path",
        os.path.join(workspace_root, "skills", skill_name, "data", "state", "graph.gpickle"),
    )
    return NetworkXGraphStore(persist_path=persist_path)
