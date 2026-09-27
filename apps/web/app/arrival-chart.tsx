"use client";

/**
 * Appeals over time, drawn from the buckets the API returns.
 *
 * No charting library. The shape is a polyline over a handful of points, which
 * is a few lines of arithmetic, and a dependency would bring a bundle larger
 * than the rest of this screen.
 *
 * The chart states how many records it left out. A count restricted to
 * trustworthy business times, presented without saying so, invites a reader to
 * believe it covers everything.
 */

export type Bucket = {
  start: string;
  count: number;
  by_topic: Record<string, number>;
};

const WIDTH = 720;
const HEIGHT = 180;
const PAD_X = 34;
const PAD_Y = 16;

export function ArrivalChart({
  buckets,
  baseline,
  peakStart,
  excluded,
  excludedLabel,
  emptyLabel,
}: {
  buckets: Bucket[];
  baseline: number | null;
  peakStart: string | null;
  excluded: number;
  excludedLabel: string;
  emptyLabel: string;
}) {
  if (buckets.length < 2) {
    return <p className="war-room-note">{emptyLabel}</p>;
  }

  const peak = Math.max(...buckets.map((bucket) => bucket.count), 1);
  const stepX = (WIDTH - PAD_X * 2) / (buckets.length - 1);
  const y = (value: number) =>
    HEIGHT - PAD_Y - (value / peak) * (HEIGHT - PAD_Y * 2);

  const points = buckets
    .map((bucket, index) => `${PAD_X + index * stepX},${y(bucket.count)}`)
    .join(" ");
  const area = `${PAD_X},${HEIGHT - PAD_Y} ${points} ${PAD_X + (buckets.length - 1) * stepX},${HEIGHT - PAD_Y}`;

  return (
    <figure className="arrival-chart">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label="Appeals over time"
      >
        <polygon points={area} className="arrival-area" />
        <polyline points={points} className="arrival-line" />
        {baseline !== null ? (
          <line
            x1={PAD_X}
            x2={WIDTH - PAD_X}
            y1={y(baseline)}
            y2={y(baseline)}
            className="arrival-baseline"
          />
        ) : null}
        {buckets.map((bucket, index) => {
          const isPeak = bucket.start === peakStart;
          return (
            <circle
              key={bucket.start}
              cx={PAD_X + index * stepX}
              cy={y(bucket.count)}
              r={isPeak ? 5 : 3}
              className={
                isPeak ? "arrival-point arrival-peak" : "arrival-point"
              }
            >
              <title>
                {`${bucket.start.slice(11, 16)} · ${bucket.count}\n` +
                  Object.entries(bucket.by_topic)
                    .sort((left, right) => right[1] - left[1])
                    .map(([topic, count]) => `${topic}: ${count}`)
                    .join("\n")}
              </title>
            </circle>
          );
        })}
        <text x={PAD_X} y={HEIGHT - 2} className="arrival-axis">
          {buckets[0].start.slice(11, 16)}
        </text>
        <text
          x={WIDTH - PAD_X}
          y={HEIGHT - 2}
          textAnchor="end"
          className="arrival-axis"
        >
          {buckets[buckets.length - 1].start.slice(11, 16)}
        </text>
        <text x={PAD_X} y={PAD_Y} className="arrival-axis">
          {peak}
        </text>
      </svg>
      {excluded > 0 ? (
        <figcaption className="codes">
          {excludedLabel}: {excluded}
        </figcaption>
      ) : null}
    </figure>
  );
}
