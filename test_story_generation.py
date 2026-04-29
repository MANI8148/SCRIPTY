#!/usr/bin/env python3
"""
Test Story Generation with Processed Dataset
Generates sample stories using the fixed dataset processor output
"""

import sys
import os
import json

sys.path.insert(0, '/Users/manikantapotla/Desktop/SCRIPTY/backend')

from story_engine import StoryEngine

def display_story(story_num, genre, theme, location, year, story_text):
    """Format and display a generated story"""
    print("=" * 70)
    print(f"STORY #{story_num}")
    print("=" * 70)
    print(f"Genre: {genre}")
    print(f"Theme: {theme}")
    print(f"Location: {location}")
    print(f"Year: {year}")
    print("-" * 70)
    print(story_text)
    print()

def check_processed_data():
    """Verify processed data exists and is valid"""
    data_dir = "backend/data_processed"
    if not os.path.exists(data_dir):
        print("✗ ERROR: Processed data directory not found")
        return False
    
    files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    if not files:
        print("✗ ERROR: No processed JSON files found")
        return False
    
    # Check first file
    with open(os.path.join(data_dir, files[0])) as f:
        data = json.load(f)
    
    print(f"✓ Found {len(files)} processed dataset files")
    print(f"✓ Sample data: {len(data.get('people', []))} people, {len(data.get('places', []))} places, {len(data.get('concepts', []))} concepts")
    return True

def main():
    print("\n" + "=" * 70)
    print("STORY GENERATION TEST - Using Processed Data")
    print("=" * 70 + "\n")
    
    # Verify data
    if not check_processed_data():
        sys.exit(1)
    
    # Initialize engine
    engine = StoryEngine(data_dir="backend/data_processed")
    
    # Generate multiple stories
    story_configs = [
        {
            "genre": "Historical Mystery",
            "theme": "Sacrifice",
            "location": "Hyderabad",
            "year": 1910
        },
        {
            "genre": "Historical Drama",
            "theme": "Honor",
            "location": "Bengal",
            "year": 1905
        },
        {
            "genre": "Political Thriller",
            "theme": "Power",
            "location": "Delhi",
            "year": 1920
        }
    ]
    
    print("\n" + "=" * 70)
    print("GENERATING SAMPLE STORIES")
    print("=" * 70 + "\n")
    
    for i, config in enumerate(story_configs, 1):
        print(f"[{i}/{len(story_configs)}] Generating: {config['genre']} - {config['theme']}")
        
        try:
            story = engine.create_structured_story(
                config['genre'],
                config['theme'],
                config['location'],
                config['year']
            )
            
            display_story(
                i,
                config['genre'],
                config['theme'],
                config['location'],
                config['year'],
                story
            )
            
        except Exception as e:
            print(f"✗ Error generating story: {e}\n")
    
    print("=" * 70)
    print("✓ STORY GENERATION TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
