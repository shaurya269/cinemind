export default function SkeletonCard() {
  return (
    <div className="rec-card skeleton-card" aria-hidden="true">
      <div className="rec-card-body">
        <div className="skeleton skeleton-poster" />
        <div className="rec-card-content">
          <div className="skeleton skeleton-line" style={{ width: "70%", height: 18 }} />
          <div className="skeleton skeleton-line" style={{ width: "40%" }} />
          <div className="skeleton skeleton-line" style={{ width: "95%" }} />
          <div className="skeleton skeleton-line" style={{ width: "85%" }} />
        </div>
      </div>
    </div>
  );
}

export function SkeletonGrid({ count = 6 }) {
  return (
    <div className="rec-grid">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
