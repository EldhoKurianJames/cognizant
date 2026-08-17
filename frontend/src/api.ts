export interface QueryResponse {
  question: string;
  sql: string;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  source: "template" | "llm";
}

export interface SchemaColumn {
  name: string;
  type: string;
}

export interface SchemaResponse {
  tables: Record<string, SchemaColumn[]>;
}

const BASE_URL = "/api";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore parse errors, fall back to statusText
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function fetchSchema(): Promise<SchemaResponse> {
  const res = await fetch(`${BASE_URL}/schema`);
  return handleResponse<SchemaResponse>(res);
}

export async function runQuery(question: string): Promise<QueryResponse> {
  const res = await fetch(`${BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return handleResponse<QueryResponse>(res);
}
