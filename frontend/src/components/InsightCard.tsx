import type { InsightCard as InsightCardType } from "../lib/api";

const WIDE_CARD_IDS = new Set(["relationship", "crash", "shipped"]);

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
  if (card.id === "relationship" || card.id === "shipped") {
    return <>{card.value}</>;
  }
  if (card.id === "crash" || card.id === "cryptic" || card.id === "goto") {
    return <QuotedText text={card.value} />;
  }
  if (card.subtitle && card.subtitle.length > 120) {
    return <>{wrapWords(card.value, 8)}</>;
  }
  return <>{card.value}</>;
}

export function isWideInsightCard(card: InsightCardType): boolean {
  return WIDE_CARD_IDS.has(card.id) || (card.subtitle?.length ?? 0) > 140;
}

export function InsightCard({
  card,
  wide = false,
}: {
  card: InsightCardType;
  wide?: boolean;
}) {
  const longSubtitle = (card.subtitle?.length ?? 0) > 100;

  return (
    <article
      className={`card-brutal flex h-full flex-col p-5 ${
        wide ? "col-span-full max-w-none" : "min-h-[180px]"
      }`}
    >
      <p className="text-sm font-semibold text-cozy-red">{card.question || card.title}</p>
      <p
        className={`font-display mt-3 font-bold leading-snug ${
          wide || longSubtitle ? "whitespace-pre-line text-lg" : "text-xl"
        }`}
      >
        <CardValue card={card} />
      </p>
      {card.subtitle && (
        <p
          className={`mt-auto pt-3 text-sm leading-relaxed opacity-75 ${
            wide ? "whitespace-pre-line" : ""
          }`}
        >
          {wide && card.id === "relationship" ? wrapWords(card.subtitle, 11) : card.subtitle}
        </p>
      )}
    </article>
  );
}
