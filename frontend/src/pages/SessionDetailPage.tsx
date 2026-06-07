import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { EditableSessionTitle } from "../components/EditableSessionTitle";
import { fetchSession } from "../lib/api";

export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, error } = useQuery({
    queryKey: ["session", id],
    queryFn: () => fetchSession(id!),
    enabled: !!id,
  });

  if (isLoading) return <p className="animate-pulse">Loading…</p>;
  if (error || !data) return <p>Session not found.</p>;

  return (
    <div className="space-y-6">
      <Link to="/sessions" className="text-sm font-semibold text-subdued-blue hover:underline">
        ← Back to sessions
      </Link>
      <header className="card-brutal p-6">
        <p className="text-sm uppercase text-cozy-red">{data.archetype}</p>
        <EditableSessionTitle
          sessionId={data.session_id}
          title={data.title}
          className="font-display text-3xl font-bold"
        />
        <p className="mt-1 text-sm opacity-60">{data.project_path}</p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        {Object.entries(data.dimensions).map(([dim, score]) => (
          <article key={dim} className="card-brutal p-5">
            <div className="flex items-baseline justify-between">
              <h3 className="font-display font-bold capitalize">{dim.replace("_", " ")}</h3>
              <span className="text-2xl font-bold text-cozy-red">{score.score}</span>
            </div>
            <p className="mt-2 text-sm leading-relaxed">{score.narrative}</p>
            {score.evidence.length > 0 && (
              <ul className="mt-3 space-y-1 border-t-2 border-ink/10 pt-3 text-xs opacity-80">
                {score.evidence.map((e, i) => (
                  <li key={i} className="italic">"{e}"</li>
                ))}
              </ul>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
