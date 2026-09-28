import { useId } from "react";
import type { ChartSpec, Locale } from "./ask-pulse-types";
import styles from "./ask-pulse.module.css";

const WIDTH = 760;
const HEIGHT = 240;
const LEFT = 48;
const RIGHT = 24;
const TOP = 20;
const BOTTOM = 42;

function label(value: unknown, locale: Locale) {
  if (typeof value !== "string") return String(value ?? "—");
  const date = /^\d{4}-\d{2}-\d{2}/.test(value) ? new Date(value) : null;
  return date && Number.isFinite(date.getTime())
    ? date.toLocaleDateString(`${locale}-KZ`, {
        timeZone: "Asia/Qyzylorda",
        month: "2-digit",
        day: "2-digit",
      })
    : value;
}

/** Render only the rows and columns selected by the governed backend. */
export function AnalyticsChart({
  spec,
  locale,
}: {
  spec: ChartSpec;
  locale: Locale;
}) {
  const titleId = useId();
  const xIndex = spec.columns.findIndex((column) => column.name === spec.x);
  const yIndex = spec.columns.findIndex((column) => column.name === spec.y);
  const seriesIndex = spec.columns.findIndex(
    (column) => column.name === spec.series,
  );
  const lowerIndex = spec.columns.findIndex(
    (column) => column.name === "lower_bound",
  );
  const upperIndex = spec.columns.findIndex(
    (column) => column.name === "upper_bound",
  );
  const observedIndex = spec.columns.findIndex(
    (column) => column.name === "observed",
  );
  const baselineIndex = spec.columns.findIndex(
    (column) => column.name === "baseline",
  );
  const numeric = (cell: unknown): cell is number =>
    typeof cell === "number" && Number.isFinite(cell);
  const rows = spec.rows.filter(
    (row) => typeof row[yIndex] === "number" && Number.isFinite(row[yIndex]),
  );
  if (spec.type === "kpi") return null;
  if (xIndex < 0 || yIndex < 0 || rows.length === 0) {
    return (
      <p className={styles.note}>
        {locale === "ru" ? "Для графика нет данных." : "График үшін дерек жоқ."}
      </p>
    );
  }
  const title =
    locale === "ru"
      ? "Результат аналитического запроса"
      : "Аналитикалық сұрау нәтижесі";
  const valueLabel = (value: number) =>
    `${value.toLocaleString(`${locale}-KZ`, { maximumFractionDigits: 1 })}${spec.y === "change_pct" ? "%" : ""}`;
  const plotValues = spec.rows
    .flatMap((row) => [
      row[yIndex],
      ...(spec.type === "forecast"
        ? [row[lowerIndex], row[upperIndex], row[observedIndex]]
        : spec.type === "surge"
          ? [row[baselineIndex]]
          : []),
    ])
    .filter(numeric);
  const maximum = Math.max(...plotValues, 1);
  const minimum = Math.min(...plotValues, 0);
  const span = maximum - minimum || 1;
  const y = (value: number) =>
    TOP + ((maximum - value) / span) * (HEIGHT - TOP - BOTTOM);
  const isBar =
    spec.type === "bar" ||
    spec.type === "ranked_edges" ||
    spec.type === "surge";
  const categories = [...new Set(spec.rows.map((row) => String(row[xIndex])))];
  const series =
    seriesIndex < 0
      ? [""]
      : [...new Set(rows.map((row) => String(row[seriesIndex] ?? "")))];
  const x = (value: unknown) =>
    LEFT +
    (categories.indexOf(String(value)) / Math.max(categories.length - 1, 1)) *
      (WIDTH - LEFT - RIGHT);
  const lastObservedCategoryIndex =
    spec.type === "forecast" && observedIndex >= 0
      ? categories.reduce(
          (lastIndex, category, index) =>
            spec.rows.some(
              (row) =>
                String(row[xIndex]) === category && numeric(row[observedIndex]),
            )
              ? index
              : lastIndex,
          -1,
        )
      : -1;
  const forecastSplitX =
    lastObservedCategoryIndex >= 0 &&
    lastObservedCategoryIndex < categories.length - 1
      ? (x(categories[lastObservedCategoryIndex]) +
          x(categories[lastObservedCategoryIndex + 1])) /
        2
      : null;
  const barHeight = Math.max(160, rows.length * 34 + 20);

  return (
    <figure className={styles.chart}>
      <svg
        viewBox={`0 0 ${WIDTH} ${isBar ? barHeight : HEIGHT}`}
        role="img"
        aria-labelledby={titleId}
        data-chart-motion="true"
      >
        <title id={titleId}>{title}</title>
        {forecastSplitX !== null ? (
          <rect
            x={forecastSplitX}
            y={TOP}
            width={WIDTH - RIGHT - forecastSplitX}
            height={HEIGHT - TOP - BOTTOM}
            className={styles.forecastWindow}
          />
        ) : null}
        {isBar ? (
          rows.map((row, index) => {
            const value = row[yIndex] as number;
            const zeroX = 190 + ((0 - minimum) / span) * 480;
            const valueX = 190 + ((value - minimum) / span) * 480;
            return (
              <g key={index}>
                <text
                  x="178"
                  y={30 + index * 34}
                  textAnchor="end"
                  className={styles.axis}
                >
                  {label(row[xIndex], locale)}
                </text>
                <rect
                  x={Math.min(zeroX, valueX)}
                  y={17 + index * 34}
                  width={Math.abs(valueX - zeroX)}
                  height={spec.type === "surge" ? "10" : "19"}
                  rx="2"
                  className={styles.bar}
                  data-chart-bar="true"
                >
                  <title>{`${label(row[xIndex], locale)}: ${value}`}</title>
                </rect>
                {spec.type === "surge" && numeric(row[baselineIndex]) ? (
                  <rect
                    x={Math.min(
                      zeroX,
                      190 + ((row[baselineIndex] - minimum) / span) * 480,
                    )}
                    y={29 + index * 34}
                    width={Math.abs(
                      ((row[baselineIndex] - minimum) / span) * 480 +
                        190 -
                        zeroX,
                    )}
                    height="5"
                    className={styles.baselineBar}
                  >
                    <title>{`${locale === "ru" ? "Базовый уровень" : "Базалық деңгей"}: ${row[baselineIndex]}`}</title>
                  </rect>
                ) : null}
                <text
                  x="750"
                  y={30 + index * 34}
                  textAnchor="end"
                  className={styles.axis}
                >
                  {valueLabel(value)}
                </text>
              </g>
            );
          })
        ) : (
          <>
            {[minimum, (minimum + maximum) / 2, maximum].map((tick) => (
              <g key={tick}>
                <line
                  x1={LEFT}
                  x2={WIDTH - RIGHT}
                  y1={y(tick)}
                  y2={y(tick)}
                  className={styles.gridLine}
                />
                <text
                  x={LEFT - 8}
                  y={y(tick) + 4}
                  textAnchor="end"
                  className={styles.axis}
                >
                  {valueLabel(tick)}
                </text>
              </g>
            ))}
            {series.map((name, seriesNumber) => {
              const points = rows
                .filter(
                  (row) =>
                    seriesIndex < 0 || String(row[seriesIndex] ?? "") === name,
                )
                .sort(
                  (a, b) =>
                    categories.indexOf(String(a[xIndex])) -
                    categories.indexOf(String(b[xIndex])),
                );
              return (
                <g
                  key={name}
                  className={
                    seriesNumber % 2
                      ? styles.alternateSeries
                      : styles.primarySeries
                  }
                >
                  {spec.type === "forecast"
                    ? (() => {
                        const bounds = points.filter(
                          (row) =>
                            numeric(row[lowerIndex]) &&
                            numeric(row[upperIndex]),
                        );
                        return bounds.length > 1 ? (
                          <polygon
                            points={[
                              ...bounds.map(
                                (row) =>
                                  `${x(row[xIndex])},${y(row[upperIndex] as number)}`,
                              ),
                              ...[...bounds]
                                .reverse()
                                .map(
                                  (row) =>
                                    `${x(row[xIndex])},${y(row[lowerIndex] as number)}`,
                                ),
                            ].join(" ")}
                            fill="currentColor"
                            opacity="0.12"
                            data-chart-area="true"
                          />
                        ) : null;
                      })()
                    : null}
                  <polyline
                    points={points
                      .map(
                        (row) =>
                          `${x(row[xIndex])},${y(row[yIndex] as number)}`,
                      )
                      .join(" ")}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeDasharray={seriesNumber % 2 ? "6 3" : undefined}
                    pathLength={1}
                    data-chart-line="true"
                  />
                  {points.map((row, index) => (
                    <circle
                      key={index}
                      cx={x(row[xIndex])}
                      cy={y(row[yIndex] as number)}
                      r="3"
                      fill="currentColor"
                      data-chart-point="true"
                      style={{
                        animationDelay: `${Math.min(index * 18, 360)}ms`,
                      }}
                    >
                      <title>{`${label(row[xIndex], locale)} · ${name}: ${row[yIndex]}`}</title>
                    </circle>
                  ))}
                </g>
              );
            })}
            {spec.type === "forecast" && observedIndex >= 0 ? (
              <polyline
                points={spec.rows
                  .filter((row) => numeric(row[observedIndex]))
                  .map(
                    (row) =>
                      `${x(row[xIndex])},${y(row[observedIndex] as number)}`,
                  )
                  .join(" ")}
                fill="none"
                stroke="var(--muted)"
                strokeWidth="2"
                strokeDasharray="4 3"
                pathLength={1}
                data-chart-line="historical"
              />
            ) : null}
            {forecastSplitX !== null ? (
              <line
                x1={forecastSplitX}
                x2={forecastSplitX}
                y1={TOP}
                y2={HEIGHT - BOTTOM}
                className={styles.forecastBoundary}
              />
            ) : null}
            {[0, Math.floor((categories.length - 1) / 2), categories.length - 1]
              .filter((value, index, array) => array.indexOf(value) === index)
              .map((index) => (
                <text
                  key={index}
                  x={x(categories[index])}
                  y={HEIGHT - 12}
                  textAnchor={
                    index === 0
                      ? "start"
                      : index === categories.length - 1
                        ? "end"
                        : "middle"
                  }
                  className={styles.axis}
                >
                  {label(categories[index], locale)}
                </text>
              ))}
          </>
        )}
      </svg>
      {spec.type === "forecast" || spec.type === "surge" ? (
        <figcaption className={styles.legend}>
          <span>
            <i className={styles.primarySwatch} aria-hidden="true" />
            {spec.type === "forecast"
              ? locale === "ru"
                ? "Прогноз"
                : "Болжам"
              : locale === "ru"
                ? "Наблюдалось"
                : "Бақыланған"}
          </span>
          <span>
            <i className={styles.referenceSwatch} aria-hidden="true" />
            {spec.type === "forecast"
              ? locale === "ru"
                ? "Наблюдения (если доступны)"
                : "Бақылаулар (бар болса)"
              : locale === "ru"
                ? "Базовый уровень"
                : "Базалық деңгей"}
          </span>
        </figcaption>
      ) : null}
      {seriesIndex >= 0 ? (
        <figcaption className={styles.legend}>
          {series.map((name, index) => (
            <span key={name}>
              <i
                className={
                  index % 2 ? styles.alternateSwatch : styles.primarySwatch
                }
                aria-hidden="true"
              />
              {name}
            </span>
          ))}
        </figcaption>
      ) : null}
      <details className={styles.dataDetails}>
        <summary>
          {locale === "ru" ? "Данные графика" : "График деректері"}
        </summary>
        <div className={styles.tableScroll}>
          <table className="lab-table">
            <thead>
              <tr>
                {spec.columns.map((column) => (
                  <th key={column.name} scope="col">
                    {column.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {spec.rows.slice(0, 100).map((row, index) => (
                <tr key={index}>
                  {row.map((cell, cellIndex) => (
                    <td key={cellIndex}>{String(cell ?? "—")}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {spec.rows.length > 100 ? (
          <p>
            {locale === "ru"
              ? "Показаны первые 100 строк. Полные данные доступны в экспорте."
              : "Алғашқы 100 жол көрсетілген. Толық деректерді экспорттауға болады."}
          </p>
        ) : null}
      </details>
    </figure>
  );
}
