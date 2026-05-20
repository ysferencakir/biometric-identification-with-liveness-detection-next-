"""
core/liveness/__init__.py
--------------------------
Tüm liveness detector'larını manager'a register eder.
Yeni bir detector eklenince buraya import + register satırı ekle.
"""

from core.liveness.manager import liveness_manager
from core.liveness.blink_detector import BlinkDetector
from core.liveness.head_movement import HeadMovementDetector
from core.liveness.texture_analyzer import TextureAnalyzer

liveness_manager.register(BlinkDetector.NAME, BlinkDetector())
liveness_manager.register(HeadMovementDetector.NAME, HeadMovementDetector())
liveness_manager.register(TextureAnalyzer.NAME, TextureAnalyzer())
