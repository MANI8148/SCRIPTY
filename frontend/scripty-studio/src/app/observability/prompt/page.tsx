"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/services/api"
import { Terminal } from "lucide-react"

export default function PromptPage() {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ["observability-prompt"],
    queryFn: api.getObservabilityPrompt,
  })

  const history = data?.history ?? []
  const selectedHistory = selectedIndex !== null ? history[selectedIndex] : null
  const displayPrompt = selectedHistory ? selectedHistory.preview : data?.current

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Terminal className="h-7 w-7" />
          Prompt Inspector
        </h1>
        <p className="text-muted-foreground">
          View current and historical prompt snapshots
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
                <Terminal className="h-5 w-5" />
                {selectedHistory ? "Historical Prompt" : "Current Prompt"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {displayPrompt ? (
                <ScrollArea className="h-[500px] w-full rounded-md border p-4">
                  <pre className="text-sm font-mono whitespace-pre-wrap">
                    {displayPrompt}
                  </pre>
                </ScrollArea>
              ) : (
                <p className="text-muted-foreground text-sm">No prompt data available.</p>
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
                        <p className="text-sm mt-1 line-clamp-2">{entry.preview}</p>
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
