"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/services/api"
import { GitBranch, AlertTriangle, Clock, TrendingUp, Users } from "lucide-react"
import type { Thread } from "@/types"

const STATUS_COLORS = {
  open: "destructive" as const,
  progressing: "warning" as const,
  resolved: "success" as const,
}

export default function ThreadsPage() {
  const { data: threads, isLoading } = useQuery({
    queryKey: ["threads"],
    queryFn: api.getThreads,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Thread Tracker</h1>
        <p className="text-muted-foreground">
          Track open narrative threads and subplots
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Open</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-destructive">
              {threads?.filter((t) => t.status === "open").length ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Progressing</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-amber-500">
              {threads?.filter((t) => t.status === "progressing").length ?? 0}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Resolved</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-emerald-500">
              {threads?.filter((t) => t.status === "resolved").length ?? 0}
            </p>
          </CardContent>
        </Card>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-1/2" />
                <Skeleton className="h-4 w-1/3" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (threads ?? []).length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <GitBranch className="h-12 w-12 text-muted-foreground/50" />
          <h3 className="mt-4 text-lg font-medium">No threads yet</h3>
          <p className="text-sm text-muted-foreground">
            Threads will appear as your story develops
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {threads?.map((thread: Thread) => (
            <Card key={thread.id}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-base">{thread.title}</CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">
                      {thread.description}
                    </p>
                  </div>
                  <Badge variant={STATUS_COLORS[thread.status]}>
                    {thread.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-6 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    Urgency: {thread.urgency}/10
                  </span>
                  <span className="flex items-center gap-1">
                    <TrendingUp className="h-3 w-3" />
                    Importance: {thread.importance}/10
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {thread.age} days old
                  </span>
                  <span className="flex items-center gap-1">
                    <Users className="h-3 w-3" />
                    {(thread.characters ?? []).length} characters
                  </span>
                </div>
                {(thread.characters ?? []).length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-3">
                    {thread.characters.map((char: string, i: number) => (
                      <Badge key={i} variant="secondary" className="text-xs">
                        {char}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
