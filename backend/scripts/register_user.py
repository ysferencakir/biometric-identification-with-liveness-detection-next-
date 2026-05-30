"""
scripts/register_user.py
------------------------
Interactive user registration script.

Usage
-----
    python scripts/register_user.py --name "Mithat" [--url http://localhost:8000] [--cam 0]

Workflow
--------
1. Opens the camera.
2. Waits until it captures REGISTER_FRAMES_REQUIRED frames where:
   - A single face is detected (client-side pre-check via Haar cascade for speed)
   - Press SPACE to manually capture a frame
   - OR enable auto-capture mode with --auto
3. Sends all captured frames to POST /api/v1/register.
4. Prints the registration result.

Controls
--------
    SPACE – capture frame manually
    Q     – quit without registering
    A     – toggle auto-capture
"""

import argparse
import base64
import time
from typing import List, Optional

import cv2
import numpy as np
import requests

# ── CLI ───────────────────────────────────────────────────────────────────────

# Argparse is parsed inside main() to avoid side-effects on import

REGISTER_URL_TEMPLATE = "{url}/api/v1/register"

# ── Helpers ───────────────────────────────────────────────────────────────────

# Lightweight Haar cascade for client-side face pre-check
_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
_cascade = cv2.CascadeClassifier(_cascade_path)
if _cascade.empty():
    import warnings
    warnings.warn("Haar cascade not found; face pre-check disabled", RuntimeWarning)
    _cascade = None

FONT  = cv2.FONT_HERSHEY_SIMPLEX
GREEN = (0, 255, 0)
BLUE  = (255, 100, 0)
WHITE = (255, 255, 255)
GRAY  = (180, 180, 180)


def has_single_face_haar(frame: np.ndarray) -> bool:
    """Quick client-side check: exactly one face via Haar cascade."""
    if _cascade is None or _cascade.empty():
        return True  # Skip pre-check if cascade unavailable; let backend decide
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = _cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    return len(faces) == 1


def encode_frame(frame: np.ndarray) -> Optional[str]:
    """Encode a BGR frame as base64 JPEG. Returns None on failure."""
    ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ret or buf is None:
        return None
    return base64.b64encode(buf).decode("utf-8")


def draw_ui(
    frame: np.ndarray,
    captured: int,
    target: int,
    auto: bool,
    face_ok: bool,
    status: str,
    user_name: str,
) -> np.ndarray:
    display = frame.copy()
    h, w = display.shape[:2]

    # Progress bar background
    bar_x, bar_y, bar_w, bar_h = 10, h - 40, w - 20, 20
    cv2.rectangle(display, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), -1)
    filled = int(bar_w * (captured / target))
    cv2.rectangle(display, (bar_x, bar_y), (bar_x + filled, bar_y + bar_h), GREEN, -1)
    cv2.putText(display, f"{captured}/{target} frames", (bar_x + 5, bar_y + 15), FONT, 0.5, WHITE, 1)

    # Face indicator
    face_color = GREEN if face_ok else (0, 0, 255)
    face_text = "Face OK" if face_ok else "No Face"
    cv2.putText(display, face_text, (10, 30), FONT, 0.8, face_color, 2)

    # Mode
    mode_text = "[A] AUTO ON" if auto else "[A] auto off | [SPACE] capture"
    cv2.putText(display, mode_text, (10, 60), FONT, 0.55, GRAY, 1)

    # Status
    cv2.putText(display, status, (10, 90), FONT, 0.55, WHITE, 1)

    # User name
    cv2.putText(display, f"Registering: {user_name}", (10, 120), FONT, 0.6, BLUE, 2)

    return display


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="User registration script")
    parser.add_argument("--name", required=True, help="Name of the user to register")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--cam", type=int, default=0, help="Camera device index")
    parser.add_argument("--frames", type=int, default=7, help="Number of frames to collect")
    parser.add_argument("--auto", action="store_true", help="Auto-capture frames (1/sec)")
    args = parser.parse_args()

    register_url = f"{args.url}/api/v1/register"
    target_frames = max(3, min(args.frames, 10))  # clamp [3, 10]

    cap = cv2.VideoCapture(args.cam)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera {args.cam}")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    captured_frames: List[str] = []
    auto_capture = args.auto
    last_auto_time = 0.0
    status_msg = "Ready – position your face in the frame"

    print(f"[INFO] Registering user: {args.name}")
    print(f"[INFO] Target frames  : {target_frames}")
    print(f"[INFO] Auto-capture   : {auto_capture}")
    print("[INFO] Controls: SPACE=capture | A=toggle auto | Q=quit")

    while len(captured_frames) < target_frames:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue

        face_ok = has_single_face_haar(frame)
        now = time.time()

        # Auto capture: 1 frame per second when face is good
        capture_now = False
        if auto_capture and face_ok and (now - last_auto_time >= 1.0):
            capture_now = True
            last_auto_time = now

        display = draw_ui(
            frame, len(captured_frames), target_frames,
            auto_capture, face_ok, status_msg, args.name,
        )
        cv2.imshow(f"Register: {args.name} - press Q to cancel", display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            print("[INFO] Registration cancelled by user.")
            cap.release()
            cv2.destroyAllWindows()
            return

        if key == ord("a"):
            auto_capture = not auto_capture
            print(f"[INFO] Auto-capture: {auto_capture}")

        if key == ord(" ") and face_ok:
            capture_now = True

        if capture_now:
            b64 = encode_frame(frame)
            if b64 is not None:
                captured_frames.append(b64)
                status_msg = f"Captured {len(captured_frames)}/{target_frames}"
                print(f"[INFO] {status_msg}")
            else:
                print("[WARN] Frame encode failed, skipping")
        elif key == ord(" ") and not face_ok:
            status_msg = "No face detected – adjust position"

    cap.release()
    cv2.destroyAllWindows()

    # ── Send to backend ───────────────────────────────────────────────────────
    print(f"[INFO] Sending {len(captured_frames)} frames to {register_url}...")
    payload = {"name": args.name, "frames": captured_frames}

    try:
        resp = requests.post(register_url, json=payload, timeout=60)
        result = resp.json()
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to backend at {register_url}")
        print("[ERROR] Make sure the backend is running: python main.py")
        return
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return

    if resp.status_code == 200 and result.get("success"):
        print("\n[SUCCESS] Registration successful!")
        print(f"   Name      : {result['name']}")
        print(f"   User ID   : {result['user_id']}")
        print(f"   Frames used: {result['frames_used']}")
    else:
        print(f"\n[FAILED] Registration failed (HTTP {resp.status_code})")
        print(f"   Detail: {result.get('detail') or result.get('message')}")


if __name__ == "__main__":
    main()
