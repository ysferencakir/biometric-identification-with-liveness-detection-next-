import difflib
from typing import Tuple, List

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

def get_char_similarity(s1: str, s2: str) -> float:
    """
    Computes character-level similarity percentage between two strings.
    Uses RapidFuzz fuzz.ratio if available, falling back to difflib.SequenceMatcher.
    """
    if not s1 or not s2:
        return 0.0
        
    if HAS_RAPIDFUZZ:
        return float(fuzz.ratio(s1, s2))
    else:
        # Fallback using standard library
        matcher = difflib.SequenceMatcher(None, s1, s2)
        return float(matcher.ratio() * 100.0)

def get_word_similarity(w1: str, w2: str) -> float:
    """Computes similarity between two single words."""
    if HAS_RAPIDFUZZ:
        return float(fuzz.ratio(w1, w2))
    else:
        return float(difflib.SequenceMatcher(None, w1, w2).ratio() * 100.0)

def calculate_word_match_ratio(target: str, transcript: str, threshold: float = 80.0) -> float:
    """
    Calculates the percentage of words in the target sentence that appear in the transcript.
    Tolerates minor phonetic differences at the word level (e.g. 'gidiyo' matches 'gidiyor' if similarity >= 80%).
    """
    target_words = target.split()
    transcript_words = transcript.split()
    
    if not target_words:
        return 0.0
    if not transcript_words:
        return 0.0
        
    matched_count = 0
    remaining_transcript = list(transcript_words)
    
    for t_word in target_words:
        # 1. Look for exact match first
        if t_word in remaining_transcript:
            matched_count += 1
            remaining_transcript.remove(t_word)
            continue
            
        # 2. Look for a fuzzy match (similarity >= threshold, e.g., 80.0%)
        best_match_idx = -1
        best_match_score = 0.0
        
        for idx, trans_word in enumerate(remaining_transcript):
            score = get_word_similarity(t_word, trans_word)
            if score >= threshold and score > best_match_score:
                best_match_score = score
                best_match_idx = idx
                
        if best_match_idx != -1:
            matched_count += 1
            remaining_transcript.pop(best_match_idx)
            
    return float(matched_count / len(target_words) * 100.0)

def check_similarity(
    target_text: str, 
    transcript_text: str, 
    required_similarity: float = 80.0
) -> Tuple[bool, float, float]:
    """
    Performs comprehensive similarity validation.
    
    Returns:
        Tuple[success, similarity_score, word_match_ratio]
    """
    if not target_text or not transcript_text:
        return False, 0.0, 0.0
        
    # Calculate character-based similarity
    similarity_score = get_char_similarity(target_text, transcript_text)
    
    # Calculate word-based match ratio
    word_match_ratio = calculate_word_match_ratio(target_text, transcript_text)
    
    # Determine success (must pass character similarity and match at least 80% of words)
    success = (similarity_score >= required_similarity) and (word_match_ratio >= 80.0)
    
    return success, round(similarity_score, 2), round(word_match_ratio, 2)
