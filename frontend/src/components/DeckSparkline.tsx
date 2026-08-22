import { LineChart, Line, ResponsiveContainer } from "recharts";

interface DeckSparklineProps {
  data: number[];
  width?: number;
  height?: number;
}

export function DeckSparkline({ data, width = 100, height = 32 }: DeckSparklineProps) {
  if (data.length === 0) {
    return <div style={{ width, height }} data-testid="sparkline-empty" />;
  }

  const first = data[0];
  const last = data[data.length - 1];
  const color = last > first ? "#22c55e" : last < first ? "#ef4444" : "#94a3b8";

  const chartData = data.map((value, index) => ({ index, value }));

  return (
    <div style={{ width, height }} data-testid="sparkline">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
