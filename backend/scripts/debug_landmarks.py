"""
Webcam'den yüz yakalar, 106 landmark'ı ekrana çizer.
Göz indekslerini bulmak için kullanılır.
Çıkış: q
"""
import sys
import cv2
import numpy as np

sys.path.insert(0, ".")
from core.detection import FaceDetector
from core.preprocessing import prepare_for_insightface

detector = FaceDetector.get_instance()
cap = cv2.VideoCapture(0)

print("Landmark debug — q ile cikis")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    rgb = prepare_for_insightface(frame)
    result = detector.detect(rgb)

    if result.has_face and result.count == 1:
        face = result.single_face._raw
        lm = getattr(face, "landmark_2d_106", None)

        if lm is not None:
            lm = np.array(lm)
            h, w = frame.shape[:2]

            # Tüm 106 noktayı çiz ve numarasını yaz
            for i, (x, y) in enumerate(lm):
                px, py = int(x), int(y)
                cv2.circle(frame, (px, py), 2, (0, 255, 0), -1)
                # Sadece göz bölgesi numaralarını yaz (30-100 arası)
                if 30 <= i <= 105:
                    cv2.putText(frame, str(i), (px + 2, py - 2),
                                cv2.FONT_HERSHEY_PLAIN, 0.6, (255, 255, 0), 1)

            # EAR deneme: sol göz 35,41,40,42,39,37
            def ear(pts, idx):
                p = pts[idx]
                A = np.linalg.norm(p[1] - p[5])
                B = np.linalg.norm(p[2] - p[4])
                C = np.linalg.norm(p[0] - p[3])
                return (A + B) / (2.0 * C + 1e-6)

            left_ear  = ear(lm, [35, 41, 40, 42, 39, 37])
            right_ear = ear(lm, [89, 95, 94, 96, 93, 91])
            avg       = (left_ear + right_ear) / 2

            cv2.putText(frame, f"L_EAR:{left_ear:.3f}  R_EAR:{right_ear:.3f}  AVG:{avg:.3f}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
            cv2.putText(frame, "Goz kirp ve EAR dusup yukselmeli",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        else:
            cv2.putText(frame, "landmark_2d_106 YOK", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    else:
        cv2.putText(frame, "Yuz bulunamadi", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    cv2.imshow("Landmark Debug", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
