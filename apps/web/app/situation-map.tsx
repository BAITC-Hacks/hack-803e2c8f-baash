"use client";

import {
  Map as MapLibreMap,
  NavigationControl,
  type GeoJSONSource,
  type GeoJSONSourceSpecification,
  type StyleSpecification,
} from "maplibre-gl";
import { useEffect, useRef } from "react";

const syntheticPoints: GeoJSONSourceSpecification["data"] = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      geometry: { type: "Point", coordinates: [76.8897, 43.2389] },
      properties: { region: "ALA", state: "present", count: 8 },
    },
    {
      type: "Feature",
      geometry: { type: "Point", coordinates: [71.4304, 51.1282] },
      properties: { region: "AST", state: "stale", count: 6 },
    },
    {
      type: "Feature",
      geometry: { type: "Point", coordinates: [73.1094, 49.8028] },
      properties: { region: "KAR", state: "missing", count: 0 },
    },
  ],
};

const emptyStyle: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [
    {
      id: "background",
      type: "background",
      paint: { "background-color": "#eef0e9" },
    },
  ],
};

export function SituationMap() {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current) return;
    const map = new MapLibreMap({
      container: container.current,
      style: emptyStyle,
      center: [71.5, 48.2],
      zoom: 3.1,
      attributionControl: false,
    });
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => {
      map.addSource("synthetic-regions", {
        type: "geojson",
        data: syntheticPoints,
      });
      map.addLayer({
        id: "synthetic-region-points",
        type: "circle",
        source: "synthetic-regions",
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["get", "count"],
            0,
            8,
            10,
            20,
          ],
          "circle-color": [
            "match",
            ["get", "state"],
            "present",
            "#1c6b55",
            "stale",
            "#ba7114",
            "#a44343",
          ],
          "circle-opacity": 0.82,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
        },
      });

      const martinTiles = process.env.NEXT_PUBLIC_MARTIN_TILE_URL;
      if (martinTiles) {
        map.addSource("martin-appeals", {
          type: "vector",
          tiles: [martinTiles],
          minzoom: 0,
          maxzoom: 14,
        });
        map.addLayer({
          id: "martin-appeal-points",
          type: "circle",
          source: "martin-appeals",
          "source-layer": "appeal_points",
          paint: { "circle-radius": 4, "circle-color": "#4b61d1" },
        });
      }
    });
    return () => {
      const source = map.getSource("synthetic-regions") as
        | GeoJSONSource
        | undefined;
      if (source) source.setData({ type: "FeatureCollection", features: [] });
      map.remove();
    };
  }, []);

  return (
    <section className="map-panel" aria-labelledby="map-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Spatial evidence</p>
          <h2 id="map-title">Coverage map</h2>
        </div>
        <span>Synthetic fixture · Martin-ready</span>
      </div>
      <div
        className="map-canvas"
        ref={container}
        role="img"
        aria-label="Map of synthetic regional coverage: Almaty present, Astana stale, Karaganda missing"
      />
      <ul className="map-alternative" aria-label="Map data as text">
        <li>ALA — present — 8 synthetic appeals</li>
        <li>AST — stale — 6 synthetic appeals</li>
        <li>KAR — missing — no numeric value</li>
      </ul>
    </section>
  );
}
