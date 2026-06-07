import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { DimensionRadar } from "../components/DimensionRadar";
import { InsightCard, isWideInsightCard } from "../components/InsightCard";
import { ProfileNarrativeReport } from "../components/ProfileNarrativeReport";
import { fetchProfile } from "../lib/api";

export function ProfilePage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["profile"], queryFn: fetchProfile });

  if (isLoading) return <p className="animate-pulse">Loading profile…</p>;
  if (error) return <EmptyState />;
  if (!data) return null;

  const archetypeCard = data.insight_cards.find((c) => c.id === "archetype");
  const gridCards = data.insight_cards.filter((c) => c.id !== "archetype");

  return (
    <div className="space-y-8">
      <section className="card-brutal bg-cozy-red/10 p-8">
        <p className="text-sm font-semibold text-cozy-red">
          {archetypeCard?.question || "Your archetype"}
        </p>
        <h2 className="font-display mt-2 text-4xl font-bold">
          {archetypeCard?.value || data.archetype}
        </h2>
        <p className="mt-3 text-sm opacity-60">
          {data.session_count} sessions · {data.upload_count} uploads
        </p>
      </section>

      {data.narrative && <ProfileNarrativeReport narrative={data.narrative} />}

      {gridCards.length > 0 && (
        <section>
          <h2 className="font-display mb-4 text-xl font-bold">Your builder map</h2>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {gridCards.map((card) => (
              <InsightCard key={card.id} card={card} wide={isWideInsightCard(card)} />
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="font-display mb-4 text-xl font-bold">Dimensions</h2>
        <DimensionRadar dimensions={data.dimensions} />
      </section>
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
