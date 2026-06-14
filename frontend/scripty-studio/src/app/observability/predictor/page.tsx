"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/services/api"
import { Cpu } from "lucide-react"

export default function PredictorPage() {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ["observability-predictor"],
    queryFn: api.getObservabilityPredictor,
  })

  const history = data?.history ?? []
  const current = data?.current ?? {}

  const sceneTypes: Record<string, unknown> = (current.scene_types as Record<string, unknown>) ?? {}
  const selectedSceneType = (current.selected_scene as string) ?? ""
  const tension = (current.tension as number) ?? 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Cpu className="h-7 w-7" />
          Predictor Viewer
        </h1>
        <p className="text-muted-foreground">
          Scene type predictions and probabilities
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
                <Cpu className="h-5 w-5" />
                Current Prediction
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="space-y-3">
                  {Object.entries(sceneTypes).map(([type, prob]) => {
                    const probability = Number(prob) || 0
                    const isSelected = type === selectedSceneType
                    return (
                      <div key={type} className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className="flex items-center gap-2">
                            {isSelected && (
                              <span className="h-2 w-2 rounded-full bg-primary" />
                            )}
                            <span className={isSelected ? "font-medium" : ""}>
                              {type}
                            </span>
                          </span>
                          <span className="text-muted-foreground">
                            {(probability * 100).toFixed(1)}%
                          </span>
                        </div>
                        <Progress
                          value={probability * 100}
                          className={`h-2 ${isSelected ? "bg-primary/20" : ""}`}
                        />
                      </div>
                    )
                  })}
                </div>

                <Separator />

                <div>
                  <p className="text-sm text-muted-foreground mb-1">Tension</p>
                  <div className="flex items-center gap-3">
                    <Progress value={tension * 100} className="h-3 flex-1" />
                    <span className="text-sm font-medium min-w-[3rem] text-right">
                      {(tension * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
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
                    {history.map((entry, i) => {
                      const output = entry.output ?? {}
                      const selected = (output.selected_scene as string) ?? "unknown"
                      return (
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
                          <p className="text-sm mt-1 capitalize">
                            Selected: {selected.replace(/_/g, " ")}
                          </p>
                        </button>
                      )
                    })}
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
