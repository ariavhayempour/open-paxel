import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { EditableSessionTitle } from "../components/EditableSessionTitle";
import { fetchSessions } from "../lib/api";

export function SessionsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["sessions"], queryFn: () => fetchSessions() });

  if (isLoading) return <p className="animate-pulse">Loading sessions…</p>;

  const items = data?.items ?? [];

  return (
    <div className="space-y-4">
      <h2 className="font-display text-2xl font-bold">Sessions</h2>
      {items.length === 0 ? (
        <p className="opacity-70">No analyzed sessions yet.</p>
      ) : (
        <ul className="space-y-3">
          {items.map((s) => (
            <li key={s.session_id}>
              <Link
                to={`/sessions/${s.session_id}`}
                className="card-brutal block p-4 transition hover:bg-warm-yellow/20"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <EditableSessionTitle sessionId={s.session_id} title={s.title} />
                    <p className="text-sm opacity-60">{s.project_path}</p>
                  </div>
                  <span className="btn-brutal bg-cream-dark px-2 py-1 text-xs">{s.archetype}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {Object.entries(s.dimensions).map(([d, score]) => (
                    <span key={d} className="text-xs font-medium">
                      {d}: <strong>{score}</strong>
                    </span>
                  ))}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
