import { type Node, type Edge, MarkerType } from "@xyflow/react";
import type { SchemaColumn, SchemaResponse } from "../api";

export interface TableNodeData {
  tableName: string;
  columns: SchemaColumn[];
  rowCount?: number;
  [key: string]: unknown;
}

export function mapSchemaToFlow(schema: SchemaResponse | null): {
  nodes: Node<TableNodeData>[];
  edges: Edge[];
} {
  if (!schema || !schema.tables) {
    return { nodes: [], edges: [] };
  }

  const tableNames = Object.keys(schema.tables);
  if (tableNames.length === 0) {
    return { nodes: [], edges: [] };
  }

  const relationships = schema.relationships || [];

  // Compute dependency levels for smart horizontal layout
  // Tables with 0 outgoing FKs are placed first (left column)
  const outgoingCount: Record<string, number> = {};
  tableNames.forEach((t) => {
    outgoingCount[t] = 0;
  });

  relationships.forEach((rel) => {
    if (outgoingCount[rel.source_table] !== undefined) {
      outgoingCount[rel.source_table] += 1;
    }
  });

  // Sort tables: independent tables (e.g. customers, products) on the left, dependent tables on the right
  const sortedTables = [...tableNames].sort((a, b) => {
    return (outgoingCount[a] ?? 0) - (outgoingCount[b] ?? 0);
  });

  // Calculate grid coordinates
  const columnsCount = Math.max(1, Math.min(3, Math.ceil(Math.sqrt(sortedTables.length))));
  const colWidth = 320;
  const rowHeight = 320;

  const nodes: Node<TableNodeData>[] = sortedTables.map((tableName, index) => {
    const colIndex = index % columnsCount;
    const rowIndex = Math.floor(index / columnsCount);

    const x = colIndex * colWidth + 40;
    const y = rowIndex * rowHeight + 40;

    return {
      id: tableName,
      type: "tableNode",
      position: { x, y },
      data: {
        tableName,
        columns: schema.tables[tableName] || [],
      },
    };
  });

  const edges: Edge[] = relationships.map((rel, idx) => {
    const edgeId = rel.id || `edge-${rel.source_table}-${rel.source_column}-${rel.target_table}-${rel.target_column}-${idx}`;
    return {
      id: edgeId,
      source: rel.source_table,
      target: rel.target_table,
      sourceHandle: `${rel.source_table}-${rel.source_column}-source`,
      targetHandle: `${rel.target_table}-${rel.target_column}-target`,
      type: "smoothstep",
      animated: true,
      style: {
        stroke: "#3b82f6",
        strokeWidth: 2,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 14,
        height: 14,
        color: "#3b82f6",
      },
      label: `${rel.source_column} → ${rel.target_column}`,
      labelStyle: {
        fontSize: 10,
        fontWeight: 600,
        fill: "#475569",
      },
      labelBgStyle: {
        fill: "#ffffff",
        fillOpacity: 0.95,
        stroke: "#cbd5e1",
        strokeWidth: 1,
        rx: 4,
        ry: 4,
      },
      labelBgPadding: [6, 2],
    };
  });

  return { nodes, edges };
}
