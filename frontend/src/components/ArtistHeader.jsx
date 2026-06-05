// Artist profile header: image/avatar, name, genres, follower count.

function formatFollowers(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return `${n}`;
}

export default function ArtistHeader({ artist }) {
  if (!artist) return null;
  const initial = artist.name?.[0]?.toUpperCase() || "?";
  return (
    <div className="artist-header">
      {artist.image ? (
        <img src={artist.image} alt={artist.name} />
      ) : (
        <div className="artist-avatar">{initial}</div>
      )}
      <div>
        <h1>{artist.name}</h1>
        <div className="sub">
          {(artist.genres || []).slice(0, 2).join(" · ") || "—"} ·{" "}
          {formatFollowers(artist.followers)} followers · popularity{" "}
          {artist.popularity}/100
        </div>
      </div>
    </div>
  );
}
