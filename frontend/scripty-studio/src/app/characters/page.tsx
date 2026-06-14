"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/services/api"
import type { Character, Relationship } from "@/types"
import {
  Plus,
  Users,
  Pencil,
  Trash2,
  User,
} from "lucide-react"
import { toast } from "sonner"

export default function CharactersPage() {
  const [editingChar, setEditingChar] = useState<Character | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const queryClient = useQueryClient()

  const { data: characters, isLoading } = useQuery({
    queryKey: ["characters"],
    queryFn: api.getCharacters,
  })

  const createMutation = useMutation({
    mutationFn: api.createCharacter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["characters"] })
      setDialogOpen(false)
      toast.success("Character created")
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Character> }) =>
      api.updateCharacter(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["characters"] })
      setEditingChar(null)
      toast.success("Character updated")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: api.deleteCharacter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["characters"] })
      toast.success("Character deleted")
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const form = e.target as HTMLFormElement
    const data = Object.fromEntries(new FormData(form))
    if (editingChar) {
      updateMutation.mutate({ id: editingChar.id, data: data as unknown as Partial<Character> })
    } else {
      createMutation.mutate(data as unknown as Partial<Character>)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Characters</h1>
          <p className="text-muted-foreground">Manage your story characters</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Character
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>
                {editingChar ? "Edit Character" : "New Character"}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    name="name"
                    defaultValue={editingChar?.name}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="role">Role</Label>
                  <Input
                    id="role"
                    name="role"
                    defaultValue={editingChar?.role}
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="emotional_state">Emotional State</Label>
                <Input
                  id="emotional_state"
                  name="emotional_state"
                  defaultValue={editingChar?.emotional_state}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="goals">Goals (comma-separated)</Label>
                <Input
                  id="goals"
                  name="goals"
                  defaultValue={editingChar?.goals?.join(", ")}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="beliefs">Beliefs (comma-separated)</Label>
                <Input
                  id="beliefs"
                  name="beliefs"
                  defaultValue={editingChar?.beliefs?.join(", ")}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="secrets">Secrets (comma-separated)</Label>
                <Input
                  id="secrets"
                  name="secrets"
                  defaultValue={editingChar?.secrets?.join(", ")}
                />
              </div>
              <Button type="submit" className="w-full">
                {editingChar ? "Save Changes" : "Create Character"}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </CardHeader>
              <CardContent className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (characters ?? []).length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Users className="h-12 w-12 text-muted-foreground/50" />
          <h3 className="mt-4 text-lg font-medium">No characters yet</h3>
          <p className="text-sm text-muted-foreground">
            Create characters to populate your story
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {characters?.map((char) => (
            <Card key={char.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                      <User className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{char.name}</CardTitle>
                      <p className="text-sm text-muted-foreground">
                        {char.role}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => {
                        setEditingChar(char)
                        setDialogOpen(true)
                      }}
                    >
                      <Pencil className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive"
                      onClick={() => deleteMutation.mutate(char.id)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">
                    Emotional State
                  </p>
                  <Badge variant="outline">{char.emotional_state}</Badge>
                </div>
                <Separator />
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Goals</p>
                  <div className="flex flex-wrap gap-1">
                    {(char.goals ?? []).map((g: string, i: number) => (
                      <Badge key={i} variant="secondary" className="text-xs">
                        {g}
                      </Badge>
                    ))}
                  </div>
                </div>
                <Separator />
                <div>
                  <p className="text-xs text-muted-foreground mb-1">
                    Relationships
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {(char.relationships ?? []).map(
                      (r: Relationship, i: number) => (
                        <Badge key={i} variant="outline" className="text-xs">
                          {r.target_name} ({r.type})
                        </Badge>
                      )
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
