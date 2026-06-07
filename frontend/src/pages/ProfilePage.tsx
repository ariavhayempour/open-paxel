import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { DimensionRadar } from "../components/DimensionRadar";
import { InsightCard } from "../components/InsightCard";
import { fetchProfile } from "../lib/api";

export function ProfilePage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["profile"], queryFn: fetchProfile });

  if (isLoading) return <p className="animate-pulse">Loading profile…</p>;
  if (error) return <EmptyState />;
  if (!data) return null;

  const scrollCards = data.insight_cards.filter(
    (c) => c.id !== "relationship" && c.id !== "prompts",
  );
  const relationshipCard = data.insight_cards.find((c) => c.id === "relationship");

  return (
    <div className="space-y-8">
      <section className="card-brutal bg-cozy-red/10 p-8">
        <p className="text-sm font-semibold uppercase text-cozy-red">Your archetype</p>
        <h2 className="font-display mt-2 text-4xl font-bold">{data.archetype}</h2>
        <p className="mt-2 opacity-70">
          {data.session_count} sessions · {data.upload_count} uploads
        </p>
      </section>

      <section>
        <h2 className="font-display mb-4 text-xl font-bold">Insight cards</h2>
        <div className="flex flex-wrap gap-4 pb-2">
          {scrollCards.map((card) => (
            <InsightCard key={card.id} card={card} />
          ))}
        </div>
        {relationshipCard && (
          <div className="mt-4">
            <InsightCard card={relationshipCard} wide />
          </div>
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <DimensionRadar dimensions={data.dimensions} />

        <section className="space-y-4">
          <div className="card-brutal p-5">
            <h2 className="font-display text-lg font-bold">Signature moves</h2>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
              {data.signature_moves.length ? (
                data.signature_moves.map((m) => <li key={m}>{m}</li>)
              ) : (
                <li className="list-none pl-0 opacity-60">Analyze more sessions to discover patterns</li>
              )}
            </ul>
          </div>
          <div className="card-brutal border-subdued-blue bg-subdued-blue/5 p-5">
            <h2 className="font-display text-lg font-bold">Growth edge</h2>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
              {data.growth_edge.length ? (
                data.growth_edge.map((g) => <li key={g}>{g}</li>)
              ) : (
                <li className="list-none pl-0 opacity-60">Run upload to get personalized tips</li>
              )}
            </ul>
          </div>
        </section>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="space-y-6">
      <div className="card-brutal max-w-lg p-8">
        <h2 className="font-display text-xl font-bold">No profile yet</h2>
        <p className="mt-2 opacity-70">
          Upload Claude Code session files on the{" "}
          <Link to="/uploads" className="font-semibold underline">
            Uploads
          </Link>{" "}
          page, or run{" "}
          <code className="rounded bg-cream-dark px-1">brain-dump upload</code> in your terminal.
        </p>
      </div>
    </div>
  );
}
