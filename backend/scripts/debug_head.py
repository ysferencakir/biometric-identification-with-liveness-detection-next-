"""
solvePnP çıktısını canlı göster — baş döndürünce yaw değişiyor mu?
"""
import sys, cv2, numpy as np
sys.path.insert(0, ".")
from core.detection import FaceDetector
from core.preprocessing import prepare_for_insightface

_MODEL_3D = np.array([
    [ 0.0,    0.0,    0.0  ],
    [ 0.0,   -330.0, -65.0 ],
    [-225.0,  170.0, -135.0],
    [ 225.0,  170.0, -135.0],
    [-150.0, -150.0, -125.0],
    [ 150.0, -150.0, -125.0],
], dtype=np.float64)
_LM_IDX = [30, 8, 36, 45, 48, 54]

detector = FaceDetector.get_instance()
cap = cv2.VideoCapture(0)
print("Basi saga/sola cevir — q ile cikis")

while True:
    ret, frame = cap.read()
    if not ret: break
    h, w = frame.shape[:2]

    rgb = prepare_for_insightface(frame)
    det = detector.detect(rgb)

    if det.has_face and det.count == 1:
        lm68 = getattr(det.single_face._raw, "landmark_3d_68", None)
        if lm68 is not None:
            lm = np.array(lm68)

            # Yeni yöntem: burun offseti
            nose_x       = lm[30, 0]
            left_eye_x   = (lm[36, 0] + lm[39, 0]) / 2.0
            right_eye_x  = (lm[45, 0] + lm[42, 0]) / 2.0
            eye_center_x = (left_eye_x + right_eye_x) / 2.0
            eye_dist     = abs(right_eye_x - left_eye_x) + 1e-6
            offset       = (nose_x - eye_center_x) / eye_dist

            color = (0, 255, 0) if abs(offset) > 0.12 else (255, 255, 0)
            cv2.putText(frame, f"OFFSET: {offset:+.3f}  (esik:+-0.12)", (10,35), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
            cv2.putText(frame, f"Saga > +0.12  |  Sola < -0.12", (10,70), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200,200,200), 2)

            # Landmark noktaları
            for idx in [30, 36, 39, 42, 45]:
                x, y = int(lm[idx,0]), int(lm[idx,1])
                cv2.circle(frame, (x,y), 5, (0,255,0), -1)
        else:
            cv2.putText(frame, "68 landmark YOK", (10,35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
    else:
        cv2.putText(frame, "Yuz bulunamadi", (10,35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)

    cv2.imshow("Head Debug", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"): break

cap.release()
cv2.destroyAllWindows()
