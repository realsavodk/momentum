// Monthly volume bar chart. Each bar = total popularity across tracks for that period,
// colored by the top song that period.

import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

const PALETTE = ["#1db954", "#378add", "#d4537e", "#ba7517", "#7f77dd", "#1d9e75"];

function shortDate(yearMonth) {
  const [year, month] = yearMonth.split("-");
  const d = new Date(Number(year), Number(month) - 1, 1);
  const mon = d.toLocaleDateString(undefined, { month: "short" });
  const yr = String(year).slice(-2);
  return `${mon} '${yr}`;
}

function formatPlays(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return `${n}`;
}

export default function MonthlyChart({ history }) {
  if (!history || !history.periods?.length) {
    return (
      <div className="card">
        <h2>Monthly new plays</h2>
        <p className="desc">
          No history yet. Snapshots accumulate each time you view this artist — or hit
          "seed demo data" to backfill.
        </p>
      </div>
    );
  }

  const { periods, series, monthly_new_plays } = history;

  // fall back to avg popularity bars if playcount data isn't available yet
  const hasPlaycounts = monthly_new_plays?.some(v => v > 0);

  const barValues = hasPlaycounts
    ? monthly_new_plays
    : periods.map((_, i) => {
        const vals = series.map(s => s.data[i]).filter(v => v != null && v > 0);
        return vals.length ? Math.round(vals.reduce((s, v) => s + v, 0) / vals.length) : 0;
      });

  const topIdxPerPeriod = periods.map((_, i) => {
    let best = -1, idx = 0;
    series.forEach((s, si) => {
      if ((s.data[i] || 0) > best) { best = s.data[i] || 0; idx = si; }
    });
    return idx;
  });
  const barColors = topIdxPerPeriod.map((idx) => PALETTE[idx % PALETTE.length]);

  const nonZero = barValues.filter(v => v > 0);
  const yMin = nonZero.length ? Math.max(0, Math.min(...nonZero) * 0.85) : 0;

  const data = {
    labels: periods.map(shortDate),
    datasets: [{
      label: hasPlaycounts ? "New plays" : "Avg. popularity",
      data: barValues,
      backgroundColor: barColors,
      borderRadius: 6,
    }],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => hasPlaycounts
            ? ` ${formatPlays(ctx.raw)} new plays`
            : ` Avg. popularity: ${ctx.raw} / 100`,
          afterBody: (items) => {
            const i = items[0].dataIndex;
            const topTrack = series[topIdxPerPeriod[i]];
            return `Top track: ${topTrack?.name ?? "—"}`;
          },
        },
      },
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: "#6e6e73" } },
      y: {
        min: yMin,
        grid: { color: "rgba(0,0,0,0.07)" },
        ticks: {
          color: "#6e6e73",
          callback: (v) => hasPlaycounts ? formatPlays(v) : v,
        },
        title: {
          display: true,
          text: hasPlaycounts ? "New Last.fm plays" : "Avg. popularity (0–100)",
          color: "#6e6e73",
          font: { size: 11 },
        },
      },
    },
  };

  return (
    <div className="card">
      <h2>Monthly new plays</h2>
      <p className="desc">
        {hasPlaycounts
          ? "New Last.fm scrobbles per month. Bar color = top track that period."
          : "Average popularity across tracked songs. Seed more history for real play counts."}
      </p>
      <div style={{ position: "relative", height: 260 }}>
        <Bar data={data} options={options} />
      </div>
    </div>
  );
}
