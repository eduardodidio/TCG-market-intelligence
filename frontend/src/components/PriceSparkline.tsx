import { LineChart, Line, ResponsiveContainer } from "recharts";

interface PriceSparklineProps {
  prices: number[];
  width?: number;
  height?: number;
}

/**
 * Mini sparkline chart showing 7-day price trend.
 * Green if prices went up, red if down, gray if flat or insufficient data.
 */
export function PriceSparkline({ prices, width = 60, height = 24 }: PriceSparklineProps) {
  if (prices.length < 2) {
    return <div style={{ width, height }} data-testid="price-sparkline-empty" />;
  }

  const first = prices[0];
  const last = prices[prices.length - 1];
  const color = last > first ? "#22c55e" : last < first ? "#ef4444" : "#94a3b8";

  const chartData = prices.map((value, index) => ({ index, value }));

  return (
    <div style={{ width, height }} data-testid="price-sparkline">
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
