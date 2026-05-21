"""
scripts/test_texture_live.py
-----------------------------
TextureAnalyzer webcam testi (çok sinyalli PAD).
Calistir: python scripts/test_texture_live.py
"""
import sys
import cv2

sys.path.insert(0, ".")
from core.liveness.texture_analyzer import TextureAnalyzer

det = TextureAnalyzer()
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Kamera acilamadi!")
    sys.exit(1)

print("TextureAnalyzer Test (FFT + Glare + LBP ensemble) — q ile cikis")
print("Kameraya duz bakin, hareketsiz kalin.")

result = None
while True:
    ret, frame = cap.read()
    if not ret:
        break

    result = det.check(frame, (0, 0, 0, 0))
    meta   = result.metadata or {}
    color  = (0, 255, 0) if result.is_live else (0, 120, 255)

    # Sinyal satırı
    line1 = (
        f"FFT:{meta.get('fft_risk', 0):.2f}  "
        f"Glare:{meta.get('glare_risk', 0):.2f}  "
        f"LBP:{meta.get('lbp_risk', 0):.2f}"
        + (f"  MFAS:{meta.get('mfas_risk', 0):.2f}" if "mfas_risk" in meta else "  MFAS:N/A")
    )
    line2 = f"Score:{result.score:.3f}  Frames:{meta.get('frames', 0)}/{8}  QSkip:{meta.get('quality_skips', 0)}"

    cv2.putText(frame, line1,           (10,  30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)
    cv2.putText(frame, line2,           (10,  60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 2)
    cv2.putText(frame, result.message,  (10,  95), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

    if result.challenge_completed:
        cv2.putText(frame, "PASSED - GERCEK YUZ!", (10, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)

    cv2.imshow("TextureAnalyzer Test", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

if result:
    print(f"Son sonuc : {'PASSED' if result.is_live else 'FAILED'}")
    print(f"Score     : {result.score}")
    print(f"Mesaj     : {result.message}")
    print(f"Metadata  : {result.metadata}")
