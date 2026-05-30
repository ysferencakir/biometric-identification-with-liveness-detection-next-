"""
scripts/live_recognition.py
---------------------------
Real-time face recognition test client.

Usage
-----
    python scripts/live_recognition.py [--url http://localhost:8000] [--cam 0]

Controls
--------
    Q  – quit
    S  – save current frame as PNG (for debugging)

Behaviour
---------
* Sends each frame to POST /api/v1/recognize
* Green bbox + name  → recognized user
* Red bbox           → face detected but unknown
* No box             → no face / multiple faces
* FPS counter shown top-left
"""

import argparse
import base64
import time
import threading
import queue
from typing import Optional, Tuple

import cv2
import numpy as np
import requests

# ── CLI args ──────────────────────────────────────────────────────────────────

# Argparse is parsed inside main() to avoid side-effects on import

# ── Drawing helpers ───────────────────────────────────────────────────────────

GREEN = (0, 255, 0)
RED   = (0, 0, 255)
WHITE = (255, 255, 255)
FONT  = cv2.FONT_HERSHEY_SIMPLEX


def draw_bbox(
    frame: np.ndarray,
    bbox: list,         # [x, y, w, h]
    color: Tuple[int, int, int],
    label: Optional[str] = None,
    score: Optional[float] = None,
) -> None:
    x, y, w, h = bbox
    # Box
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
    # Label background + text
    if label:
        score_str = f" ({score:.2f})" if score is not None else ""
        text = f"{label}{score_str}"
        (tw, th), _ = cv2.getTextSize(text, FONT, 0.65, 2)
        cv2.rectangle(frame, (x, y - th - 10), (x + tw + 6, y), color, -1)
        cv2.putText(frame, text, (x + 3, y - 5), FONT, 0.65, (0, 0, 0), 2)


def draw_overlay(frame: np.ndarray, message: str, fps: float) -> None:
    """Draw FPS counter and status message on top of the frame."""
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 25), FONT, 0.7, WHITE, 2)
    cv2.putText(frame, message, (10, 55), FONT, 0.6, WHITE, 1)


# ── Main loop ─────────────────────────────────────────────────────────────────

def encode_frame(frame: np.ndarray) -> Optional[str]:
    """Encode a BGR frame as base64 JPEG. Returns None on failure."""
    ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ret or buf is None:
        return None
    return base64.b64encode(buf).decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Live face recognition client")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--cam", type=int, default=0, help="Camera device index")
    parser.add_argument("--fps-cap", type=int, default=15, help="Max frames sent per second")
    args = parser.parse_args()

    recognize_url = f"{args.url}/api/v1/recognize"
    frame_interval = 1.0 / args.fps_cap

    cap = cv2.VideoCapture(args.cam)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera {args.cam}")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print(f"[INFO] Connecting to {recognize_url}")
    print("[INFO] Press Q to quit, S to save frame")

    last_api_time = 0.0
    last_result: Optional[dict] = None
    fps_counter = 0
    fps_timer = time.time()
    display_fps = 0.0
    frame_idx = 0

    # Threading for non-blocking API calls
    result_queue = queue.Queue()
    request_lock = threading.Lock()
    is_requesting = False

    def api_worker(b64_string: str):
        nonlocal is_requesting
        try:
            payload = {"image_b64": b64_string}
            resp = requests.post(recognize_url, json=payload, timeout=5)
            if resp.status_code == 200:
                result_queue.put(resp.json())
        except requests.RequestException as e:
            print(f"[WARN] API error: {e}")
        finally:
            with request_lock:
                is_requesting = False

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARN] Frame capture failed, retrying...")
            time.sleep(0.05)
            continue

        now = time.time()

        # ── FPS display ───────────────────────────────────────────────────
        fps_counter += 1
        if now - fps_timer >= 1.0:
            display_fps = fps_counter / (now - fps_timer)
            fps_counter = 0
            fps_timer = now

        # ── Update results from background thread ─────────────────────────
        while not result_queue.empty():
            last_result = result_queue.get()

        # ── API call (rate-limited and non-blocking) ──────────────────────
        if now - last_api_time >= frame_interval:
            with request_lock:
                if not is_requesting:
                    b64 = encode_frame(frame)
                    if b64 is not None:
                        is_requesting = True
                        last_api_time = now
                        threading.Thread(target=api_worker, args=(b64,), daemon=True).start()

        # ── Draw result ───────────────────────────────────────────────────
        display = frame.copy()
        status_msg = "Waiting..."

        if last_result:
            r = last_result
            status_msg = r.get("message", "")

            if r.get("face_detected") and r.get("bbox"):
                bbox = r["bbox"]
                score = r.get("recognition_score", 0.0)

                if r.get("recognized"):
                    name = r.get("name", "Unknown")
                    draw_bbox(display, bbox, GREEN, label=name, score=score)
                else:
                    draw_bbox(display, bbox, RED, label="Unknown", score=score)

        draw_overlay(display, status_msg, display_fps)
        cv2.imshow("Face Recognition - press Q to quit", display)

        # ── Key handling ─────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("s"):
            fname = f"frame_{frame_idx:04d}.png"
            cv2.imwrite(fname, frame)
            print(f"[INFO] Saved {fname}")
            frame_idx += 1

    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Done.")


if __name__ == "__main__":
    main()
