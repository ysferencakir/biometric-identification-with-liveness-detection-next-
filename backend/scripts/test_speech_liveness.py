import os
import sys
import time

# Ensure backend root is on the path so we can import our modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.speech_liveness.text_normalizer import normalize_text, turkish_lower
from core.speech_liveness.similarity_checker import check_similarity
from core.speech_liveness.sentence_generator import speech_challenge_registry

def test_turkish_lowercase():
    print("\n--- TEST: Turkish Lowercase ---")
    inputs = {
        "İSTANBUL": "istanbul",
        "IŞIKLAR": "ışıklar",
        "ÖĞRETMEN ÇOCUK": "öğretmen çocuk",
        "ŞEMSİYE": "şemsiye",
        "ÜZÜM": "üzüm"
    }
    all_ok = True
    for inp, expected in inputs.items():
        got = turkish_lower(inp)
        status = "OK" if got == expected else "FAIL"
        print(f"[{status}] turkish_lower('{inp}') -> got: '{got}', expected: '{expected}'")
        if got != expected:
            all_ok = False
    return all_ok

def test_normalization():
    print("\n--- TEST: Text Normalization ---")
    tests = [
        ("Mavi, araba yolda gidiyor!!!", "mavi araba yolda gidiyor"),
        ("  Küçük - kedi   süt   içiyor. ", "küçük kedi süt içiyor"),
        ("Ali kırmızı kalemi aldı?", "ali kırmızı kalemi aldı"),
        ("Bugün HAVA çok GÜZEL...", "bugün hava çok güzel")
    ]
    all_ok = True
    for inp, expected in tests:
        got = normalize_text(inp)
        status = "OK" if got == expected else "FAIL"
        print(f"[{status}] normalize_text('{inp}') -> got: '{got}'")
        if got != expected:
            all_ok = False
    return all_ok

def test_similarity():
    print("\n--- TEST: Similarity Checker ---")
    # (Target, Transcript, Expected Success >= 80%)
    tests = [
        ("mavi araba yolda gidiyor", "mavi araba yolda gidiyor", True),
        ("mavi araba yolda gidiyor", "mavi araba yolda gidiyo", True), # Tolerates ending verbs
        ("mavi araba yolda gidiyor", "mavi araba yoldan gidiyor", True), # Tolerates minor suffix
        ("mavi araba yolda gidiyor", "kırmızı araba yolda gidiyor", False), # Wrong adjective (only 3/4 words match)
        ("küçük kedi süt içiyor", "küçük kedi süt içiyo", True),
        ("ali kırmızı kalemi aldı", "veli kırmızı kalemi aldı", False),
    ]
    all_ok = True
    for target, transcript, expected_pass in tests:
        norm_t = normalize_text(target)
        norm_tr = normalize_text(transcript)
        passed, sim, word_match = check_similarity(norm_t, norm_tr, required_similarity=80.0)
        status = "OK" if passed == expected_pass else "FAIL"
        print(f"[{status}] '{target}' vs '{transcript}': passed={passed}, char_sim={sim}%, word_match={word_match}%")
        if passed != expected_pass:
            all_ok = False
    return all_ok

def test_registry():
    print("\n--- TEST: Challenge Registry ---")
    reg = speech_challenge_registry
    
    # 1. Generate challenge
    cid, target = reg.generate_challenge()
    print(f"[INFO] Generated challenge: ID={cid}, Target='{target}'")
    
    # 2. Validate first time (should succeed)
    ok, text, msg = reg.validate_and_consume(cid)
    print(f"[OK] First consumption: success={ok}, text='{text}', msg='{msg}'")
    if not ok or text != target:
        print("FAIL: First validation should succeed.")
        return False
        
    # 3. Validate second time (should fail - single use security check)
    ok, text, msg = reg.validate_and_consume(cid)
    print(f"[OK] Second consumption (Single-Use check): success={ok}, text='{text}', msg='{msg}'")
    if ok:
        print("FAIL: Second validation should fail.")
        return False
        
    # 4. Expiration check
    print("[INFO] Testing challenge timeout...")
    # Change TTL of registry instance to 0.1s for fast testing
    original_ttl = reg.ttl_seconds
    reg.ttl_seconds = 0.1
    
    cid2, target2 = reg.generate_challenge()
    time.sleep(0.2) # sleep longer than TTL
    ok, text, msg = reg.validate_and_consume(cid2)
    print(f"[OK] Expired challenge validation: success={ok}, text='{text}', msg='{msg}'")
    
    # Restore TTL
    reg.ttl_seconds = original_ttl
    
    if ok:
        print("FAIL: Expired challenge should fail.")
        return False
        
    return True

if __name__ == "__main__":
    print("=== RUNNING CORE VERIFICATION TESTS ===")
    results = [
        test_turkish_lowercase(),
        test_normalization(),
        test_similarity(),
        test_registry()
    ]
    if all(results):
        print("\n=== ALL TESTS PASSED SUCCESFULLY! ===")
        sys.exit(0)
    else:
        print("\n=== SOME TESTS FAILED! ===")
        sys.exit(1)
