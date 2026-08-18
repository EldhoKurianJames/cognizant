import { useEffect, useState } from "react";
import { fetchSchema, runQuery, type QueryResponse, type SchemaResponse } from "./api";
import { SchemaPanel } from "./components/SchemaPanel";
import { QueryForm } from "./components/QueryForm";
import { ResultsTable } from "./components/ResultsTable";
import { CacheAnalytics } from "./components/CacheAnalytics";
import { DatabaseSelector } from "./components/DatabaseSelector";

interface ActiveConnection {
  connectionId: string;
  filename: string;
}

function App() {
  const [schema, setSchema] = useState<SchemaResponse | null>(null);
  const [schemaLoading, setSchemaLoading] = useState(true);
  const [schemaError, setSchemaError] = useState<string | null>(null);

  const [result, setResult] = useState<QueryResponse | null>(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"query" | "cache">("query");

  // null = using the default configured DATABASE_URL database.
  const [activeConnection, setActiveConnection] = useState<ActiveConnection | null>(null);

  function loadSchema(connectionId: string | null) {
    setSchemaLoading(true);
    setSchemaError(null);
    fetchSchema(connectionId)
      .then(setSchema)
      .catch((err: Error) => setSchemaError(err.message))
      .finally(() => setSchemaLoading(false));
  }

  useEffect(() => {
    loadSchema(activeConnection?.connectionId ?? null);
    // Switching databases invalidates any results shown from the previous one.
    setResult(null);
  }, [activeConnection]);

  async function handleSubmit(question: string) {
    setQueryLoading(true);
    setQueryError(null);
    setLastQuestion(question);
    try {
      const response = await runQuery(question, activeConnection?.connectionId ?? null);
      setResult(response);
    } catch (err) {
      setResult(null);
      setQueryError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setQueryLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen bg-neutral-50">
      <aside className="w-72 shrink-0 border-r border-neutral-200 bg-white">
        <DatabaseSelector
          activeConnection={activeConnection}
          onUploaded={setActiveConnection}
          onReset={() => setActiveConnection(null)}
        />
        <SchemaPanel schema={schema} loading={schemaLoading} error={schemaError} bare />
      </aside>

      <main className="flex-1">
        <header className="border-b border-neutral-200 bg-white px-8 py-5">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold text-neutral-900">Analytics Query Assistant</h1>
              <p className="mt-0.5 text-sm text-neutral-500">
                Ask questions about your data in plain English. Only read-only queries are executed.
              </p>
            </div>
            <div className="flex gap-1 rounded-md border border-neutral-200 bg-neutral-50 p-1">
              <button
                onClick={() => setActiveTab("query")}
                className={
                  "rounded-md px-3 py-1.5 text-xs font-medium " +
                  (activeTab === "query" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500")
                }
              >
                Query
              </button>
              <button
                onClick={() => setActiveTab("cache")}
                className={
                  "rounded-md px-3 py-1.5 text-xs font-medium " +
                  (activeTab === "cache" ? "bg-white shadow-sm text-neutral-900" : "text-neutral-500")
                }
              >
                Cache Analytics
              </button>
            </div>
          </div>
        </header>

        <div className="mx-auto flex max-w-4xl flex-col gap-6 px-8 py-8">
          {activeTab === "query" ? (
            <>
              <QueryForm onSubmit={handleSubmit} loading={queryLoading} />

              {queryError && (
                <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  <p className="font-medium">Couldn't answer that question</p>
                  <p className="mt-0.5 text-red-600">{queryError}</p>
                </div>
              )}

              {queryLoading && (
                <p className="text-sm text-neutral-500">
                  Generating SQL for "{lastQuestion}"…
                </p>
              )}

              {result && !queryLoading && <ResultsTable result={result} />}
            </>
          ) : (
            <CacheAnalytics />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
