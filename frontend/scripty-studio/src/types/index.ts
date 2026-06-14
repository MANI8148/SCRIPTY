export interface Story {
  id: string
  title: string
  genre: string
  theme: string
  location: string
  year: number
  mode: "SHORT" | "CHAPTER" | "BOOK"
  chapter_count: number
  coherence_score: number
  created_at: string
  updated_at: string
}

export interface Chapter {
  id: string
  story_id: string
  number: number
  title: string
  content: string
  scene_count: number
  word_count: number
  coherence_score: number
  created_at: string
}

export interface Character {
  id: string
  name: string
  role: string
  goals: string[]
  beliefs: string[]
  emotional_state: string
  relationships: Relationship[]
  secrets: string[]
  arc_stage: string
  personality: string[]
}

export interface Relationship {
  target_id: string
  target_name: string
  type: "ally" | "enemy" | "family" | "mentor" | "rival" | "neutral"
  strength: number
}

export interface StoryBible {
  locations: BibleEntry[]
  factions: BibleEntry[]
  lore: BibleEntry[]
  themes: string[]
  rules: string[]
}

export interface BibleEntry {
  id: string
  title: string
  content: string
  last_modified: string
}

export interface Thread {
  id: string
  title: string
  description: string
  status: "open" | "progressing" | "resolved"
  urgency: number
  importance: number
  age: number
  characters: string[]
  created_at: string
}

export interface TimelineEvent {
  id: string
  chapter_id: string
  chapter_number: number
  type: "chapter" | "event" | "mystery" | "discovery" | "conflict"
  title: string
  description: string
  position: number
}

export interface AnalyticsData {
  coherence_trend: { chapter: number; score: number }[]
  character_consistency: { character: string; score: number }[]
  thread_health: { thread: string; status: string; score: number }[]
  memory_usage: { type: string; count: number }[]
  predictor_influence: { predictor: string; influence: number }[]
  generation_stats: {
    total_stories: number
    total_chapters: number
    avg_coherence: number
    avg_word_count: number
    total_characters: number
    total_threads: number
  }
}

export interface DashboardStats {
  total_stories: number
  total_chapters: number
  active_characters: number
  open_threads: number
  avg_coherence: number
}

export interface GenerationParams {
  temperature: number
  top_p: number
  max_tokens: number
  model: string
}

export interface Settings {
  model: string
  api_endpoint: string
  generation_params: GenerationParams
  dark_mode: boolean
}
