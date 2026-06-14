import type {
  Story,
  Chapter,
  Character,
  StoryBible,
  BibleEntry,
  Thread,
  TimelineEvent,
  AnalyticsData,
  DashboardStats,
} from "@/types"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:5001"

class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

async function fetchWithRetry<T>(
  url: string,
  options: RequestInit = {},
  retries = 3
): Promise<T> {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
      })
      if (!res.ok) {
        throw new ApiError(`HTTP ${res.status}`, res.status)
      }
      return await res.json()
    } catch (err) {
      if (i === retries - 1) throw err
      await new Promise((r) => setTimeout(r, 1000 * (i + 1)))
    }
  }
  throw new Error("Max retries exceeded")
}

export const api = {
  health: () => fetchWithRetry<{ status: string }>(`${API_BASE}/api/health`),

  getDashboardStats: () =>
    fetchWithRetry<DashboardStats>(`${API_BASE}/api/dashboard/stats`),

  getStories: () => fetchWithRetry<Story[]>(`${API_BASE}/api/stories`),

  getStory: (id: string) => fetchWithRetry<Story>(`${API_BASE}/api/stories/${id}`),

  createStory: (data: Partial<Story>) =>
    fetchWithRetry<Story>(`${API_BASE}/api/stories`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  deleteStory: (id: string) =>
    fetchWithRetry<void>(`${API_BASE}/api/stories/${id}`, { method: "DELETE" }),

  getChapters: (storyId: string) =>
    fetchWithRetry<Chapter[]>(`${API_BASE}/api/stories/${storyId}/chapters`),

  generateChapter: (storyId: string) =>
    fetchWithRetry<Chapter>(`${API_BASE}/api/stories/${storyId}/generate`, {
      method: "POST",
    }),

  generateStory: (data: {
    location: string
    year: number
    story_mode: string
    genre: string
    theme: string
    characters?: string[]
  }) => fetchWithRetry<Story>(`${API_BASE}/api/generate`, {
    method: "POST",
    body: JSON.stringify(data),
  }),

  evaluateStory: (storyId: string) =>
    fetchWithRetry<{ score: number }>(`${API_BASE}/api/evaluate`, {
      method: "POST",
      body: JSON.stringify({ story_id: storyId }),
    }),

  getCharacters: () => fetchWithRetry<Character[]>(`${API_BASE}/api/characters`),

  getCharacter: (id: string) =>
    fetchWithRetry<Character>(`${API_BASE}/api/characters/${id}`),

  createCharacter: (data: Partial<Character>) =>
    fetchWithRetry<Character>(`${API_BASE}/api/characters`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateCharacter: (id: string, data: Partial<Character>) =>
    fetchWithRetry<Character>(`${API_BASE}/api/characters/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteCharacter: (id: string) =>
    fetchWithRetry<void>(`${API_BASE}/api/characters/${id}`, {
      method: "DELETE",
    }),

  getStoryBible: () => fetchWithRetry<StoryBible>(`${API_BASE}/api/bible`),

  updateBibleEntry: (section: string, id: string, data: Partial<BibleEntry>) =>
    fetchWithRetry<BibleEntry>(`${API_BASE}/api/bible/${section}/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  getThreads: () => fetchWithRetry<Thread[]>(`${API_BASE}/api/threads`),

  updateThread: (id: string, data: Partial<Thread>) =>
    fetchWithRetry<Thread>(`${API_BASE}/api/threads/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  getTimeline: (storyId: string) =>
    fetchWithRetry<TimelineEvent[]>(`${API_BASE}/api/stories/${storyId}/timeline`),

  getAnalytics: () =>
    fetchWithRetry<AnalyticsData>(`${API_BASE}/api/analytics`),

  getObservabilityPrompt: () =>
    fetchWithRetry<{ current: string; history: { timestamp: string; preview: string }[] }>(`${API_BASE}/api/observability/prompt`),

  getObservabilityContext: () =>
    fetchWithRetry<{ current: Record<string, unknown>; history: { timestamp: string; keys: string[] }[] }>(`${API_BASE}/api/observability/context`),

  getObservabilityRetrieval: () =>
    fetchWithRetry<{ current: Record<string, unknown>[]; history: { timestamp: string; count: number }[] }>(`${API_BASE}/api/observability/retrieval`),

  getObservabilityPredictor: () =>
    fetchWithRetry<{ current: Record<string, unknown>; history: { timestamp: string; output: Record<string, unknown> }[] }>(`${API_BASE}/api/observability/predictor`),
}
