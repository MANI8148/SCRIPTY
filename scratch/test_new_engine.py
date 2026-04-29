import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from story_engine import StoryEngine
from control_system import validate_narrative_structure

# Initialize engine
engine = StoryEngine(data_dir="backend/data_processed")

# Generate a story
genre = "Historical Mystery"
theme = "Sacrifice"
location = "Hyderabad"
year = 1910

print(f"--- Generating {genre} Story ---\n")
story = engine.create_structured_story(genre, theme, location, year)
print(story)

# Verify structure
print("\n--- Structural Verification ---")
valid, msg = validate_narrative_structure(engine.story_state) # Note: new engine uses story_state as outline
print(f"Valid: {valid}, Message: {msg}")
