"""
SCRIPTY - Story Engine (V5 - Production Quality)
Rule-based narrative engine generating 30-60 lines of high-quality story.
Implements role utilization, alias variation, and semantic action logic.
"""
import random
import os

try:
    from backend.data.dataset_bridge import DatasetBridge
    from backend.external.location_engine import LocationEngine
    from backend.utils.india_timeline import IndiaTimeline
    from backend.core.logic_layer import LogicLayer
    from backend.utils.grammar import format_story
    from backend.external.apis import get_enriched_data
except ImportError:
    from data.dataset_bridge import DatasetBridge
    from external.location_engine import LocationEngine
    from utils.india_timeline import IndiaTimeline
    from core.logic_layer import LogicLayer
    from utils.grammar import format_story
    from external.apis import get_enriched_data

class StoryEngine:
    def __init__(self):
        self.bridge = DatasetBridge()
        self.loc_engine = LocationEngine()
        self.logic = LogicLayer()
        self.state = {}
        self.used_variants = {}

    def get_variant(self, word, category):
        """Returns a synonym or alias for a word to avoid repetition."""
        aliases = {
            "city": ["the regional capital", "the old city", "the urban sprawl", "the bustling region"],
            "manuscript": ["the document", "the fragile paper", "the ancient text", "the record"],
            "artifact": ["the item", "the object", "the treasure", "the relic"],
            "information": ["the secret", "the evidence", "the findings", "the truth"]
        }
        
        if word not in self.used_variants:
            self.used_variants[word] = 0
            return word # Use the original word first
            
        # If we've used it before, pick a variant or description
        self.used_variants[word] += 1
        # Try to pick an alias we haven't used yet or a random one
        potential = aliases.get(category, [word])
        return random.choice(potential)

    def generate_story(self, location_name: str, year: int, location_type: str = "urban"):
        # 1. Initialize State and Context
        self.used_variants = {} # Reset for new story
        loc_data = get_enriched_data(location_name)
        time_ctx = IndiaTimeline.get_temporal_context(year)
        
        protagonist = self.bridge.safe_get_character()
        role = self.bridge.get_role(time_ctx["era"])
        role_logic = self.logic.get_role_logic(role)
        
        narrative_obj = self.bridge.get_narrative_object("Information")
        obj_type = self.logic.get_object_type(narrative_obj)
        action = self.logic.get_compatible_action(narrative_obj)
        
        antagonist = self.bridge.safe_get_character()
        while antagonist == protagonist:
            antagonist = self.bridge.safe_get_character()

        self.state = {
            "protagonist": protagonist,
            "role": role,
            "role_logic": role_logic,
            "obj": narrative_obj,
            "obj_type": obj_type,
            "action": action,
            "location": location_name,
            "loc_data": loc_data,
            "time": time_ctx,
            "antagonist": antagonist,
            "year": year
        }

        # 2. Build 5-Paragraph Narrative
        story_arc = [
            self._intro(),
            self._conflict(),
            self._escalation(),
            self._climax(),
            self._resolution()
        ]

        full_text = "\n\n".join(story_arc)
        return format_story(full_text)

    def _intro(self):
        s = self.state
        city_alias = self.get_variant(s["location"], "city")
        p1 = f"In the year {s['year']}, {s['location']} was a place where history and mystery converged."
        p2 = f"It was a setting {s['loc_data']['narrative_desc']}."
        p3 = f"The architectural wonders of the era stood as silent witnesses to the passing of time, their stones echoing the footsteps of a thousand souls."
        p4 = f"For those who lived here, every street corner held a story, and every shadow a secret."
        p5 = f"{s['protagonist']}, a {s['role']} known for {s['role_logic']['specialty']}, walked the streets of {city_alias}."
        
        vibe_templates = [
            f"The air felt heavy with the scent of rain and old stone.",
            f"A quiet anticipation hung over the area, as if the very buildings were waiting for a change.",
            f"Life pulsated through the veins of {city_alias}, unconcerned with the shadows gathering at the edges.",
            f"The horizon was stained with the colors of a setting sun, casting long silhouettes against the pavement."
        ]
        return f"{p1}\n{p2}.\n{p3}\n{p4}\n{p5}\n{random.choice(vibe_templates)}"

    def _conflict(self):
        s = self.state
        obj_display = s["obj"]
        obj_alias = self.get_variant(s["obj"], s["obj_type"])
        p1 = f"Everything changed when {s['protagonist']} happened upon the {obj_display}."
        p2 = f"With the professional eye of a {s['role']}, {s['protagonist']} began {s['role_logic']['action_modifier']} the {obj_alias}."
        p3 = f"The {obj_alias} bore markings that suggested a legacy far more complex than a simple {s['obj_type']}."
        p4 = f"It became clear that to {s['action']} this discovery would be a significant challenge."
        p5 = f"The deeper {s['protagonist']} looked, the more the complexity of the situation revealed itself."
        
        reaction_templates = [
            f"The implications of the find sent a chill through the {s['role']}.",
            f"Finding the {obj_alias} was a catalyst that could not be ignored.",
            f"The weight of the {obj_alias} felt like both a burden and a promise.",
            f"Every instinct honed by years of experience told {s['protagonist']} that this was the moment they had been waiting for."
        ]
        return f"{p1}\n{p2}.\n{p3}\n{p4}.\n{p5}\n{random.choice(reaction_templates)}"

    def _escalation(self):
        s = self.state
        city_alias = self.get_variant(s["location"], "city")
        obj_alias = self.get_variant(s["obj"], s["obj_type"])
        
        p1 = f"Rumors of the {obj_alias} quickly reached {s['antagonist']}, a figure who operated in the darker corners of {city_alias}."
        p2 = f"This rival had spent years seeking exactly this kind of power."
        p3 = f"The streets began to feel smaller as shadows seemed to follow {s['protagonist']}'s every move through the old district."
        p4 = f"Whispers of betrayal and coded messages began to fill the humid afternoon air."
        p5 = f"No corner of {city_alias} seemed safe from the reaching grasp of the opposition."
        
        tension_templates = [
            f"A game of cat and mouse ensued across the region.",
            f"The stakes rose with every passing hour as {s['antagonist']} closed the gap.",
            f"Pressure mounted, forcing the {s['role']} to make a choice between safety and the truth.",
            f"The once-familiar landmarks of {city_alias} now seemed like obstacles in a desperate race."
        ]
        return f"{p1}\n{p2}.\n{p3}\n{p4}.\n{p5}\n{random.choice(tension_templates)}"

    def _climax(self):
        s = self.state
        city_alias = self.get_variant(s["location"], "city")
        obj_alias = self.get_variant(s["obj"], s["obj_type"])
        
        p1 = f"The final confrontation occurred in the shadow of the old quarter."
        p2 = f"As the moon rose over {city_alias}, the two factions finally crossed paths."
        p3 = f"In a bold move, {s['protagonist']} {s['role_logic']['climax_move']} {obj_alias}."
        p4 = f"Faced with the evidence, {s['antagonist']} found their influence in the bustling region suddenly crumbling."
        p5 = f"The air cracked with the intensity of the standoff as the final cards were played."
        
        action_templates = [
            "A sudden shift in momentum turned the tide of the struggle.",
            "In a decisive moment, the truth was finally laid bare.",
            "The carefully constructed lies of the opposition fell apart under scrutiny.",
            "The silence that followed was more powerful than any outcry could ever be."
        ]
        return f"{p1}\n{p2}.\n{p3}\n{p4}.\n{p5}\n{random.choice(action_templates)}"

    def _resolution(self):
        s = self.state
        city_alias = self.get_variant(s["location"], "city")
        p1 = f"With the {s['obj_type']} finally secured, {s['location']} entered a new period of relative calm."
        p2 = f"{s['protagonist']} returned to their life, but the environment felt different now."
        p3 = f"The story of {s['protagonist']} and {s['antagonist']} faded into a local legend, whispered in the quiet corners of the old city."
        p4 = f"The echoes of their struggle would remain as a warning to those who came after."
        p5 = f"As a new day dawned, the {city_alias} stood resilient against the tides of time."
        
        ending_templates = [
            "History would remember this intervention, even if the details were lost to time.",
            "A sense of balance had been restored to the region, at least for the moment.",
            "The future of the region now rested on a more solid foundation.",
            "In the end, it was not just about the object, but the spirit of those who protected it."
        ]
        return f"{p1}\n{p2}\n{p3}\n{p4}.\n{p5}\n{random.choice(ending_templates)}"

if __name__ == "__main__":
    engine = StoryEngine()
    print(engine.generate_story("Hyderabad", 1920, "urban"))
