import re
import string

# Turkish character lowercase mapping
TURKISH_LOWER_MAP = {
    'I': 'ı',
    'İ': 'i',
    'Ç': 'ç',
    'Ğ': 'ğ',
    'Ö': 'ö',
    'Ş': 'ş',
    'Ü': 'ü'
}

def turkish_lower(text: str) -> str:
    """
    Turkish-friendly lowercase converter.
    Handles 'I' -> 'ı' and 'İ' -> 'i' correctly, which standard python .lower() does not.
    """
    for k, v in TURKISH_LOWER_MAP.items():
        text = text.replace(k, v)
    return text.lower()

def normalize_text(text: str) -> str:
    """
    Normalizes Turkish text for comparison:
    1. Converts all text to Turkish-aware lowercase.
    2. Removes all punctuation marks.
    3. Trims and normalizes consecutive spaces into a single space.
    4. Retains all Turkish characters (ç, ğ, ı, ö, ş, ü, â, î, û).
    """
    if not text:
        return ""
        
    # 1. Turkish lowercase
    normalized = turkish_lower(text)
    
    # 2. Replace hyphens/dashes with spaces to avoid joining words
    normalized = normalized.replace("-", " ").replace("_", " ")
    
    # 3. Strip punctuation characters (including standard string.punctuation and unicode variants)
    # Using regex to remove punctuation while keeping letters and spaces
    punctuation_regex = re.compile(r'[^\w\s\d' + ''.join(TURKISH_LOWER_MAP.values()) + 'âîû]')
    normalized = punctuation_regex.sub('', normalized)
    
    # 4. Remove multiple spaces and strip boundaries
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()
