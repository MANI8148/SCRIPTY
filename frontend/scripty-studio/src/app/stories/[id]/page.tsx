"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/services/api"
import type { Chapter } from "@/types"
import {
  Play,
  RefreshCw,
  Download,
  BookOpen,
  BarChart3,
} from "lucide-react"
import { toast } from "sonner"

export default function StoryWorkspacePage() {
  const params = useParams()
  const storyId = params.id as string
  const [activeChapter, setActiveChapter] = useState<number | null>(null)
  const queryClient = useQueryClient()

  const { data: story, isLoading: storyLoading } = useQuery({
    queryKey: ["story", storyId],
    queryFn: () => api.getStory(storyId),
  })

  const { data: chapters, isLoading: chaptersLoading } = useQuery({
    queryKey: ["chapters", storyId],
    queryFn: () => api.getChapters(storyId),
  })

  const generateMutation = useMutation({
    mutationFn: () => api.generateChapter(storyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chapters", storyId] })
      queryClient.invalidateQueries({ queryKey: ["story", storyId] })
      toast.success("Chapter generated!")
    },
  })

  const currentChapter = chapters?.[activeChapter ?? chapters.length - 1] ?? chapters?.[chapters.length - 1]

  if (storyLoading || chaptersLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-[250px_1fr_300px] gap-4">
          <Skeleton className="h-[600px]" />
          <Skeleton className="h-[600px]" />
          <Skeleton className="h-[600px]" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{story?.title}</h1>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Badge variant="secondary">{story?.genre}</Badge>
            <span>{story?.location}, {story?.year}</span>
            <Badge variant="outline">{story?.mode}</Badge>
            <Badge variant={story && story.coherence_score >= 0.8 ? "success" : "warning"}>
              {(story && (story.coherence_score * 100).toFixed(0)) ?? "--"}% coherence
            </Badge>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
            <Play className="h-4 w-4 mr-2" />
            {generateMutation.isPending ? "Generating..." : "Generate Chapter"}
          </Button>
          <Button variant="outline" disabled>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr_280px] gap-4">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-sm font-medium">Chapters</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[500px]">
              <div className="space-y-2">
                {(chapters ?? []).length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No chapters yet. Generate your first chapter.
                  </p>
                ) : (
                  chapters?.map((ch: Chapter, i: number) => (
                    <button
                      key={ch.id}
                      onClick={() => setActiveChapter(i)}
                      className={`w-full text-left p-3 rounded-lg text-sm transition-colors ${
                        activeChapter === i || (activeChapter === null && i === (chapters ?? []).length - 1)
                          ? "bg-accent"
                          : "hover:bg-accent/50"
                      }`}
                    >
                      <p className="font-medium">
                        Chapter {ch.number}: {ch.title}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {ch.word_count} words · {ch.scene_count} scenes
                      </p>
                    </button>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="lg:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">
              {currentChapter
                ? `Chapter ${currentChapter.number}: ${currentChapter.title}`
                : "Editor"}
            </CardTitle>
            {currentChapter && (
              <div className="flex gap-1">
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <RefreshCw className="h-3 w-3" />
                </Button>
              </div>
            )}
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[500px]">
              {currentChapter ? (
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {currentChapter.content}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-[500px] text-center">
                  <BookOpen className="h-12 w-12 text-muted-foreground/50" />
                  <p className="mt-4 text-sm text-muted-foreground">
                    No content yet. Generate a chapter to begin writing your story.
                  </p>
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-sm font-medium">Analytics</CardTitle>
          </CardHeader>
          <CardContent>
            {currentChapter ? (
              <div className="space-y-4">
                <div>
                  <p className="text-xs text-muted-foreground">Word Count</p>
                  <p className="text-lg font-bold">{currentChapter.word_count}</p>
                </div>
                <Separator />
                <div>
                  <p className="text-xs text-muted-foreground">Scenes</p>
                  <p className="text-lg font-bold">{currentChapter.scene_count}</p>
                </div>
                <Separator />
                <div>
                  <p className="text-xs text-muted-foreground">Coherence Score</p>
                  <p className="text-lg font-bold">
                    {(currentChapter.coherence_score * 100).toFixed(0)}%
                  </p>
                </div>
                <Separator />
                <div>
                  <p className="text-xs text-muted-foreground">Created</p>
                  <p className="text-sm">
                    {new Date(currentChapter.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-[200px] text-muted-foreground/50">
                <BarChart3 className="h-8 w-8" />
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
