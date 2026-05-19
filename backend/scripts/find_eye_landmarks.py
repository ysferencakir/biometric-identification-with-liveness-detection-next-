"""
Goz kirpma sirasinda en cok Y ekseninde degisen landmark'lari bulur.
- 'o' tus: goz ACIK ornegi kaydet
- 'c' tus: goz KAPALI ornegi kaydet
- 'r' tus: sonuclari goster
- 'q' tus: cikis
"""
import sys, numpy as np, cv2
sys.path.insert(0, ".")
from core.detection import FaceDetector
from core.preprocessing import prepare_for_insightface

detector = FaceDetector.get_instance()
cap = cv2.VideoCapture(0)

open_samples, closed_samples = [], []
current_lm = None

print("o=acik, c=kapali, r=sonuc, q=cikis")

while True:
    ret, frame = cap.read()
    if not ret: break

    rgb = prepare_for_insightface(frame)
    det = detector.detect(rgb)

    status = "Yuz yok"
    if det.has_face and det.count == 1:
        face = det.single_face._raw
        lm = getattr(face, "landmark_2d_106", None)
        if lm is not None:
            current_lm = np.array(lm)
            status = f"Acik:{len(open_samples)} Kapali:{len(closed_samples)}"

            # Mevcut indeks grubunun EAR'ini goster
            def ear(pts, idx):
                p = pts[idx]
                A = np.linalg.norm(p[1]-p[5])
                B = np.linalg.norm(p[2]-p[4])
                C = np.linalg.norm(p[0]-p[3])
                return (A+B)/(2*C+1e-6)
            e = ear(current_lm, [35,41,40,42,39,37])
            cv2.putText(frame, f"EAR(mevcut):{e:.3f}", (10,60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,255,255), 2)

    cv2.putText(frame, status, (10,30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
    cv2.putText(frame, "o=acik c=kapali r=sonuc q=cikis", (10, frame.shape[0]-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
    cv2.imshow("Find Eye Landmarks", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
    elif key == ord('o') and current_lm is not None:
        open_samples.append(current_lm.copy())
        print(f"Acik ornegi kaydedildi ({len(open_samples)})")
    elif key == ord('c') and current_lm is not None:
        closed_samples.append(current_lm.copy())
        print(f"Kapali ornegi kaydedildi ({len(closed_samples)})")
    elif key == ord('r'):
        if len(open_samples) < 2 or len(closed_samples) < 2:
            print("En az 2'ser ornek gerekli"); continue

        open_arr   = np.mean(open_samples, axis=0)    # (106, 2)
        closed_arr = np.mean(closed_samples, axis=0)

        # Y ekseni farki — goz kirpinca en cok hangi nokta Y'de degisiyor?
        y_diff = np.abs(open_arr[:, 1] - closed_arr[:, 1])
        ranked = np.argsort(y_diff)[::-1]

        print("\n=== En cok Y degisen ilk 20 landmark ===")
        for i in ranked[:20]:
            print(f"  idx={i:3d}  dy={y_diff[i]:.2f}px  "
                  f"open_y={open_arr[i,1]:.1f}  closed_y={closed_arr[i,1]:.1f}")

        # Üst 12 noktayi vurgula
        frame2 = frame.copy()
        for rank, idx in enumerate(ranked[:12]):
            ox, oy = int(open_arr[idx,0]), int(open_arr[idx,1])
            cv2.circle(frame2, (ox, oy), 5, (0,0,255), -1)
            cv2.putText(frame2, str(idx), (ox+4, oy-4),
                        cv2.FONT_HERSHEY_PLAIN, 1.0, (0,255,255), 1)
        cv2.imshow("En cok degisen noktalar (kirmizi)", frame2)
        cv2.waitKey(0)

cap.release()
cv2.destroyAllWindows()
