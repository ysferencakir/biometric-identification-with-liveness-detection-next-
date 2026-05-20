"""
scripts/test_texture_live.py
-----------------------------
TextureAnalyzer webcam testi.
Calistir: python scripts/test_texture_live.py
"""
import sys, cv2
sys.path.insert(0, ".")
from core.liveness.texture_analyzer import TextureAnalyzer

det = TextureAnalyzer()
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Kamera acilamadi!"); sys.exit(1)

print("TextureAnalyzer Test — q ile cikis")
print("Kameraya duz bakin, hareketsiz kalin.")

while True:
    ret, frame = cap.read()
    if not ret: break

    result = det.check(frame, (0,0,0,0))
    meta   = result.metadata
    color  = (0,255,0) if result.is_live else (0,120,255)

    cv2.putText(frame, f"LapVar:{meta.get('lap_var',0):.0f}  Entropy:{meta.get('entropy',0):.2f}  Contrast:{meta.get('loc_contrast',0):.1f}",
                (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)
    cv2.putText(frame, f"Score:{result.score:.3f}  Frames:{meta.get('frames',0)}",
                (10,60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200,200,200), 2)
    cv2.putText(frame, result.message, (10,95), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

    if result.is_live:
        cv2.putText(frame, "PASSED - GERCEK YUZ!", (10,140),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 3)

    cv2.imshow("TextureAnalyzer Test", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"): break
    if result.challenge_completed:
        cv2.waitKey(2000); break

cap.release()
cv2.destroyAllWindows()
print("Sonuc:", "PASSED" if result.is_live else "FAILED")
print("Score:", result.score)
