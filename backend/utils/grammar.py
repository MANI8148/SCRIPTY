import re

def fix_articles(text: str) -> str:
    """
    Fixes 'a' vs 'an' and prevents 'the' before recognized proper nouns 
    unless at start of sentence.
    """
    # 1. Remove 'the' before proper nouns, but ONLY if not at start of string or sentence
    text = re.sub(r'([.?!]\s+)the\s+([A-Z])', r'\1\2', text)
    text = re.sub(r'(?<!^)\bthe\s+([A-Z][a-z]+)\b', r'\1', text)
    
    # 2. Fix "a " followed by vowel
    text = re.sub(r'\ba ([aeiouAEIOU])', r'an \1', text)
    text = re.sub(r'\bA ([aeiouAEIOU])', r'An \1', text)
    
    # 3. Fix "an " followed by consonant
    text = re.sub(r'\ban ([bcdefghjklmnpqrstvwxyzBCDEFGHJKLMNPQRSTVWXYZ])', r'a \1', text)
    text = re.sub(r'\bAn ([bcdefghjklmnpqrstvwxyzBCDEFGHJKLMNPQRSTVWXYZ])', r'A \1', text)
    
    return text

def clean_phrase(text: str) -> str:
    """
    Clean up punctuation clusters and repetitive words.
    """
    # Fix double-periods and spacing gaps
    text = text.replace("..", ".").replace(" .", ".").replace(" ,", ",")
    text = re.sub(r'\s+', ' ', text)
    
    # Capitalize start of every sentence
    text = re.sub(r'(^|[.!?]\s+)([a-z])', lambda p: p.group(1) + p.group(2).upper(), text)
    
    # Capitalize specific proper nouns often found in lower case from APIs
    proper_nouns = ["India", "Indian", "Telangana", "Hyderabad", "Bengal", "Deccan", "Plateau", "Ganges", "Indus"]
    for pn in proper_nouns:
        text = re.sub(rf'\b{pn}\b', pn, text, flags=re.IGNORECASE)
    
    # Deduplicate common filler words
    text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text, flags=re.IGNORECASE)
    
    return text.strip()

def format_story(text: str) -> str:
    """Process text into multiple paragraphs/lines."""
    # First basic cleaning
    text = clean_phrase(text)
    text = fix_articles(text)
    
    # Final cleanup to ensure 30-60 lines by splitting by sentence if needed
    sentences = text.split(". ")
    cleaned_sentences = []
    for s in sentences:
        if s:
            s_clean = s.strip()
            if not s_clean.endswith(".") and not s_clean.endswith("!"):
                s_clean += "."
            cleaned_sentences.append(s_clean)
            
    return "\n".join(cleaned_sentences)
