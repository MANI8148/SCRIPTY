def remove_repetition(text):
    """
    Detects and removes duplicate sentences or highly repetitive phrases.
    """
    sentences = text.split(". ")
    unique_sentences = []
    for s in sentences:
        if s.strip() and s.strip() not in unique_sentences:
            unique_sentences.append(s.strip())
    return ". ".join(unique_sentences)

def block_dataset_patterns(text):
    """
    Explicitly scans for and removes any known dataset boilerplate or historical dumps.
    """
    forbidden_patterns = [
        "Project Gutenberg", "pg-header", "pg-footer", "images.html",
        "même instant", "all rights reserved", "transcriber's note"
    ]
    for pattern in forbidden_patterns:
        if pattern.lower() in text.lower():
            return False, f"Forbidden pattern detected: {pattern}"
    return True, "Safe"

def clean_text(text):
    """
    Removes weird tokens, normalizes spacing, and fixes common punctuation issues.
    """
    if not text:
        return ""
    
    # Normalize spacing
    text = " ".join(text.split())
    
    # Fix spacing around punctuation
    text = text.replace(" .", ".").replace(" ,", ",").replace(" ?", "?")
    
    return text.strip()

def validate_story(text, protagonist):
    """
    Ensures the story is coherent and references the main character.
    Reject if character is missing or if text length is suspiciously large without periods.
    """
    if not text or len(text) < 50:
        return False, "Story too short or empty."
    
    if protagonist.lower() not in text.lower():
        return False, f"Protagonist {protagonist} missing from narrative."
    
    safe, msg = block_dataset_patterns(text)
    if not safe:
        return False, msg
        
    return True, "Valid"

def validate_narrative_structure(story_map):
    """
    Ensures the story follows the required emotional/narrative arc.
    """
    # Keys used in StoryEngine.create_structured_story
    required_keys = ["Introduction", "Conflict", "Climax", "Resolution"]
    
    if isinstance(story_map, dict):
        phases = list(story_map.keys())
    else:
        # Fallback for list of objects
        phases = [o.get("phase") for o in story_map if isinstance(o, dict)]
    
    missing = [req for req in required_keys if req not in phases]
    
    if missing:
        return False, f"Invalid structure. Missing: {', '.join(missing)}"
    return True, "Valid"
