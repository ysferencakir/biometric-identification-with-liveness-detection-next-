"""
scripts/test_e2e.py
--------------------
E2E otomatik test senaryolari.
Backend 8000'de calisıyor olmali.
Calistir: python scripts/test_e2e.py
"""

import sys, base64, json
import numpy as np
import cv2
import requests

BASE = "http://127.0.0.1:8000/api/v1"
results = []

def ok(name):
    print(f"  PASS {name}")
    results.append((name, True, ""))

def fail(name, err):
    print(f"  FAIL {name}: {err}")
    results.append((name, False, str(err)))

def test(name, fn):
    try:
        fn()
        ok(name)
    except AssertionError as e:
        fail(name, e)
    except Exception as e:
        fail(name, f"{type(e).__name__}: {e}")

def b64(img):
    _, buf = cv2.imencode(".jpg", img)
    return base64.b64encode(buf).decode()

def blank():
    return np.zeros((480, 640, 3), dtype=np.uint8)


print("\n=== Sprint 4 - E2E Test Senaryolari ===\n")

# 1. Saglık
print("1. Sistem Saglik")
test("GET /health -> ok",           lambda: (setattr(sys, '_r', requests.get(f"{BASE}/health", timeout=5)) or True) and requests.get(f"{BASE}/health", timeout=5).json()["status"] == "ok" or (_ for _ in ()).throw(AssertionError("status != ok")))

# Daha temiz versiyon
def t_health():
    r = requests.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200 and r.json()["status"] == "ok"

def t_available():
    r = requests.get(f"{BASE}/liveness/available", timeout=5)
    assert r.status_code == 200
    dets = r.json()["detectors"]
    assert len(dets) >= 2, f"En az 2 detector bekleniyor, {len(dets)} var"
    print(f"     Detectors: {[d['name'] for d in dets]}")

test("GET /health", t_health)
test("GET /liveness/available (>=2 detector)", t_available)

# 2. Kayit
print("\n2. Kullanici Kaydi")

def t_register_empty():
    r = requests.post(f"{BASE}/register", json={"name": "X", "frames": []}, timeout=5)
    assert r.status_code == 422, f"422 bekleniyor, {r.status_code} geldi"

def t_register_blank():
    frames = [b64(blank()) for _ in range(5)]
    r = requests.post(f"{BASE}/register", json={"name": "Blank", "frames": frames}, timeout=10)
    assert r.status_code == 422, f"422 bekleniyor, {r.status_code} geldi"

test("Register: bos frame -> 422", t_register_empty)
test("Register: yuzsuz frame -> 422", t_register_blank)

# 3. Session
print("\n3. Session Yonetimi")
SID = [None]

def t_session_create():
    r = requests.post(f"{BASE}/session/create", json={}, timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert len(d["challenges"]) == 2, f"2 challenge bekleniyor: {d['challenges']}"
    SID[0] = d["session_id"]
    print(f"     Session: {SID[0][:8]}... | {d['challenges']}")

def t_session_get():
    r = requests.get(f"{BASE}/session/{SID[0]}", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "active"
    assert d["completed_challenges"] == []

def t_session_404():
    r = requests.get(f"{BASE}/session/bad-id", timeout=5)
    assert r.status_code == 404

test("POST /session/create (2 challenge)", t_session_create)
test("GET /session/{id} (active)", t_session_get)
test("GET /session/bad-id -> 404", t_session_404)

# 4. Liveness Submit
print("\n4. Liveness Submit")

def t_liveness_blank():
    r = requests.get(f"{BASE}/session/{SID[0]}", timeout=5)
    ch = r.json()["challenges"][0]
    body = {"session_id": SID[0], "challenge_name": ch, "frame": b64(blank())}
    r2 = requests.post(f"{BASE}/liveness/submit", json=body, timeout=10)
    assert r2.status_code == 200
    d = r2.json()
    assert d["passed"] == False, "Bos frame'de passed=False bekleniyor"
    print(f"     Challenge={ch} passed={d['passed']} msg={d['instruction'][:30]}")

def t_liveness_bad_challenge():
    body = {"session_id": SID[0], "challenge_name": "nonexistent", "frame": b64(blank())}
    r = requests.post(f"{BASE}/liveness/submit", json=body, timeout=5)
    assert r.status_code == 400

def t_liveness_bad_session():
    body = {"session_id": "bad", "challenge_name": "blink", "frame": b64(blank())}
    r = requests.post(f"{BASE}/liveness/submit", json=body, timeout=5)
    assert r.status_code == 404

test("Liveness: yuzsuz frame -> passed=False", t_liveness_blank)
test("Liveness: gecersiz challenge -> 400", t_liveness_bad_challenge)
test("Liveness: gecersiz session -> 404", t_liveness_bad_session)

# 5. Verify
print("\n5. Verify")

def t_verify_before_liveness():
    body = {"session_id": SID[0], "frame": b64(blank())}
    r = requests.post(f"{BASE}/verify", json=body, timeout=5)
    assert r.status_code == 400, f"400 bekleniyor, {r.status_code} geldi"

test("Verify: liveness bitmeden -> 400", t_verify_before_liveness)

# 6. Users
print("\n6. Kullanici API")

def t_list_users():
    r = requests.get(f"{BASE}/users", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert "count" in d
    print(f"     Kayitli kullanici: {d['count']}")

def t_delete_404():
    r = requests.delete(f"{BASE}/users/nonexistent-id", timeout=5)
    assert r.status_code == 404

test("GET /users", t_list_users)
test("DELETE /users/nonexistent -> 404", t_delete_404)

# Sonuc
passed = sum(1 for _, ok_, _ in results if ok_)
total  = len(results)
print(f"\n{'='*40}")
print(f"Sonuc: {passed}/{total} PASSED")
if passed < total:
    for name, ok_, err in results:
        if not ok_:
            print(f"  FAIL: {name} — {err}")
print(f"{'='*40}\n")
sys.exit(0 if passed == total else 1)
