import random
import uuid
import time
import threading
from typing import Optional, Dict, Tuple

# Predefined, simple, phonetic, and easy-to-pronounce 4-5 word Turkish sentences
TURKISH_SENTENCES = [
    "mavi araba yolda gidiyor",
    "küçük kedi süt içiyor",
    "ali kırmızı kalemi aldı",
    "bugün hava çok güzel",
    "yeşil ağaç rüzgarda sallanıyor",
    "tatlı bebek odasında uyuyor",
    "taze ekmek fırından çıktı",
    "anne lezzetli yemek pişirdi",
    "büyük köpek bahçede koşuyor",
    "kitap okumak çok faydalı",
    "sarı balon gökyüzüne uçtu",
    "babam bana yeni oyuncak aldı"
]

class SpeechChallengeRegistry:
    """
    Thread-safe in-memory registry to manage active liveness speech challenges.
    Provides single-use challenges with a 25-second time-to-live (TTL).
    """
    def __init__(self, ttl_seconds: float = 25.0):
        self.ttl_seconds = ttl_seconds
        # Stores challenge state: {challenge_id: (target_text, created_at_timestamp, is_used)}
        self._challenges: Dict[str, Tuple[str, float, bool]] = {}
        self._lock = threading.Lock()
        
        # Keep track of last generated sentences per session or globally to prevent immediate back-to-back repetition
        self._last_generated: Optional[str] = None

    def generate_challenge(self) -> Tuple[str, str]:
        """
        Generates a new challenge with a unique challenge_id and a random Turkish sentence.
        Guarantees that the same sentence is not repeated back-to-back.
        """
        with self._lock:
            available_sentences = [s for s in TURKISH_SENTENCES if s != self._last_generated]
            if not available_sentences:
                available_sentences = TURKISH_SENTENCES
            
            target_text = random.choice(available_sentences)
            self._last_generated = target_text
            
            challenge_id = str(uuid.uuid4())
            now = time.time()
            self._challenges[challenge_id] = (target_text, now, False)
            
            # Auto-cleanup expired challenges in a lazy fashion to prevent memory growth
            self._cleanup_expired()
            
            return challenge_id, target_text

    def validate_and_consume(self, challenge_id: str) -> Tuple[bool, Optional[str], str]:
        """
        Validates the challenge:
        - Must exist
        - Must not be expired (TTL < 8s)
        - Must not be used already (single-use)
        
        Returns:
            Tuple[success, target_text_if_valid, error_message]
        """
        with self._lock:
            if challenge_id not in self._challenges:
                return False, None, "Challenge ID bulunamadı veya geçersiz."
            
            target_text, created_at, is_used = self._challenges[challenge_id]
            
            if is_used:
                return False, None, "Bu challenge zaten kullanılmış (tek kullanımlık güvenlik engeli)."
            
            # Mark as used immediately to prevent multiple submissions (single-use)
            self._challenges[challenge_id] = (target_text, created_at, True)
            
            elapsed = time.time() - created_at
            if elapsed > self.ttl_seconds:
                return False, None, f"Challenge süresi doldu ({elapsed:.1f} saniye geçti, limit: {self.ttl_seconds} saniye)."
                
            return True, target_text, "Başarılı"

    def _cleanup_expired(self) -> None:
        """Removes challenges that have been created longer than 10x TTL to keep memory clean."""
        now = time.time()
        expired_ids = [
            cid for cid, (_, created_at, _) in self._challenges.items()
            if now - created_at > (self.ttl_seconds * 10)
        ]
        for cid in expired_ids:
            self._challenges.pop(cid, None)

# Global registry instance
speech_challenge_registry = SpeechChallengeRegistry(ttl_seconds=25.0)
