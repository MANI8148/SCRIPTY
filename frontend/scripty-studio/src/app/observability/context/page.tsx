"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/services/api"
import { FileJson } from "lucide-react"

export default function ContextPage() {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ["observability-context"],
    queryFn: api.getObservabilityContext,
  })

  const history = data?.history ?? []
  const current = data?.current ?? {}
  const displayedKeys = selectedIndex !== null
    ? history[selectedIndex]?.keys ?? []
    : Object.keys(current)

  const displayedContext = selectedIndex !== null
    ? Object.fromEntries(displayedKeys.map((k) => [k, null]))
    : current

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <FileJson className="h-7 w-7" />
          Context Inspector
        </h1>
        <p className="text-muted-foreground">
          Inspect context passed to the LLM
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
                <FileJson className="h-5 w-5" />
                {selectedIndex !== null ? "Historical Context" : "Current Context"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {Object.keys(displayedContext).length === 0 ? (
                <p className="text-muted-foreground text-sm">No context data available.</p>
              ) : (
                <ScrollArea className="h-[500px]">
                  <div className="space-y-4">
                    {Object.entries(selectedIndex !== null ? current : current).map(
                      ([key, value]) => (
                        <div key={key}>
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="secondary">{key}</Badge>
                          </div>
                          <pre className="text-sm font-mono whitespace-pre-wrap rounded-md bg-muted p-3">
                            {value !== null
                              ? typeof value === "object"
                                ? JSON.stringify(value, null, 2)
                                : String(value)
                              : "N/A"}
                          </pre>
                        </div>
                      )
                    )}
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
                        <div className="flex flex-wrap gap-1 mt-1">
                          {entry.keys.map((k) => (
                            <Badge key={k} variant="outline" className="text-xs">
                              {k}
                            </Badge>
                          ))}
                        </div>
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
