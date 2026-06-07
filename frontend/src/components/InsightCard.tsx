import type { InsightCard as InsightCardType } from "../lib/api";

const QUOTED_CARD_IDS = new Set(["goto", "cryptic", "crash"]);

function wrapWords(text: string, wordsPerLine = 11): string {
  const words = text.trim().split(/\s+/).filter(Boolean);
  if (words.length <= wordsPerLine) return text.trim();

  const lines: string[] = [];
  for (let i = 0; i < words.length; i += wordsPerLine) {
    lines.push(words.slice(i, i + wordsPerLine).join(" "));
  }
  return lines.join("\n");
}

function stripWrappingQuotes(text: string): string {
  return text.replace(/^[\s"'“”]+|[\s"'“”]+$/g, "").trim();
}

function QuotedText({ text }: { text: string }) {
  const bare = stripWrappingQuotes(text);
  return (
    <>
      <span className="font-serif">{"\u201C"}</span>
      {bare}
      <span className="font-serif">{"\u201D"}</span>
    </>
  );
}

function CardValue({ card }: { card: InsightCardType }) {
  if (card.id === "relationship") {
    return <>{wrapWords(card.value, 11)}</>;
  }
  if (QUOTED_CARD_IDS.has(card.id)) {
    return <QuotedText text={card.value} />;
  }
  return <>{card.value}</>;
}

export function InsightCard({
  card,
  wide = false,
}: {
  card: InsightCardType;
  wide?: boolean;
}) {
  return (
    <article
      className={`card-brutal p-5 ${
        wide ? "w-full max-w-2xl" : "min-w-[240px] max-w-[280px] flex-shrink-0"
      }`}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-subdued-blue">{card.title}</p>
      <p
        className={`font-display mt-2 font-bold leading-snug ${
          wide ? "whitespace-pre-line text-base" : "text-xl leading-tight"
        }`}
      >
        <CardValue card={card} />
      </p>
      {card.subtitle && <p className="mt-2 text-sm opacity-70">{card.subtitle}</p>}
    </article>
  );
}
