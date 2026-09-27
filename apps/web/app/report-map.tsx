"use client";

/**
 * A map of where reports fall, drawn from the points themselves.
 *
 * There is no tile layer and no mapping library on purpose. The operator needs
 * to see the shape and spread of a set of reports, which the points alone carry,
 * and a tile request would send the location of citizen reports to a third party
 * every time someone opened an incident.
 *
 * The projection is equirectangular with a cosine correction on longitude, which
 * is accurate enough over the few kilometres an incident covers and keeps the
 * component free of dependencies.
 */

export type ReportPoint = {
  longitude: number;
  latitude: number;
  label?: string;
  kind?: "confirmed" | "candidate";
};

const WIDTH = 480;
const HEIGHT = 300;
const PADDING = 28;
// The scale bar gets a band of its own at the bottom. Drawing it over the plot
// put the label on top of a report and made a dense cluster unreadable.
const SCALE_BAND = 26;

function metresPerDegreeLongitude(latitude: number): number {
  return 111_320 * Math.cos((latitude * Math.PI) / 180);
}

export function ReportMap({
  points,
  centroid,
  spreadMetres,
  emptyLabel,
}: {
  points: ReportPoint[];
  centroid?: { longitude: number; latitude: number } | null;
  spreadMetres?: number | null;
  emptyLabel: string;
}) {
  if (points.length === 0) {
    return (
      <div
        className="report-map report-map-empty"
        role="img"
        aria-label={emptyLabel}
      >
        <p>{emptyLabel}</p>
      </div>
    );
  }

  const longitudes = points.map((point) => point.longitude);
  const latitudes = points.map((point) => point.latitude);
  const minLon = Math.min(...longitudes);
  const maxLon = Math.max(...longitudes);
  const minLat = Math.min(...latitudes);
  const maxLat = Math.max(...latitudes);

  // A single point, or a perfectly straight line of them, would divide by zero.
  // Widening the span keeps the drawing sane and honest about how little spread
  // there is, rather than stretching one point across the whole canvas.
  const lonSpan = Math.max(maxLon - minLon, 0.0008);
  const latSpan = Math.max(maxLat - minLat, 0.0008);
  const midLat = (minLat + maxLat) / 2;

  const project = (point: { longitude: number; latitude: number }) => ({
    x:
      PADDING +
      ((point.longitude - minLon + (lonSpan - (maxLon - minLon)) / 2) /
        lonSpan) *
        (WIDTH - PADDING * 2),
    // Screen y grows downward while latitude grows upward.
    y:
      HEIGHT -
      PADDING -
      ((point.latitude - minLat + (latSpan - (maxLat - minLat)) / 2) /
        latSpan) *
        (HEIGHT - PADDING * 2),
  });

  const widthMetres = lonSpan * metresPerDegreeLongitude(midLat);
  const scaleMetres = niceScale(widthMetres / 3);
  const scalePixels = (scaleMetres / widthMetres) * (WIDTH - PADDING * 2);

  return (
    <figure className="report-map">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`${points.length} reports`}
        preserveAspectRatio="xMidYMid meet"
      >
        <rect
          x="0"
          y="0"
          width={WIDTH}
          height={HEIGHT}
          className="report-map-bg"
        />
        {centroid
          ? (() => {
              const middle = project(centroid);
              const radiusPixels =
                spreadMetres && widthMetres > 0
                  ? (spreadMetres / widthMetres) * (WIDTH - PADDING * 2)
                  : 0;
              // A spread wider than the plot would draw a circle nobody can
              // see the edge of, so it is clamped and the figure states the
              // number instead of implying it from the drawing.
              const drawn = Math.min(radiusPixels, (WIDTH - PADDING * 2) / 2);
              return drawn > 2 ? (
                <circle
                  cx={middle.x}
                  cy={middle.y}
                  r={drawn}
                  className="report-map-spread"
                />
              ) : null;
            })()
          : null}
        {points.map((point, index) => {
          const position = project(point);
          return (
            <circle
              key={`${point.longitude}-${point.latitude}-${index}`}
              cx={position.x}
              cy={position.y}
              r={7}
              className={
                point.kind === "candidate"
                  ? "report-map-point report-map-point-candidate"
                  : "report-map-point"
              }
            >
              {point.label ? <title>{point.label}</title> : null}
            </circle>
          );
        })}
        <g className="report-map-scale">
          <line
            x1={PADDING}
            y1={HEIGHT - 10}
            x2={PADDING + scalePixels}
            y2={HEIGHT - 10}
          />
          <text x={PADDING} y={HEIGHT - 16}>
            {scaleMetres >= 1000
              ? `${(scaleMetres / 1000).toFixed(1)} km`
              : `${Math.round(scaleMetres)} m`}
          </text>
        </g>
      </svg>
    </figure>
  );
}

function niceScale(metres: number): number {
  const steps = [50, 100, 200, 500, 1000, 2000, 5000, 10000];
  for (const step of steps) {
    if (metres <= step) return step;
  }
  return steps[steps.length - 1];
}
