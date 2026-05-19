"""
core/decision_engine.py
------------------------
Nihai erişim kararı.

Politika (v0.2):
  1. Session'daki tüm liveness challenge'ları geçilmiş olmalı.
  2. Ortalama liveness confidence >= MIN_LIVENESS_CONFIDENCE olmalı.
  3. Yüz tanıma eşiği geçilmeli (recognized == True).
  4. Frame'de tek yüz olmalı.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from core.recognition import RecognitionResult

logger = logging.getLogger(__name__)

# ── Politika sabitleri ────────────────────────────────────────────────────────
MIN_LIVENESS_CONFIDENCE = 0.60   # ortalama liveness skoru bu değerin altındaysa reddet
MIN_CHALLENGES_REQUIRED = 2      # kaç liveness challenge tamamlanmış olmalı


@dataclass
class LivenessSummary:
    """Bir session'daki tüm liveness sonuçlarının özeti."""
    challenges_passed:    list[str]   # geçilen challenge isimleri
    challenges_failed:    list[str]   # başarısız olanlar
    avg_confidence:       float       # ortalama güven skoru
    all_passed:           bool        # tümü geçildi mi


@dataclass
class AccessDecision:
    """Sistemin nihai erişim kararı."""
    access_granted:   bool
    recognition:      RecognitionResult
    liveness:         Optional[LivenessSummary] = None
    reason:           str = ""

    # Kısayollar
    @property
    def user_id(self) -> Optional[str]:
        return self.recognition.user_id

    @property
    def name(self) -> Optional[str]:
        return self.recognition.name

    @property
    def recognition_score(self) -> float:
        return self.recognition.recognition_score


def decide(
    recognition: RecognitionResult,
    liveness_results: Optional[list[dict]] = None,
) -> AccessDecision:
    """
    Recognition + liveness sonuçlarını birleştirip erişim kararı verir.

    Parameters
    ----------
    recognition      : RecognitionResult — yüz tanıma sonucu
    liveness_results : list[dict] — DB'den gelen liveness_challenges satırları
                       Her dict: {challenge_name, passed, confidence}
                       None ise liveness atlanır (geriye dönük uyumluluk).

    Returns
    -------
    AccessDecision
    """

    # ── 1. Yüz tespiti kontrolleri ────────────────────────────────────────────
    if not recognition.face_detected:
        return AccessDecision(
            access_granted=False,
            recognition=recognition,
            reason="No face detected",
        )

    if recognition.face_count > 1:
        return AccessDecision(
            access_granted=False,
            recognition=recognition,
            reason="Multiple faces – ambiguous identity",
        )

    # ── 2. Liveness kontrolü ──────────────────────────────────────────────────
    liveness_summary = None

    if liveness_results is not None:
        passed_rows   = [r for r in liveness_results if r.get("passed")]
        failed_rows   = [r for r in liveness_results if not r.get("passed")]
        passed_names  = [r["challenge_name"] for r in passed_rows]
        failed_names  = [r["challenge_name"] for r in failed_rows]

        confidences   = [r.get("confidence", 0.0) for r in liveness_results]
        avg_conf      = sum(confidences) / len(confidences) if confidences else 0.0
        all_passed    = len(failed_rows) == 0 and len(passed_rows) >= MIN_CHALLENGES_REQUIRED

        liveness_summary = LivenessSummary(
            challenges_passed=passed_names,
            challenges_failed=failed_names,
            avg_confidence=round(avg_conf, 4),
            all_passed=all_passed,
        )

        logger.info(
            "Liveness: passed=%s failed=%s avg_conf=%.3f",
            passed_names, failed_names, avg_conf,
        )

        if not all_passed:
            return AccessDecision(
                access_granted=False,
                recognition=recognition,
                liveness=liveness_summary,
                reason="Liveness failed",
            )

        if avg_conf < MIN_LIVENESS_CONFIDENCE:
            return AccessDecision(
                access_granted=False,
                recognition=recognition,
                liveness=liveness_summary,
                reason="Low liveness confidence",
            )

    # ── 3. Biyometrik tanıma kontrolü ─────────────────────────────────────────
    if not recognition.recognized:
        return AccessDecision(
            access_granted=False,
            recognition=recognition,
            liveness=liveness_summary,
            reason="Face not recognised",
        )

    # ── 4. Erişim ver ─────────────────────────────────────────────────────────
    logger.info(
        "ACCESS GRANTED: user=%s score=%.3f liveness_conf=%.3f",
        recognition.user_id,
        recognition.recognition_score,
        liveness_summary.avg_confidence if liveness_summary else -1,
    )

    return AccessDecision(
        access_granted=True,
        recognition=recognition,
        liveness=liveness_summary,
        reason="Recognised",
    )
