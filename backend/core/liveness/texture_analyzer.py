"""
core/liveness/texture_analyzer.py
-----------------------------------
MiniFASNet tabanlı pasif anti-spoofing liveness tespiti.

Orijinal: minivision-ai/silent-face-anti-spoofing (MiniFASNetV2 + V1SE ensemble)
prob çıktısı: [background, real, fake] → index 1 = real skor
"""

import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from core.liveness.base import LivenessDetectorBase, LivenessResult
from core.detection import FaceDetector
from core.preprocessing import prepare_for_insightface

_MODEL_DIR  = Path(__file__).parent.parent.parent / "models" / "anti_spoofing"
_MODEL_V2   = _MODEL_DIR / "2.7_80x80_MiniFASNetV2.pth"
_MODEL_V1SE = _MODEL_DIR / "4_0_0_80x80_MiniFASNetV1SE.pth"
_MFAS_PY    = _MODEL_DIR / "MiniFASNet.py"

_INPUT_SIZE     = (80, 80)
_FRAMES_REQ     = 5
_WINDOW_SECS    = 15.0
_LIVE_THRESHOLD = 0.55
_FACE_MARGIN    = 0.25


def _import_minifasnet():
    """MiniFASNet.py'yi dinamik import et."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("MiniFASNet", str(_MFAS_PY))
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_model(model_cls, path: Path):
    model = model_cls(conv6_kernel=(5, 5))
    state = torch.load(str(path), map_location="cpu", weights_only=False)
    if isinstance(state, dict):
        cleaned = {k.replace("module.", ""): v for k, v in state.items()}
        model.load_state_dict(cleaned, strict=False)
    model.eval()
    return model


def _preprocess(face_bgr: np.ndarray) -> torch.Tensor:
    img = cv2.resize(face_bgr, _INPUT_SIZE)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    # MiniFASNet sadece [0,1] scale kullanır, ImageNet norm YOK
    return torch.from_numpy(img.transpose(2, 0, 1)).unsqueeze(0).float()


def _crop_face(frame: np.ndarray, bbox: tuple, margin: float = _FACE_MARGIN) -> np.ndarray:
    x1, y1, x2, y2 = [int(v) for v in bbox]
    h, w = frame.shape[:2]
    mw = int((x2 - x1) * margin)
    mh = int((y2 - y1) * margin)
    return frame[max(0, y1-mh):min(h, y2+mh), max(0, x1-mw):min(w, x2+mw)]


class TextureAnalyzer(LivenessDetectorBase):
    NAME = "texture"
    _models_loaded = False
    _model_v2  = None
    _model_v1se = None

    def __init__(self) -> None:
        self._reset_state()
        if not TextureAnalyzer._models_loaded:
            self._load_models()

    def _load_models(self):
        try:
            mfas = _import_minifasnet()
            TextureAnalyzer._model_v2   = _load_model(mfas.MiniFASNetV2,   _MODEL_V2)
            TextureAnalyzer._model_v1se = _load_model(mfas.MiniFASNetV1SE, _MODEL_V1SE)
            TextureAnalyzer._models_loaded = True
            import logging
            logging.getLogger(__name__).info("MiniFASNet models loaded OK")
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("MiniFASNet load error: %s", exc)

    def _reset_state(self):
        self._scores: list[float] = []
        self._start_time = time.monotonic()

    def get_instruction(self) -> str:
        return "Kameraya duz bakin, hareketsiz kalin."

    def reset(self) -> None:
        self._reset_state()

    @torch.no_grad()
    def _infer(self, face_bgr: np.ndarray) -> float:
        if not self._models_loaded:
            return 0.5
        tensor = _preprocess(face_bgr)
        # prob: [background, spoof, real] → index 2 = real face
        p_v2   = F.softmax(self._model_v2(tensor),   dim=1)[0, 1].item()
        p_v1se = F.softmax(self._model_v1se(tensor), dim=1)[0, 1].item()
        # spoof score düşükse gerçek yüz → 1 - spoof_score
        return 1.0 - (p_v2 + p_v1se) / 2.0

    def check(self, bgr_frame: np.ndarray, bbox: tuple) -> LivenessResult:
        elapsed   = time.monotonic() - self._start_time
        timed_out = elapsed > _WINDOW_SECS

        if not self._models_loaded:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False, message="Model yuklenemedi.",
            )

        try:
            detector  = FaceDetector.get_instance()
            rgb       = prepare_for_insightface(bgr_frame)
            detection = detector.detect(rgb)
        except Exception as exc:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False, message=f"Tespit hatasi: {exc}",
            )

        if not detection.has_face or detection.count != 1:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False, message="Tek yuz bulunamadi.",
                metadata={"frames": len(self._scores)},
            )

        face_crop = _crop_face(bgr_frame, detection.single_face.bbox)
        if face_crop.size == 0:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False, message="Yuz kirpma hatasi.",
            )

        real_score = self._infer(face_crop)
        self._scores.append(real_score)

        if len(self._scores) >= _FRAMES_REQ or timed_out:
            avg  = float(np.mean(self._scores))
            live = avg >= _LIVE_THRESHOLD
            done = live
            if not live and not timed_out:
                self._scores.clear()
        else:
            avg  = real_score
            live = False
            done = False

        return LivenessResult(
            is_live=live,
            score=round(avg, 3),
            method=self.NAME,
            challenge_completed=done,
            message=(
                "Tamamlandi!" if done
                else "Sahte goruntu!" if (not live and len(self._scores) == 0 and elapsed > 2)
                else f"Analiz: {min(len(self._scores), _FRAMES_REQ)}/{_FRAMES_REQ} ({avg:.2f})"
            ),
            metadata={"real_score": round(avg, 3), "frames": len(self._scores)},
        )
