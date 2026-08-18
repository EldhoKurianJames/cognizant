import { useRef, useState } from "react";
import { uploadDatabase, removeUploadedDatabase } from "../api";

interface Props {
  activeConnection: { connectionId: string; filename: string } | null;
  onUploaded: (connection: { connectionId: string; filename: string }) => void;
  onReset: () => void;
}

export function DatabaseSelector({ activeConnection, onUploaded, onReset }: Props) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    try {
      const { connection_id, filename } = await uploadDatabase(file);
      onUploaded({ connectionId: connection_id, filename });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleReset() {
    if (activeConnection) {
      await removeUploadedDatabase(activeConnection.connectionId).catch(() => {
        // best-effort cleanup; the connection will just go unused server-side
      });
    }
    onReset();
  }

  return (
    <div className="border-b border-neutral-200 px-5 py-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        Active Database
      </p>

      {activeConnection ? (
        <div className="flex items-center justify-between gap-2 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2">
          <div className="truncate">
            <p className="truncate text-xs font-medium text-indigo-800">{activeConnection.filename}</p>
            <p className="text-[11px] text-indigo-500">Uploaded database</p>
          </div>
          <button
            onClick={handleReset}
            className="shrink-0 rounded-md border border-indigo-300 bg-white px-2 py-1 text-[11px] font-medium text-indigo-700"
          >
            Use default
          </button>
        </div>
      ) : (
        <div className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2">
          <p className="text-xs font-medium text-neutral-700">Configured database (DATABASE_URL)</p>
        </div>
      )}

      <label className="mt-2 block">
        <span className="mb-1 block text-[11px] text-neutral-500">
          Or upload your own SQLite (.db) file to query instead
        </span>
        <input
          ref={fileInputRef}
          type="file"
          accept=".db,.sqlite,.sqlite3"
          onChange={handleFileChange}
          disabled={uploading}
          className="block w-full text-xs text-neutral-600 file:mr-2 file:rounded-md file:border file:border-neutral-300 file:bg-white file:px-2 file:py-1 file:text-xs file:font-medium file:text-neutral-700"
        />
      </label>

      {uploading && <p className="mt-1 text-[11px] text-neutral-400">Uploading…</p>}
      {error && <p className="mt-1 text-[11px] text-red-600">{error}</p>}
    </div>
  );
}
