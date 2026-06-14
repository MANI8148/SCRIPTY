"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/services/api"
import { Database } from "lucide-react"

export default function RetrievalPage() {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ["observability-retrieval"],
    queryFn: api.getObservabilityRetrieval,
  })

  const history = data?.history ?? []
  const current = data?.current ?? []
  const displayPassages = selectedIndex !== null ? current : current

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Database className="h-7 w-7" />
          Retrieval Viewer
        </h1>
        <p className="text-muted-foreground">
          Inspect retrieved context passages and their relevance
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-3">
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Database className="h-5 w-5" />
                Retrieved Passages
              </CardTitle>
            </CardHeader>
            <CardContent>
              {displayPassages.length === 0 ? (
                <p className="text-muted-foreground text-sm">No passages retrieved.</p>
              ) : (
                <ScrollArea className="h-[500px]">
                  <div className="space-y-3">
                    {displayPassages.map((passage, i) => {
                      const source = (passage as Record<string, unknown>).source as string ?? `Passage ${i + 1}`
                      const score = (passage as Record<string, unknown>).score as number ?? 0
                      const content = (passage as Record<string, unknown>).content as string ?? JSON.stringify(passage)
                      return (
                        <div key={i} className="rounded-lg border p-4">
                          <div className="flex items-start justify-between mb-2">
                            <Badge variant="secondary" className="text-xs">
                              {source}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {Math.round(score * 100)}% relevant
                            </span>
                          </div>
                          <Progress value={score * 100} className="h-1.5 mb-3" />
                          <p className="text-sm text-muted-foreground line-clamp-3">
                            {content}
                          </p>
                        </div>
                      )
                    })}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">History</CardTitle>
            </CardHeader>
            <CardContent>
              {history.length === 0 ? (
                <p className="text-muted-foreground text-sm">No history available.</p>
              ) : (
                <ScrollArea className="h-[500px]">
                  <div className="space-y-2">
                    {history.map((entry, i) => (
                      <button
                        key={i}
                        onClick={() => setSelectedIndex(selectedIndex === i ? null : i)}
                        className={`w-full text-left rounded-lg border p-3 transition-colors hover:bg-accent ${
                          selectedIndex === i ? "border-primary bg-accent" : ""
                        }`}
                      >
                        <p className="text-xs text-muted-foreground">
                          {entry.timestamp}
                        </p>
                        <p className="text-sm mt-1">
                          {entry.count} passage{entry.count !== 1 ? "s" : ""} retrieved
                        </p>
                      </button>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
