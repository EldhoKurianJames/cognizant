import { useState } from "react";

interface Props {
  onSubmit: (question: string) => void;
  loading: boolean;
}

const EXAMPLE_QUESTIONS = [
  "Who are the top 5 customers by spending?",
  "What is the total revenue by month?",
  "List all orders with customer names and amounts",
];

export function QueryForm({ onSubmit, loading }: Props) {
  const [question, setQuestion] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (trimmed && !loading) {
      onSubmit(trimmed);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <label htmlFor="question" className="text-sm font-medium text-neutral-700">
        Ask a question about your data
      </label>
      <div className="flex gap-2">
        <input
          id="question"
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What is the total revenue by month?"
          className="flex-1 rounded-md border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-neutral-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="rounded-md bg-neutral-900 px-5 py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-neutral-300"
        >
          {loading ? "Running…" : "Run"}
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {EXAMPLE_QUESTIONS.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => setQuestion(example)}
            className="rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs text-neutral-600"
          >
            {example}
          </button>
        ))}
      </div>
    </form>
  );
}
