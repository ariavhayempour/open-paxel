import type { ProfileNarrative } from "../lib/api";

function NarrativeBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card-brutal p-6">
      <h2 className="font-display text-lg font-bold">{title}</h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed opacity-90">{children}</div>
    </section>
  );
}

export function ProfileNarrativeReport({ narrative }: { narrative: ProfileNarrative }) {
  return (
    <div className="space-y-4">
      <NarrativeBlock title="Your narrative">
        <p>{narrative.narrative}</p>
      </NarrativeBlock>

      <NarrativeBlock title="What You Built">
        <p>{narrative.what_you_built}</p>
      </NarrativeBlock>

      <NarrativeBlock title="Decision Patterns">
        <p>{narrative.decision_patterns}</p>
        {narrative.matched_pattern && (
          <div className="border-l-4 border-cozy-red bg-cream-dark/40 py-2 pl-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-cozy-red">
              {narrative.matched_pattern_category || "Matched pattern"}
            </p>
            <p className="mt-1 font-display font-bold">{narrative.matched_pattern}</p>
          </div>
        )}
      </NarrativeBlock>

      {narrative.strengths.length > 0 && (
        <NarrativeBlock title="Strengths">
          <ul className="list-disc space-y-2 pl-5">
            {narrative.strengths.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </NarrativeBlock>
      )}

      {narrative.growth_areas.length > 0 && (
        <NarrativeBlock title="Growth Areas">
          <ul className="list-disc space-y-2 pl-5">
            {narrative.growth_areas.map((g) => (
              <li key={g}>{g}</li>
            ))}
          </ul>
        </NarrativeBlock>
      )}
    </div>
  );
}
