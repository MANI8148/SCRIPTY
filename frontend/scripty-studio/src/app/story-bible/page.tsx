"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/services/api"
import type { BibleEntry } from "@/types"
import { ScrollText, Book, Map, Shield, Lightbulb, Scale, Plus } from "lucide-react"
import { toast } from "sonner"

const SECTIONS = [
  { id: "locations", label: "Locations", icon: Map },
  { id: "factions", label: "Factions", icon: Shield },
  { id: "lore", label: "Lore", icon: Book },
  { id: "themes", label: "Themes", icon: Lightbulb },
  { id: "rules", label: "Rules", icon: Scale },
]

export default function StoryBiblePage() {
  const [activeTab, setActiveTab] = useState("locations")
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState("")

  const { data: bible, isLoading } = useQuery({
    queryKey: ["bible"],
    queryFn: api.getStoryBible,
  })

  const entries = bible?.[activeTab as keyof typeof bible] ?? []

  const handleSave = () => {
    // In a real app, this would call the API
    toast.success("Entry saved")
    setEditingId(null)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Story Bible</h1>
          <p className="text-muted-foreground">
            World-building and narrative reference
          </p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          {SECTIONS.map((section) => (
            <TabsTrigger key={section.id} value={section.id} className="flex items-center gap-2">
              <section.icon className="h-4 w-4" />
              {section.label}
            </TabsTrigger>
          ))}
        </TabsList>

        {SECTIONS.map((section) => (
          <TabsContent key={section.id} value={section.id}>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  {Array.isArray(entries) ? entries.length : 0} entries
                </p>
                <Button variant="outline" size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Entry
                </Button>
              </div>

              {isLoading ? (
                <div className="space-y-4">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Card key={i}>
                      <CardHeader>
                        <Skeleton className="h-5 w-1/2" />
                      </CardHeader>
                      <CardContent>
                        <Skeleton className="h-20 w-full" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : Array.isArray(entries) && entries.length > 0 ? (
                (entries as BibleEntry[]).map((entry) => (
                  <Card key={entry.id}>
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <CardTitle className="text-base">
                          {entry.title}
                        </CardTitle>
                        <div className="flex gap-2">
                          <Badge variant="outline" className="text-xs">
                            {entry.last_modified
                              ? new Date(
                                  entry.last_modified
                                ).toLocaleDateString()
                              : "Recently"}
                          </Badge>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      {editingId === entry.id ? (
                        <div className="space-y-2">
                          <Textarea
                            value={editContent}
                            onChange={(e) => setEditContent(e.target.value)}
                            className="min-h-[100px]"
                          />
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setEditingId(null)}
                            >
                              Cancel
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => handleSave()}
                            >
                              Save
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div
                          className="prose prose-sm dark:prose-invert max-w-none cursor-pointer"
                          onClick={() => {
                            setEditingId(entry.id)
                            setEditContent(entry.content)
                          }}
                        >
                          <div className="whitespace-pre-wrap text-sm text-muted-foreground">
                            {entry.content || "Click to add content..."}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <ScrollText className="h-12 w-12 text-muted-foreground/50" />
                  <h3 className="mt-4 text-lg font-medium">No entries yet</h3>
                  <p className="text-sm text-muted-foreground">
                    Add entries to build your story bible
                  </p>
                </div>
              )}
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
