import os
import sys

# Add workspace root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ai.hybrid_retriever import HybridRetriever


def main():
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print(f"Initializing HybridRetriever with workspace_root: {workspace_root}")

    import logging

    logging.basicConfig(level=logging.INFO)

    retriever = HybridRetriever(workspace_root=workspace_root)

    # Test query
    question = "非功能性流程模擬"
    print(f"\nQuerying: '{question}'...")
    try:
        # Let's inspect the graph first in the script
        g = retriever._get_graph()
        print(f"Graph loaded with {len(g._G.nodes())} nodes.")

        results = retriever.query(question, top_n=3)
        print("\nResults:")
        for idx, res in enumerate(results):
            print(
                f"[{idx + 1}] Score: {res.get('score'):.4f} | Origin: {res.get('origin')} | Source: {res.get('source')}"
            )
            print(f"    Text: {res.get('text')[:200]}...")
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
