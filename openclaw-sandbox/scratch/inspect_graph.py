import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ai.graph_store import get_graph_store


def main():
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    graph = get_graph_store(workspace_root, skill_name="knowledge_compiler")

    print("Graph store backend:", graph.__class__.__name__)

    # We can inspect the graph nodes and edges
    # For NetworkXGraphStore, self._graph is a networkx.MultiDiGraph
    nx_graph = graph._G
    print(f"Number of nodes: {nx_graph.number_of_nodes()}")
    print(f"Number of edges: {nx_graph.number_of_edges()}")

    print("\nNodes (first 20):")
    nodes = list(nx_graph.nodes(data=True))
    for node in nodes[:20]:
        print(f"  - {node[0]}: {node[1]}")

    print("\nEdges (first 20):")
    edges = list(nx_graph.edges(data=True))
    for edge in edges[:20]:
        print(f"  - {edge[0]} --({edge[2].get('relation')})--> {edge[1]}")


if __name__ == "__main__":
    main()
