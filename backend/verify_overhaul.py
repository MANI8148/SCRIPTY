"""
SCRIPTY - System Verification Script (V5 Overhaul)
Runs the StoryEngine to verify narrative quality, API cleaning, and role logic.
"""
import sys
import os
import asyncio

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from backend.core.story_engine import StoryEngine
    from backend.core.data_models import StoryMode
except ImportError:
    from core.story_engine import StoryEngine
    from core.data_models import StoryMode

def main():
    print("--- SCRIPTY SYSTEM VERIFICATION (V5 OVERHAUL) ---")
    print("Initializing StoryEngine...")
    engine = StoryEngine()
    
    print("\nGenerating Story for Hyderabad, 1920 (Colonial Era)...")
    try:
        result = asyncio.run(engine.generate_story("Hyderabad", 1920, StoryMode.SHORT, location_type="urban"))
        story = result["story_text"]
        print("\n--- GENERATED STORY ---")
        print(story)
        print("\n--- VERIFICATION STATS ---")
        lines = story.split("\n")
        print(f"Total Lines: {len(lines)}")
        
        # Check for repetition
        city_count = story.count("Hyderabad")
        print(f"City Name ('Hyderabad') Count: {city_count}")
        
        # Check for "the Hyderabad"
        wrong_article = "the Hyderabad" in story.lower()
        print(f"Improper article ('the Hyderabad') found: {wrong_article}")
        
        # Check for role keywords
        role_keywords = ["ledger", "fine print", "paper trail", "shadowy sources", "evidence", "damning", "technical", "hacking", "mechanical", "cryptic", "runes", "truth"]
        found_role_impact = any(kw in story.lower() for kw in role_keywords)
        print(f"Role-specific impact detected: {found_role_impact}")
        
        # Count sentences as lines
        print(f"Total Sentences (Lines): {len(lines)}")
        if len(lines) >= 30 and len(lines) <= 60:
            print("✓ Story length is within target (30-60 lines).")
        else:
            # We can artificially inflate lines by splitting very long sentences or just noting it
            print(f"⚠ Story length ({len(lines)} lines) is outside of target (30-60 lines).")
            
        print("\n✓ Verification Complete.")
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
