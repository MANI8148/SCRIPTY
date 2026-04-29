import os
import json
import re
from bs4 import BeautifulSoup

def is_mythological(name):
    """Checks if any part of the name contains a mythological figure."""
    myth_names = {
        "indra", "agni", "krishna", "vishnu", "garuda", "shiva", "brahma", 
        "rama", "sita", "hanuman", "surya", "vayu", "yamaraj", "narada",
        "partha", "bhishma", "drona", "yudhisthira", "dhritarashtra", "vyasa",
        "ganga", "kuru", "pandu", "shakti", "vasudeva", "balarama", "rishi"
    }
    name_lower = name.lower()
    return any(myth in name_lower for myth in myth_names)

def classify_entity(word):
    """
    ULTRA-STRICT Rule-based entity classification.
    """
    # Clean punctuation and whitespace
    word_clean = re.sub(r'^[^\w]+|[^\w]+$', '', word)
    
    # 1. NOISE RULES
    noise_words = {
        "thou", "thy", "thee", "thine", "herein", "behold", "unto", "wherefore", "thence",
        "about", "according", "after", "again", "against", "all", "although", "amongst",
        "another", "any", "as", "at", "but", "by", "could", "did", "do", "does", "each",
        "every", "for", "from", "had", "has", "have", "he", "her", "his", "how", "if",
        "in", "into", "is", "it", "its", "just", "like", "may", "more", "most", "much",
        "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "our",
        "out", "over", "said", "shall", "she", "should", "so", "some", "such", "than",
        "that", "the", "their", "them", "then", "there", "these", "they", "this", "those",
        "through", "to", "too", "under", "until", "up", "very", "was", "we", "were", "what",
        "when", "where", "which", "while", "who", "whom", "why", "will", "with", "within",
        "without", "would", "yet", "you", "your", "alas", "besides", "indeed", "towards",
        "absolute", "accept", "additional", "addressing", "accomplished", "accordingly", "afterwards"
    }
    
    if word_clean.lower() in noise_words:
        return "noise"
    if len(word_clean) < 3:
        return "noise"
    if any(c in word_clean for c in "\n\r\t{}[]<>0123456789"):
        return "noise"
    
    # 2. PLACE RULES
    known_places = {"bengal", "kasi", "panchala", "madra", "manipura", "himalayas", "ganga", "yamuna", "india"}
    place_suffixes = ("pur", "nagar", "abad", "garh", "pattan", "ore", "bad", "ana", "war")
    if word_clean.lower() in known_places:
        return "place"
    if any(word_clean.lower().endswith(s) for s in place_suffixes):
        return "place"
    
    # 3. CONCEPT RULES
    concepts = {
        "dharma", "karma", "atma", "soul", "fate", "yuga", "dhanam", "moksha", "vedas",
        "absolute", "truth", "knowledge", "wisdom", "sacred", "scripture", "ritual",
        "adi", "parva", "adhyatma", "akshauhini", "amrita"
    }
    if word_clean.lower() in concepts:
        return "concept"
    
    # 4. MYTHOLOGY (Strict filter)
    if is_mythological(word_clean):
        # We categorize myth names as 'concept' relative to our realistic story goal
        return "concept"
        
    return "person"

def extract_rule_based_data(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'lxml')
    for tag in soup(['script', 'style', 'header', 'footer']):
        tag.decompose()
        
    paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text().strip()) > 30]
    full_text = " ".join(paragraphs[:500])
    
    # Improved Entity Detection using Regex
    # Matches words starting with Capitals, potentially multi-word
    entities = re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b', full_text)
    
    results = {
        "people": set(),
        "places": set(),
        "concepts": set(),
        "keywords": set(),
        "actions": set()
    }
    
    for ent in entities:
        category = classify_entity(ent)
        if category == "person":
            results["people"].add(ent)
        elif category == "place":
            results["places"].add(ent)
        elif category == "concept":
            results["concepts"].add(ent)
            
    # Simple Keyword Extraction
    raw_keywords = re.findall(r'\b[a-z]{6,}\b', full_text.lower())
    results["keywords"] = set([w for w in raw_keywords if classify_entity(w) != "noise"])
    
    # Action Extraction
    common_verbs = ["stood", "walked", "opened", "spoke", "found", "watched", "discovered"]
    for verb in common_verbs:
        pattern = rf'\b{verb}\b\s+(?:the\s+|a\s+)?([a-z]{4,})\b'
        matches = re.findall(pattern, full_text.lower())
        for m in matches:
            results["actions"].add(f"{verb} {m}")
                
    return {
        "people": sorted(list(results["people"])),
        "places": sorted(list(results["places"])),
        "concepts": sorted(list(results["concepts"])),
        "keywords": sorted(list(results["keywords"]))[:50],
        "actions": sorted(list(results["actions"]))[:50]
    }

def process_all_data():
    dataset_dir = "dataset"
    output_dir = "backend/data_processed"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    files = [f for f in os.listdir(dataset_dir) if f.endswith(".html")]
    for filename in files:
        path = os.path.join(dataset_dir, filename)
        try:
            data = extract_rule_based_data(path)
            data["source"] = filename
            save_path = os.path.join(output_dir, filename.replace(".html", ".json"))
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"Processed: {filename}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    process_all_data()
