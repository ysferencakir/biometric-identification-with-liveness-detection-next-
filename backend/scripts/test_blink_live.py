"""
scripts/test_blink_live.py
--------------------------
BlinkDetector'ı webcam üzerinde canlı test eder.
Çalıştır: python scripts/test_blink_live.py
Çıkış: q tuşu
"""
import sys
import cv2
import numpy as np

sys.path.insert(0, ".")

from core.liveness.blink_detector import BlinkDetector

detector = BlinkDetector()
detector.reset()

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Kamera acilamadi!")
    sys.exit(1)

print("BlinkDetector Test — 'q' ile cikis")
print("Hedef: 2 goz kirpma, 8 saniye icinde")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    result = detector.check(frame, (0, 0, 0, 0))

    ear   = result.metadata.get("ear", 0)
    blink = result.metadata.get("blinks", 0)
    ela   = result.metadata.get("elapsed", 0)

    color = (0, 255, 0) if result.is_live else (0, 120, 255)

    cv2.putText(frame, f"EAR: {ear:.3f}  (esik:<0.21)",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 0), 2)
    cv2.putText(frame, f"Blinks: {blink}/2",
                (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
    cv2.putText(frame, f"Score: {result.score:.2f}  ({ela:.1f}s)",
                (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
    cv2.putText(frame, result.message,
                (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

    if result.is_live:
        cv2.putText(frame, "PASSED!", (20, 220),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 255, 0), 3)

    cv2.imshow("BlinkDetector Test", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break
    if result.is_live:
        cv2.waitKey(2000)
        break

cap.release()
cv2.destroyAllWindows()
print("Sonuc:", "PASSED" if result.is_live else "FAILED")
print("Toplam kirpma:", result.metadata.get("blinks", 0))
