import json
import sys

def main():
    with open('backend/scripts/audit_raw_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    target_keys = sys.argv[1:] if len(sys.argv) > 1 else list(data.keys())
    for q_code in target_keys:
        if q_code not in data:
            continue
        q_data = data[q_code]
        print("=" * 80)
        print(f"[{q_code}] Question: {q_data.get('question')}")
        print(f"Status: {q_data.get('verification_status')}")
        print(f"Refusal Reason: {q_data.get('refusal_reason')}")
        print(f"Facts Count: {len(q_data.get('facts', []))}")
        print(f"Citations Count: {len(q_data.get('citations', []))}")
        print(f"Calculations Count: {len(q_data.get('calculations', []))}")
        print(f"Elapsed Time: {q_data.get('elapsed_sec', 0):.2f}s")
        print("\n--- Answer Text ---")
        print(q_data.get('answer', ''))
        print("\n--- Top 3 Citations ---")
        for c in q_data.get('citations', [])[:3]:
            print(f"  * Doc: {c.get('document_title')} | P.{c.get('page_number')} | Excerpt: {str(c.get('excerpt'))[:120]}...")
        print()

if __name__ == '__main__':
    main()
