import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";

const LABELS: Record<string, string> = {
  steering: "Steering",
  execution: "Execution",
  engineering: "Engineering",
  product_instinct: "Product",
  planning: "Planning",
};

export function DimensionRadar({ dimensions }: { dimensions: Record<string, number> }) {
  const data = Object.entries(dimensions).map(([key, value]) => ({
    dimension: LABELS[key] ?? key,
    score: value,
  }));

  if (!data.length) {
    return (
      <div className="card-brutal flex h-72 items-center justify-center p-6 text-sm opacity-60">
        No dimension data yet
      </div>
    );
  }

  return (
    <div className="card-brutal p-4">
      <h2 className="font-display mb-2 text-lg font-bold">Five dimensions</h2>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data}>
          <PolarGrid stroke="#1a1612" strokeOpacity={0.2} />
          <PolarAngleAxis dataKey="dimension" tick={{ fill: "#1a1612", fontSize: 12 }} />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />
          <Radar
            name="Score"
            dataKey="score"
            stroke="#c45c5c"
            fill="#c45c5c"
            fillOpacity={0.35}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
