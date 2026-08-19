import { useState, useEffect, useMemo, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  type Node,
  type Edge,
  type NodeTypes,
} from "@xyflow/react";
import { TableNode } from "./TableNode";
import { mapSchemaToFlow, type TableNodeData } from "../utils/schemaFlowMapper";
import type { SchemaResponse } from "../api";

interface Props {
  schema: SchemaResponse | null;
  className?: string;
  showMiniMap?: boolean;
}

const nodeTypes: NodeTypes = {
  tableNode: TableNode,
};

export function SchemaDiagram({ schema, className = "h-full w-full", showMiniMap = true }: Props) {
  const [searchTerm, setSearchTerm] = useState("");

  const initialFlow = useMemo(() => {
    return mapSchemaToFlow(schema);
  }, [schema]);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node<TableNodeData>>(initialFlow.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(initialFlow.edges);

  useEffect(() => {
    const flow = mapSchemaToFlow(schema);
    setNodes(flow.nodes);
    setEdges(flow.edges);
  }, [schema, setNodes, setEdges]);

  // Filter nodes if search term entered
  const filteredNodes = useMemo(() => {
    if (!searchTerm.trim()) return nodes;
    const term = searchTerm.toLowerCase();
    return nodes.map((node) => {
      const match =
        node.data.tableName.toLowerCase().includes(term) ||
        node.data.columns.some((c) => c.name.toLowerCase().includes(term));
      return {
        ...node,
        hidden: !match,
      };
    });
  }, [nodes, searchTerm]);

  const resetLayout = useCallback(() => {
    const flow = mapSchemaToFlow(schema);
    setNodes(flow.nodes);
    setEdges(flow.edges);
  }, [schema, setNodes, setEdges]);

  const tableCount = Object.keys(schema?.tables || {}).length;
  const relCount = schema?.relationships?.length || 0;

  if (!schema || tableCount === 0) {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center p-6 text-center text-slate-400">
        <svg
          className="mb-2 h-10 w-10 text-slate-300"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6z" />
          <path d="M9 4v16" />
          <path d="M15 4v16" />
          <path d="M4 10h16" />
          <path d="M4 16h16" />
        </svg>
        <p className="text-sm font-medium text-slate-600">No tables found</p>
        <p className="text-xs text-slate-400 mt-0.5">Database schema is empty or loading.</p>
      </div>
    );
  }

  return (
    <div className={`relative flex flex-col bg-slate-50/50 ${className}`}>
      {/* Top Toolbar */}
      <div className="z-10 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-white/90 px-3.5 py-2 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 font-mono text-[11px] font-medium text-slate-600">
            <span>{tableCount}</span> {tableCount === 1 ? "table" : "tables"}
          </span>
          {relCount > 0 && (
            <span className="flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 font-mono text-[11px] font-medium text-blue-700">
              <span>{relCount}</span> {relCount === 1 ? "relation" : "relations"}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <input
              type="text"
              placeholder="Filter tables/columns…"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-7 w-36 rounded-md border border-slate-200 bg-slate-50 px-2 text-xs text-slate-800 placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none sm:w-48"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm("")}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
              >
                ✕
              </button>
            )}
          </div>
          <button
            onClick={resetLayout}
            title="Reset node positions"
            className="flex h-7 items-center gap-1 rounded-md border border-slate-200 bg-white px-2 text-[11px] font-medium text-slate-600 hover:bg-slate-50"
          >
            <svg
              className="h-3 w-3"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
              <path d="M21 3v5h-5" />
              <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
              <path d="M3 21v-5h5" />
            </svg>
            Auto Layout
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 w-full h-full min-h-[300px]">
        <ReactFlow
          nodes={filteredNodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.2}
          maxZoom={1.5}
          defaultEdgeOptions={{
            type: "smoothstep",
            animated: true,
          }}
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1.2} color="#cbd5e1" />
          <Controls position="bottom-right" showInteractive={false} />
          {showMiniMap && (
            <MiniMap
              position="bottom-left"
              nodeColor="#94a3b8"
              nodeStrokeColor="#475569"
              maskColor="rgba(241, 245, 249, 0.7)"
              className="!border !border-slate-200 !rounded-lg !shadow-sm overflow-hidden"
              zoomable
              pannable
            />
          )}
        </ReactFlow>
      </div>
    </div>
  );
}
