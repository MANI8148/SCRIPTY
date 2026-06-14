"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/services/api"
import {
  BookOpen,
  FileText,
  Users,
  GitBranch,
  TrendingUp,
  UserCheck,
  Layers,
} from "lucide-react"
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts"

const statCards = [
  { label: "Total Stories", icon: BookOpen, color: "text-blue-500", key: "total_stories" as const },
  { label: "Chapters Generated", icon: FileText, color: "text-green-500", key: "total_chapters" as const },
  { label: "Active Characters", icon: Users, color: "text-purple-500", key: "active_characters" as const },
  { label: "Open Threads", icon: GitBranch, color: "text-amber-500", key: "open_threads" as const },
  { label: "Avg Coherence", icon: TrendingUp, color: "text-cyan-500", key: "avg_coherence" as const },
]

const recentStories = [
  { title: "The London Fog", genre: "Mystery", chapters: 12, coherence: 0.87, date: "2h ago" },
  { title: "Empire of Dust", genre: "Historical Fiction", chapters: 8, coherence: 0.82, date: "5h ago" },
  { title: "Stars Beyond", genre: "Sci-Fi", chapters: 15, coherence: 0.79, date: "1d ago" },
  { title: "The Last Kingdom", genre: "Fantasy", chapters: 20, coherence: 0.91, date: "2d ago" },
]

const threadHealth = [
  { thread: "Main Quest", status: "open", score: 85 },
  { thread: "Character Arc A", status: "progressing", score: 65 },
  { thread: "Subplot B", status: "resolved", score: 100 },
  { thread: "Mystery C", status: "open", score: 40 },
]

const characterActivity = [
  { character: "Eleanor", scenes: 12, dialogues: 8 },
  { character: "James", scenes: 10, dialogues: 6 },
  { character: "Margaret", scenes: 7, dialogues: 5 },
  { character: "Thomas", scenes: 5, dialogues: 3 },
]

const generationActivity = [
  { day: "Mon", chapters: 3 },
  { day: "Tue", chapters: 5 },
  { day: "Wed", chapters: 2 },
  { day: "Thu", chapters: 7 },
  { day: "Fri", chapters: 4 },
  { day: "Sat", chapters: 6 },
  { day: "Sun", chapters: 3 },
]

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: api.getDashboardStats,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Welcome to Scripty Studio</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {statCards.map((card) => (
          <Card key={card.key}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {card.label}
              </CardTitle>
              <card.icon className={`h-4 w-4 ${card.color}`} />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-20" />
              ) : (
                <div className="text-2xl font-bold">
                  {stats?.[card.key] ?? "--"}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-lg">Recent Stories</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentStories.map((story) => (
                <div
                  key={story.title}
                  className="flex items-center justify-between border-b pb-2 last:border-0"
                >
                  <div>
                    <p className="font-medium">{story.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {story.genre} · {story.chapters} chapters
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">
                      {(story.coherence * 100).toFixed(0)}%
                    </p>
                    <p className="text-xs text-muted-foreground">{story.date}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Thread Health</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {threadHealth.map((thread) => (
                <div key={thread.thread} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>{thread.thread}</span>
                    <span className="text-muted-foreground capitalize">
                      {thread.status}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{ width: `${thread.score}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Character Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {characterActivity.map((char) => (
                <div
                  key={char.character}
                  className="flex items-center gap-3"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-sm font-medium">
                    {char.character[0]}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{char.character}</p>
                    <p className="text-xs text-muted-foreground">
                      {char.scenes} scenes · {char.dialogues} dialogues
                    </p>
                  </div>
                  <div className="flex gap-2 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Layers className="h-3 w-3" />
                      {char.scenes}
                    </span>
                    <span className="flex items-center gap-1">
                      <UserCheck className="h-3 w-3" />
                      {char.dialogues}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Generation Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={generationActivity}>
                <defs>
                  <linearGradient id="colorChapters" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="day" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="chapters"
                  stroke="hsl(var(--primary))"
                  fillOpacity={1}
                  fill="url(#colorChapters)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
