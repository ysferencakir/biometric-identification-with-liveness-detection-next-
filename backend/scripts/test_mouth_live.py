"""
scripts/test_mouth_live.py
MouthMovementDetector webcam testi.
Calistir: python scripts/test_mouth_live.py
"""
import sys, cv2
sys.path.insert(0, ".")
from core.liveness.mouth_movement import MouthMovementDetector

det = MouthMovementDetector()
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Kamera acilamadi!"); sys.exit(1)

print("MouthMovement Test — q ile cikis")
print("Agzinizi 2 kez acip kapatin.")

while True:
    ret, frame = cap.read()
    if not ret: break

    result = det.check(frame, (0,0,0,0))
    meta   = result.metadata
    color  = (0,255,0) if result.is_live else (0,120,255)

    cv2.putText(frame, f"MAR: {meta.get('mar',0):.3f}  (ac>{0.55} kapat<{0.40})",
                (10,35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
    cv2.putText(frame, f"Ac/Kapat: {meta.get('open_close',0)}/2  Score:{result.score:.2f}",
                (10,70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200,200,200), 2)
    cv2.putText(frame, result.message, (10,105), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

    if result.is_live:
        cv2.putText(frame, "PASSED!", (10,150),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,255,0), 3)

    cv2.imshow("MouthMovement Test", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("Sonuc:", "PASSED" if result.is_live else "FAILED")
