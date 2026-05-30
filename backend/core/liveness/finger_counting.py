"""
core/liveness/finger_counting.py
----------------------------------
Parmak sayma tabanlı liveness challenge.

Akış:
  1. reset() çağrıldığında 1-5 arası rastgele hedef sayı atanır.
  2. Her frame'de MediaPipe Hands ile parmak sayısı tespit edilir.
  3. Temporal smoothing: son 20 frame'in %80'i hedef sayıyı gösterince geçer.
  4. 20 saniye içinde geçilemezse otomatik reset (yeni hedef sayı).

Neden bu yöntem:
  - Tek frame tespiti titreme/oklüzyon nedeniyle gürültülüdür.
  - Çoğunluk oyu (majority vote) anlık hataları filtreler.
  - Yönelim-bağımsız sayma: el eğik tutulsa da doğru çalışır.
"""

import copy
import logging
import random
import time
from collections import Counter, deque
from typing import Optional

import numpy as np

from core.liveness.base import LivenessDetectorBase, LivenessResult
from core.liveness.hands_provider import HandsProvider

logger = logging.getLogger(__name__)

# ── Tuning parametreleri ──────────────────────────────────────────────────────
BUFFER_SIZE         = 20    # karar için biriktirilecek frame sayısı
MIN_FRAMES_NEEDED   = 10    # bu kadar frame dolmadan karar verilmez
AGREEMENT_THRESHOLD = 0.80  # geçmek için gereken oran (örn. 16/20)
WINDOW_SECONDS      = 20.0  # otomatik reset timeout'u


class FingerCountingDetector(LivenessDetectorBase):
    """
    Kullanıcıdan rastgele 1-5 parmak göstermesini isteyen liveness challenge.

    Her session için ayrı bir instance oluşturulur (copy.deepcopy).
    Hedef sayı reset() sırasında belirlenir; __deepcopy__ sayesinde
    HandsProvider singleton'ı doğru şekilde aktarılır.
    """

    NAME = "finger_counting"

    def __init__(self) -> None:
        self._hands_provider: Optional[HandsProvider] = None
        self._target_count: int = 1
        self._frame_buffer: deque[int] = deque(maxlen=BUFFER_SIZE)
        self._start_time: float = time.monotonic()
        self._passed: bool = False
        self.reset()

    # ── Deepcopy: HandsProvider singleton'ı kopyalanmasın ────────────────────

    def __deepcopy__(self, memo: dict) -> "FingerCountingDetector":
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            # Singleton provider referansını sıfırla; check() lazy-load eder
            setattr(result, k, None if k == "_hands_provider" else copy.deepcopy(v, memo))
        return result

    # ── LivenessDetectorBase arayüzü ─────────────────────────────────────────

    def reset(self) -> None:
        self._target_count = random.randint(1, 5)
        self._frame_buffer.clear()
        self._start_time = time.monotonic()
        self._passed = False

    def get_instruction(self) -> str:
        return f"Lutfen {self._target_count} parmagunuzu kameraya gosterin."

    def check(self, bgr_frame: np.ndarray, bbox: tuple) -> LivenessResult:
        # Önceki başarıyı koru
        if self._passed:
            return LivenessResult(
                is_live=True, score=1.0, method=self.NAME,
                challenge_completed=True,
                message="Tamamlandi!",
                metadata={"target": self._target_count},
            )

        elapsed = time.monotonic() - self._start_time

        # Timeout → yeni hedef sayıyla baştan başla
        if elapsed > WINDOW_SECONDS:
            self.reset()
            elapsed = 0.0

        # HandsProvider'ı lazy-load et (singleton'a bağlan)
        if self._hands_provider is None:
            try:
                self._hands_provider = HandsProvider.get_instance()
            except Exception as exc:
                logger.warning("HandsProvider init failed: %s", exc)

        if self._hands_provider is None:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False,
                message="El tespiti baslatılamadı.",
            )

        # El tespiti
        detected = self._hands_provider.process(bgr_frame)

        if detected is None:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False,
                message=f"{self._target_count} parmagunuzu kameraya gosterin.",
                metadata={"target": self._target_count, "hand_visible": False},
            )

        self._frame_buffer.append(detected)

        # Yeterli frame birikmediyse bekle
        if len(self._frame_buffer) < MIN_FRAMES_NEEDED:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False,
                message=(
                    f"{self._target_count} parmagunuzu sabitleyin... "
                    f"({len(self._frame_buffer)}/{MIN_FRAMES_NEEDED})"
                ),
                metadata={
                    "target":       self._target_count,
                    "detected":     detected,
                    "buffer_fill":  len(self._frame_buffer),
                },
            )

        # Çoğunluk oyu
        counter = Counter(self._frame_buffer)
        most_common, freq = counter.most_common(1)[0]
        agreement = freq / len(self._frame_buffer)

        if agreement >= AGREEMENT_THRESHOLD and most_common == self._target_count:
            self._passed = True
            return LivenessResult(
                is_live=True, score=1.0, method=self.NAME,
                challenge_completed=True,
                message="Tamamlandi!",
                metadata={
                    "target":    self._target_count,
                    "detected":  most_common,
                    "agreement": round(agreement, 2),
                },
            )

        # Yanlış sayı veya henüz yeterli agreement yok
        score = round(agreement, 3) if most_common == self._target_count else 0.0
        return LivenessResult(
            is_live=False,
            score=score,
            method=self.NAME,
            challenge_completed=False,
            message=(
                f"{self._target_count} parmagunuzu gosterin "
                f"(algilanan: {most_common})"
            ),
            metadata={
                "target":    self._target_count,
                "detected":  most_common,
                "agreement": round(agreement, 2),
                "elapsed":   round(elapsed, 1),
            },
        )
