import {
  LayoutDashboard,
  BookOpen,
  Users,
  ScrollText,
  GitBranch,
  BarChart3,
  Settings,
  Terminal,
  FileJson,
  Database,
  Cpu,
  type LucideIcon,
} from "lucide-react"

export interface NavItem {
  label: string
  href: string
  icon: LucideIcon
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Stories", href: "/stories", icon: BookOpen },
  { label: "Characters", href: "/characters", icon: Users },
  { label: "Story Bible", href: "/story-bible", icon: ScrollText },
  { label: "Threads", href: "/threads", icon: GitBranch },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "Inspectors", href: "/observability/prompt", icon: Terminal },
  { label: "Settings", href: "/settings", icon: Settings },
]

export const GENRES = [
  "Historical Fiction",
  "Fantasy",
  "Sci-Fi",
  "Mystery",
  "Romance",
  "Thriller",
  "Adventure",
  "Drama",
] as const

export const MODES = ["SHORT", "CHAPTER", "BOOK"] as const

export const RELATIONSHIP_TYPES = [
  "ally",
  "enemy",
  "family",
  "mentor",
  "rival",
  "neutral",
] as const

export const THREAD_STATUSES = ["open", "progressing", "resolved"] as const

export const TIMELINE_EVENT_TYPES = [
  "chapter",
  "event",
  "mystery",
  "discovery",
  "conflict",
] as const

export const MODELS = ["gpt-4", "gpt-3.5-turbo", "claude-3", "llama3", "qwen"] as const
