"""
core/decision_engine.py
------------------------
Final access-decision logic.

TODAY (v0.1 – recognition only):
  Passes the recognition result straight through.

FUTURE (v0.2 – + liveness):
  Will combine RecognitionResult + LivenessResult to produce a single
  AccessDecision.  Plug in your liveness module here without touching
  recognition.py or the API routes.

Example future usage:
  decision = decide(recognition_result, liveness_result)
  if decision.access_granted:
      ...
"""

import logging
from dataclasses import dataclass
from typing import Optional

from core.recognition import RecognitionResult

logger = logging.getLogger(__name__)


@dataclass
class AccessDecision:
    """
    Single unified output of the decision engine.
    Extends RecognitionResult with an access_granted flag.
    """
    access_granted: bool
    recognition: RecognitionResult
    # TODO: add LivenessResult here when liveness module is integrated
    liveness_passed: Optional[bool] = None
    reason: str = ""


def decide(
    recognition: RecognitionResult,
    # TODO: add liveness_result: Optional[LivenessResult] = None
) -> AccessDecision:
    """
    Combine recognition (and future liveness) into a final access decision.

    Current policy:
      - access_granted iff recognized == True
      - liveness is not yet evaluated (always assumed passed)

    When liveness is ready, update the policy here.
    """

    # TODO: replace stub with: liveness_passed = liveness_result.is_live if liveness_result else None
    liveness_passed: Optional[bool] = None

    # Policy
    if not recognition.face_detected:
        return AccessDecision(
            access_granted=False,
            recognition=recognition,
            liveness_passed=liveness_passed,
            reason="No face detected",
        )

    if recognition.face_count > 1:
        return AccessDecision(
            access_granted=False,
            recognition=recognition,
            liveness_passed=liveness_passed,
            reason="Multiple faces – ambiguous identity",
        )

    if not recognition.recognized:
        return AccessDecision(
            access_granted=False,
            recognition=recognition,
            liveness_passed=liveness_passed,
            reason="Face not recognised",
        )

    # TODO: also check liveness_passed here once integrated
    # if liveness_passed is False:
    #     return AccessDecision(False, recognition, liveness_passed, "Liveness check failed")

    return AccessDecision(
        access_granted=True,
        recognition=recognition,
        liveness_passed=liveness_passed,
        reason="Recognised",
    )
