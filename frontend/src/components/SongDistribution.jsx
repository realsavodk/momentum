// Donut chart: share of activity across the artist's top tracks (latest snapshot).

import { Doughnut } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
} from "chart.js";

ChartJS.register(ArcElement, Tooltip);

const PALETTE = ["#1db954", "#378add", "#d4537e", "#ba7517", "#7f77dd", "#1d9e75",
  "#e24b4a", "#888780"];

export default function SongDistribution({ topTracks }) {
  if (!topTracks?.length) return null;

  const tracks = topTracks.slice(0, 8);
  const data = {
    labels: tracks.map((t) => t.name),
    datasets: [
      {
        data: tracks.map((t) => t.popularity),
        backgroundColor: tracks.map((_, i) => PALETTE[i % PALETTE.length]),
        borderColor: "#ffffff",
        borderWidth: 2,
      },
    ],
  };
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: "62%",
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const total = ctx.dataset.data.reduce((s, v) => s + v, 0);
            return ` ${Math.round((ctx.raw / total) * 100)}% share`;
          },
        },
      },
    },
  };

  return (
    <div className="card">
      <h2>Song distribution</h2>
      <p className="desc">Share of activity across top tracks</p>
      <div style={{ position: "relative", height: 220 }}>
        <Doughnut data={data} options={options} />
      </div>
    </div>
  );
}
