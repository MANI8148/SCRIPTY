import { create } from "zustand"
import type { Story, Character, Thread, Settings, DashboardStats } from "@/types"

interface AppState {
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
  toggleSidebar: () => void

  stories: Story[]
  setStories: (stories: Story[]) => void
  addStory: (story: Story) => void
  removeStory: (id: string) => void

  characters: Character[]
  setCharacters: (characters: Character[]) => void
  addCharacter: (character: Character) => void
  updateCharacter: (id: string, data: Partial<Character>) => void
  removeCharacter: (id: string) => void

  threads: Thread[]
  setThreads: (threads: Thread[]) => void

  stats: DashboardStats | null
  setStats: (stats: DashboardStats) => void

  settings: Settings
  updateSettings: (settings: Partial<Settings>) => void
}

const defaultSettings: Settings = {
  model: "gpt-4",
  api_endpoint: "http://127.0.0.1:5001",
  generation_params: {
    temperature: 0.8,
    top_p: 0.9,
    max_tokens: 2000,
    model: "gpt-4",
  },
  dark_mode: true,
}

export const useStore = create<AppState>((set) => ({
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  stories: [],
  setStories: (stories) => set({ stories }),
  addStory: (story) => set((s) => ({ stories: [story, ...s.stories] })),
  removeStory: (id) =>
    set((s) => ({ stories: s.stories.filter((st) => st.id !== id) })),

  characters: [],
  setCharacters: (characters) => set({ characters }),
  addCharacter: (character) =>
    set((s) => ({ characters: [...s.characters, character] })),
  updateCharacter: (id, data) =>
    set((s) => ({
      characters: s.characters.map((c) =>
        c.id === id ? { ...c, ...data } : c
      ),
    })),
  removeCharacter: (id) =>
    set((s) => ({
      characters: s.characters.filter((c) => c.id !== id),
    })),

  threads: [],
  setThreads: (threads) => set({ threads }),

  stats: null,
  setStats: (stats) => set({ stats }),

  settings: defaultSettings,
  updateSettings: (newSettings) =>
    set((s) => ({
      settings: { ...s.settings, ...newSettings },
    })),
}))
