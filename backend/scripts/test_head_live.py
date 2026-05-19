"""
HeadMovementDetector webcam testi.
Calistir: python scripts/test_head_live.py
"""
import sys, cv2
sys.path.insert(0, ".")
from core.liveness.head_movement import HeadMovementDetector

detector = HeadMovementDetector()
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Kamera acilamadi!"); sys.exit(1)

print("HeadMovement Test — q ile cikis")
print("Sirasi ile: saga → sola")

while True:
    ret, frame = cap.read()
    if not ret: break

    result = detector.check(frame, (0,0,0,0))

    yaw       = result.metadata.get("yaw", 0)
    completed = result.metadata.get("completed", [])
    elapsed   = result.metadata.get("elapsed", 0)
    color     = (0, 255, 0) if result.is_live else (0, 120, 255)

    cv2.putText(frame, f"YAW: {yaw:.3f}  (saga<0.38 | sola>0.62)",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255,255,0), 2)
    cv2.putText(frame, f"Tamamlanan: {completed}",
                (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.putText(frame, result.message,
                (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.putText(frame, f"Score: {result.score:.2f}  ({elapsed:.1f}s)",
                (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200,200,200), 2)

    if result.is_live:
        cv2.putText(frame, "PASSED!", (20, 220),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0,255,0), 3)

    cv2.imshow("HeadMovement Test", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"): break
    if result.is_live:
        cv2.waitKey(2000); break

cap.release()
cv2.destroyAllWindows()
print("Sonuc:", "PASSED" if result.is_live else "FAILED")
