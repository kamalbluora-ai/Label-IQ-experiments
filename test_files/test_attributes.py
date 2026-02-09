import asyncio
import json
from pathlib import Path
from compliance.attributes_orchestrator import AttributeOrchestrator


def load_docai_output(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


async def main():
    json_path = Path(__file__).parent / "ex2_doc_ai_output.json"
    print(f"Loading: {json_path}")
    
    label_facts = load_docai_output(json_path)
    
    orchestrator = AttributeOrchestrator()
    results = await orchestrator.evaluate(label_facts)
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
