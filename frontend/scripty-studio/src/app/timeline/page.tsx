"use client"

import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useQuery } from "@tanstack/react-query"
import type { TimelineEvent } from "@/types"
import {
  ZoomIn,
  ZoomOut,
  BookOpen,
  Sparkles,
  Search,
  Eye,
  Swords,
} from "lucide-react"

const EVENT_ICONS: Record<string, React.ReactNode> = {
  chapter: <BookOpen className="h-4 w-4" />,
  event: <Sparkles className="h-4 w-4" />,
  mystery: <Search className="h-4 w-4" />,
  discovery: <Eye className="h-4 w-4" />,
  conflict: <Swords className="h-4 w-4" />,
}

const EVENT_COLORS: Record<string, string> = {
  chapter: "border-blue-500 bg-blue-500/10",
  event: "border-green-500 bg-green-500/10",
  mystery: "border-purple-500 bg-purple-500/10",
  discovery: "border-amber-500 bg-amber-500/10",
  conflict: "border-red-500 bg-red-500/10",
}

export default function TimelinePage() {
  const [zoom, setZoom] = useState(1)

  // Using threads as sample data - in production this would use api.getTimeline
  const { data: events, isLoading } = useQuery({
    queryKey: ["timeline"],
    queryFn: async () => {
      // Sample timeline data for demonstration
      return [
        { id: "1", chapter_id: "c1", chapter_number: 1, type: "chapter", title: "The Beginning", description: "Story opens in London, 1850", position: 1 },
        { id: "2", chapter_id: "c1", chapter_number: 1, type: "event", title: "First Meeting", description: "Eleanor meets James at the factory", position: 2 },
        { id: "3", chapter_id: "c1", chapter_number: 1, type: "mystery", title: "The Missing Ledger", description: "Factory records go missing", position: 3 },
        { id: "4", chapter_id: "c2", chapter_number: 2, type: "chapter", title: "Dark Discoveries", description: "Secrets begin to surface", position: 4 },
        { id: "5", chapter_id: "c2", chapter_number: 2, type: "discovery", title: "Hidden Truth", description: "Eleanor finds evidence of corruption", position: 5 },
        { id: "6", chapter_id: "c2", chapter_number: 2, type: "conflict", title: "Confrontation", description: "Workers confront the factory owner", position: 6 },
        { id: "7", chapter_id: "c3", chapter_number: 3, type: "chapter", title: "Rising Tension", description: "The situation escalates", position: 7 },
        { id: "8", chapter_id: "c3", chapter_number: 3, type: "event", title: "Alliance Formed", description: "Characters unite against common foe", position: 8 },
        { id: "9", chapter_id: "c3", chapter_number: 3, type: "mystery", title: "Who Is the Benefactor?", description: "Anonymous support emerges", position: 9 },
      ] as TimelineEvent[]
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Timeline</h1>
          <p className="text-muted-foreground">
            Story events in chronological order
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={() => setZoom((z) => Math.min(z + 0.2, 2))}
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setZoom((z) => Math.max(z - 0.2, 0.5))}
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {isLoading ? (
        <Skeleton className="h-[400px] w-full" />
      ) : (
        <Card>
          <CardContent className="p-6">
            <div
              className="relative"
              style={{ transform: `scale(${zoom})`, transformOrigin: "top left" }}
            >
              {/* Timeline line */}
              <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-border" />

              <div className="space-y-6 relative">
                {(events ?? []).map((event: TimelineEvent) => (
                  <div key={event.id} className="relative pl-14">
                    {/* Timeline dot */}
                    <div
                      className={`absolute left-4 w-4 h-4 rounded-full border-2 -translate-x-1/2 mt-1.5 ${EVENT_COLORS[event.type] || "border-gray-500"}`}
                    />

                    {/* Content card */}
                    <div className="rounded-lg border p-4 hover:bg-accent/50 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">
                            {EVENT_ICONS[event.type]}
                          </span>
                          <div>
                            <p className="font-medium">{event.title}</p>
                            <p className="text-sm text-muted-foreground">
                              {event.description}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            Ch. {event.chapter_number}
                          </Badge>
                          <Badge
                            variant="outline"
                            className="text-xs capitalize"
                          >
                            {event.type}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
