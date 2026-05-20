"""
scripts/test_performance.py
-----------------------------
Performans metrikleri:
  - Frame isleme suresi (liveness/submit latency)
  - Recognize latency
  - Session olusturma suresi
  - FAR/FRR icin aciklama

Calistir: python scripts/test_performance.py
Backend 8000'de calisıyor olmali.
"""

import sys, time, base64, statistics
import numpy as np
import cv2
import requests

BASE = "http://127.0.0.1:8000/api/v1"

def b64(img):
    _, buf = cv2.imencode(".jpg", img)
    return base64.b64encode(buf).decode()

def blank(w=640, h=480):
    return np.zeros((h, w, 3), dtype=np.uint8)

def webcam_frame():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return blank()
    for _ in range(5):
        ret, frame = cap.read()
    cap.release()
    return frame if ret else blank()


print("\n=== Sprint 4 — Performans Metrikleri ===\n")

N = 10  # her test icin tekrar sayisi

# ── 1. Session Olusturma Latency ──────────────────────────────────────────────
print("1. Session Olusturma Latency")
times = []
for _ in range(N):
    t0 = time.monotonic()
    r = requests.post(f"{BASE}/session/create", json={}, timeout=10)
    times.append((time.monotonic() - t0) * 1000)
    assert r.status_code == 200

print(f"   N={N} | Ort: {statistics.mean(times):.0f}ms | Min: {min(times):.0f}ms | Max: {max(times):.0f}ms")
target = 200
print(f"   Hedef: <{target}ms | {'PASS' if statistics.mean(times) < target else 'FAIL'}")

# ── 2. Liveness Submit Latency (bos frame) ────────────────────────────────────
print("\n2. Liveness Submit Latency (yuzsuz frame)")
sess = requests.post(f"{BASE}/session/create", json={}, timeout=5).json()
sid  = sess["session_id"]
ch   = sess["challenges"][0]
frame_b64 = b64(blank())
times = []
for _ in range(N):
    t0 = time.monotonic()
    r = requests.post(f"{BASE}/liveness/submit",
                      json={"session_id": sid, "challenge_name": ch, "frame": frame_b64},
                      timeout=15)
    times.append((time.monotonic() - t0) * 1000)
    assert r.status_code == 200

print(f"   N={N} | Ort: {statistics.mean(times):.0f}ms | Min: {min(times):.0f}ms | Max: {max(times):.0f}ms")
target = 500
print(f"   Hedef: <{target}ms | {'PASS' if statistics.mean(times) < target else 'FAIL'}")

# ── 3. Webcam Frame Latency ───────────────────────────────────────────────────
print("\n3. Liveness Submit Latency (gercek kamera frame)")
wframe = webcam_frame()
wframe_b64 = b64(wframe)
print(f"   Frame boyutu: {len(wframe_b64) // 1024} KB")

sess2 = requests.post(f"{BASE}/session/create", json={}, timeout=5).json()
sid2  = sess2["session_id"]
ch2   = sess2["challenges"][0]
times2 = []
for _ in range(5):
    t0 = time.monotonic()
    r = requests.post(f"{BASE}/liveness/submit",
                      json={"session_id": sid2, "challenge_name": ch2, "frame": wframe_b64},
                      timeout=15)
    times2.append((time.monotonic() - t0) * 1000)
    assert r.status_code == 200

print(f"   N=5  | Ort: {statistics.mean(times2):.0f}ms | Min: {min(times2):.0f}ms | Max: {max(times2):.0f}ms")
target = 500
print(f"   Hedef: <{target}ms | {'PASS' if statistics.mean(times2) < target else 'FAIL'}")

# ── 4. Recognize Latency ──────────────────────────────────────────────────────
print("\n4. Recognize Latency")
times3 = []
for _ in range(5):
    t0 = time.monotonic()
    r = requests.post(f"{BASE}/recognize", json={"image_b64": wframe_b64}, timeout=15)
    times3.append((time.monotonic() - t0) * 1000)
    assert r.status_code == 200
    d = r.json()

print(f"   N=5  | Ort: {statistics.mean(times3):.0f}ms | face_detected={d['face_detected']} recognized={d['recognized']}")
target = 1000
print(f"   Hedef: <{target}ms | {'PASS' if statistics.mean(times3) < target else 'FAIL'}")

# ── 5. FAR / FRR Aciklama ────────────────────────────────────────────────────
print("\n5. FAR / FRR — Bilgi")
users = requests.get(f"{BASE}/users", timeout=5).json()
print(f"   Kayitli kullanici: {users['count']}")
print("""
   FAR (False Accept Rate): Yetkisiz kullanicinin kabul edilme orani.
   FRR (False Rejection Rate): Yetkili kullanicinin reddedilme orani.

   Manuel test icin:
     - Kayitli kullanici ile /verify → GRANTED bekleniyor (FRR testi)
     - Kayitsiz biri ile /verify → DENIED bekleniyor (FAR testi)
     - Fotoğraf ile /verify → DENIED bekleniyor (spoofing testi)

   Otomatik FAR/FRR: birden fazla kayitli kullanici + test seti gerektirir.
   Bu prototip icin manuel test yeterlidir (hedef: FAR<5%, FRR<10%).
""")

# ── Ozet ─────────────────────────────────────────────────────────────────────
print("="*45)
print("OZET")
print(f"  Session olusturma:  {statistics.mean(times):.0f}ms  (hedef <200ms)")
print(f"  Liveness (bos):     {statistics.mean(times):.0f}ms  (hedef <500ms)")
print(f"  Liveness (kamera):  {statistics.mean(times2):.0f}ms  (hedef <500ms)")
print(f"  Recognize:          {statistics.mean(times3):.0f}ms  (hedef <1000ms)")
print("="*45)
