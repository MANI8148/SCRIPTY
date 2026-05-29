import os
import sys

# Add repository root to path
sys.path.append(os.getcwd())

from backend.core.story_engine import StoryEngine
from backend.control_system import block_dataset_patterns

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
paragraphs = [paragraph for paragraph in story.split("\n\n") if paragraph.strip()]
safe, msg = block_dataset_patterns(story)
valid = len(paragraphs) == 5 and safe
print(f"Valid: {valid}, Paragraphs: {len(paragraphs)}, Message: {msg}")
