import sys
import json
import urllib.request
import urllib.error
import time

sys.stdout.reconfigure(encoding='utf-8')


BASE_URL = "http://localhost:8000/api/v1"

def login(username, password):
    url = f"{BASE_URL}/auth/login"
    data = f"username={username}&password={password}".encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "KOYLA-Verification/1.0"}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("access_token")

def get_status():
    url = f"{BASE_URL}/qa/status"
    req = urllib.request.Request(url, headers={"User-Agent": "KOYLA-Verification/1.0"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def query_qa(token, query, org_id=None, fiscal_year=None, top_k=5):
    url = f"{BASE_URL}/qa/query"
    payload = {
        "query": query,
        "organization_id": org_id,
        "fiscal_year": fiscal_year,
        "top_k": top_k,
        "enable_reranker": True
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "KOYLA-Verification/1.0"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body

def main():
    print("=" * 60)
    print("KOYLA PHASE 6 LIVE AUDIT & VERIFICATION SUITE")
    print("=" * 60)

    # 1. Status Check
    print("\n--- 1. QA & LOCAL LLM STATUS ---")
    status = get_status()
    print(json.dumps(status, indent=2))
    assert status["status"] == "OPERATIONAL"
    assert status["llm"]["is_healthy"] is True
    assert status["llm"]["is_local"] is True
    assert status["llm"]["model_name"] == "SmolLM2-135M-Instruct"

    # 2. Login Central User
    print("\n--- 2. AUTHENTICATION ---")
    admin_token = login("hq_officer", "Admin123!")
    print(f"Logged in as hq_officer (token length: {len(admin_token)})")

    ecl_token = login("ecl_analyst", "Password123!")
    print(f"Logged in as ecl_analyst (token length: {len(ecl_token)})")

    # 3. Grounded Question (Actual Neural Generation)
    print("\n--- 3. GROUNDED QUESTION (ACTUAL LOCAL LLM GENERATION) ---")
    code, res3 = query_qa(
        admin_token,
        "What is the geological coal reserve or production reported for ECL?",
        top_k=3
    )
    print(f"HTTP {code}")
    print(f"Query: {res3.get('query')}")
    print(f"Answer: {res3.get('answer')}")
    print(f"LLM Status: {res3.get('llm_status')}")
    print(f"LLM Provider: {res3.get('llm_provider')}")
    print(f"LLM Model: {res3.get('llm_model')}")
    print(f"Verification: {res3.get('verification_status')}")
    print(f"Confidence: {res3.get('confidence_score')}")
    print(f"Citations count: {len(res3.get('citations', []))}")
    for c in res3.get('citations', [])[:2]:
        print(f"  - [{c.get('citation_index')}] {c.get('document_title')} (Page {c.get('page_number')})")

    # 4. Refusal on Unsupported / Off-Topic Question
    print("\n--- 4. REFUSAL ON UNSUPPORTED / OFF-TOPIC QUESTION ---")
    code, res4 = query_qa(
        admin_token,
        "What was the flight trajectory of the Apollo 11 moon mission?",
        top_k=3
    )
    print(f"HTTP {code}")
    print(f"Query: {res4.get('query')}")
    print(f"Answer: {res4.get('answer')}")
    print(f"Verification: {res4.get('verification_status')}")
    assert "Insufficient verified evidence found" in res4.get('answer')

    # 5. Deterministic Arithmetic (YoY comparison)
    print("\n--- 5. DETERMINISTIC ARITHMETIC (YOY PRODUCTION) ---")
    code, res5 = query_qa(
        admin_token,
        "What is the year over year production change from FY2022-23 to FY2023-24?",
        top_k=3
    )
    print(f"HTTP {code}")
    print(f"Query: {res5.get('query')}")
    print(f"Answer: {res5.get('answer')}")
    print(f"Arithmetic Used: {res5.get('arithmetic_used')}")
    print(f"Calculations: {res5.get('calculations')}")

    # 6. Organization Scope Security Isolation
    print("\n--- 6. ORGANIZATION SECURITY ISOLATION ---")
    # ecl_analyst attempts to query BCCL or an unauthorized scope
    code, res6 = query_qa(
        ecl_token,
        "What is the coal production in BCCL mines?",
        org_id="00000000-0000-0000-0000-000000000000" # Explicit invalid / unauthorized org id
    )
    print(f"Unauthorized Org Query Result: HTTP {code}")
    print(f"Detail: {res6}")
    assert code == 403, f"Expected HTTP 403, got {code}"

    print("\n" + "=" * 60)
    print("ALL VERIFICATION SUITE TESTS EXECUTED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    main()
