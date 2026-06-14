"use client"


import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  MarkerType,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/services/api"
import type { Character, Relationship } from "@/types"
import { Skeleton } from "@/components/ui/skeleton"

const RELATIONSHIP_COLORS: Record<string, string> = {
  ally: "#22c55e",
  enemy: "#ef4444",
  family: "#a855f7",
  mentor: "#3b82f6",
  rival: "#f59e0b",
  neutral: "#6b7280",
}

export default function CharacterGraphPage() {
  const { data: characters, isLoading } = useQuery({
    queryKey: ["characters"],
    queryFn: api.getCharacters,
  })

  const nodes: Node[] = (characters ?? []).map((char: Character, i: number) => ({
    id: char.id,
    type: "default",
    position: {
      x: 200 + Math.cos((2 * Math.PI * i) / (characters?.length || 1)) * 200,
      y: 200 + Math.sin((2 * Math.PI * i) / (characters?.length || 1)) * 200,
    },
    data: {
      label: (
        <div className="flex flex-col items-center p-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 font-bold text-sm">
            {char.name[0]}
          </div>
          <span className="text-xs font-medium mt-1">{char.name}</span>
          <span className="text-[10px] text-muted-foreground">{char.role}</span>
          <Badge variant="outline" className="text-[10px] mt-1">
            {char.emotional_state}
          </Badge>
        </div>
      ),
    },
    style: {
      background: "hsl(var(--card))",
      border: "1px solid hsl(var(--border))",
      borderRadius: 12,
      padding: 8,
      minWidth: 140,
    },
  }))

  const edges: Edge[] = (characters ?? []).flatMap((char: Character) =>
    (char.relationships ?? []).map((rel: Relationship) => ({
      id: `${char.id}-${rel.target_id}`,
      source: char.id,
      target: rel.target_id,
      label: rel.type,
      style: {
        stroke: RELATIONSHIP_COLORS[rel.type] || "#6b7280",
        strokeWidth: 2,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: RELATIONSHIP_COLORS[rel.type] || "#6b7280",
      },
    }))
  )

  const [nodeState, setNodeState, onNodesChange] = useNodesState(nodes)
  const [edgeState, setEdgeState, onEdgesChange] = useEdgesState(edges)

  // Update nodes/edges when data changes
  if (!isLoading && characters && (nodeState.length === 0 || nodeState.length !== characters.length)) {
    setNodeState(nodes)
    setEdgeState(edges)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Character Graph</h1>
        <p className="text-muted-foreground">
          Visualize character relationships
        </p>
      </div>

      <div className="flex gap-2 flex-wrap">
        {Object.entries(RELATIONSHIP_COLORS).map(([type, color]) => (
          <Badge
            key={type}
            variant="outline"
            className="flex items-center gap-1.5"
          >
            <span
              className="h-2 w-2 rounded-full"
              style={{ background: color }}
            />
            {type}
          </Badge>
        ))}
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <Skeleton className="h-[500px] w-full" />
          ) : (
            <div className="h-[500px]">
              <ReactFlow
                nodes={nodeState}
                edges={edgeState}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                fitView
                attributionPosition="bottom-left"
              >
                <Background />
                <Controls />
                <MiniMap
                  className="border rounded-lg"
                  style={{ background: "hsl(var(--card))" }}
                />
              </ReactFlow>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
