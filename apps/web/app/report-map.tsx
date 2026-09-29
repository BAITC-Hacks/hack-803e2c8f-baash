"use client";

import { useEffect, useMemo, useRef } from "react";
import {
  AttributionControl,
  GeoJSONSource,
  Map as MapLibre,
  MapLayerMouseEvent,
  Marker,
  Popup,
} from "maplibre-gl";

export type ReportPoint = {
  longitude: number;
  latitude: number;
  label?: string;
  kind?: "confirmed" | "candidate";
};

type MapMode = "overview" | "cluster" | "incident";
type Locale = "ru" | "kk";

const ALMATY_CENTER: [number, number] = [76.915, 43.25];
const ALMATY_BOUNDS: [[number, number], [number, number]] = [
  [76.76, 43.12],
  [77.12, 43.39],
];
type PointGeometry = { type: "Point"; coordinates: [number, number] };
type MapFeature = {
  type: "Feature";
  id: string;
  properties: { label: string; kind: "confirmed" | "candidate" };
  geometry: PointGeometry;
};
type MapFeatureCollection = {
  type: "FeatureCollection";
  features: MapFeature[];
};
type MapData = Parameters<GeoJSONSource["setData"]>[0];

function circlePolygon(
  center: { longitude: number; latitude: number },
  radiusMetres: number,
) {
  const coordinates: [number, number][] = [];
  const latitudeRadius = radiusMetres / 111_320;
  const longitudeRadius =
    radiusMetres / (111_320 * Math.cos((center.latitude * Math.PI) / 180));
  for (let step = 0; step <= 48; step += 1) {
    const angle = (step / 48) * Math.PI * 2;
    coordinates.push([
      center.longitude + Math.cos(angle) * longitudeRadius,
      center.latitude + Math.sin(angle) * latitudeRadius,
    ]);
  }
  return {
    type: "Feature" as const,
    properties: {},
    geometry: { type: "Polygon" as const, coordinates: [coordinates] },
  };
}

export function ReportMap({
  points,
  centroid,
  spreadMetres,
  emptyLabel,
  mode = "cluster",
  locale = "ru",
  countLabel,
  ariaLabel,
}: {
  points: ReportPoint[];
  centroid?: { longitude: number; latitude: number } | null;
  spreadMetres?: number | null;
  emptyLabel: string;
  mode?: MapMode;
  locale?: Locale;
  countLabel?: string;
  ariaLabel?: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibre | null>(null);
  const popupRef = useRef<Popup | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const features = useMemo(
    () =>
      points
        .filter(
          (point) =>
            Number.isFinite(point.longitude) && Number.isFinite(point.latitude),
        )
        .map((point, index) => ({
          type: "Feature" as const,
          id: `${point.longitude}:${point.latitude}:${index}`,
          properties: {
            label: point.label ?? "Обращение",
            kind: point.kind ?? "candidate",
          },
          geometry: {
            type: "Point" as const,
            coordinates: [point.longitude, point.latitude] as [number, number],
          },
        })),
    [points],
  );
  const geometry = useMemo<MapFeatureCollection>(
    () => ({ type: "FeatureCollection", features }),
    [features],
  );
  const footprint = useMemo(() => {
    if (!centroid || !spreadMetres || spreadMetres <= 0 || mode === "overview")
      return { type: "FeatureCollection" as const, features: [] };
    return {
      type: "FeatureCollection" as const,
      features: [circlePolygon(centroid, spreadMetres)],
    };
  }, [centroid, mode, spreadMetres]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new MapLibre({
      container: containerRef.current,
      center: ALMATY_CENTER,
      zoom: 11.7,
      minZoom: 10.5,
      maxZoom: 16,
      maxBounds: ALMATY_BOUNDS,
      pitch: 0,
      bearing: 0,
      attributionControl: false,
      dragPan: false,
      dragRotate: false,
      scrollZoom: false,
      doubleClickZoom: false,
      keyboard: false,
      touchZoomRotate: false,
      style: {
        version: 8,
        glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
    });
    mapRef.current = map;
    map.addControl(new AttributionControl({ compact: true }), "bottom-right");

    const setupLayers = () => {
      if (map.getSource("report-points")) return;
      map.addSource("report-points", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
        cluster: true,
        clusterRadius: 42,
        clusterMaxZoom: 15,
      });
      map.addLayer({
        id: "report-cluster-halo",
        type: "circle",
        source: "report-points",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": "#3f72d8",
          "circle-radius": ["step", ["get", "point_count"], 20, 5, 24, 10, 29],
          "circle-opacity": 0.18,
          "circle-stroke-color": "#3f72d8",
          "circle-stroke-width": 1,
        },
      });
      map.addLayer({
        id: "report-clusters",
        type: "circle",
        source: "report-points",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": mode === "incident" ? "#d9574f" : "#d69632",
          "circle-radius": ["step", ["get", "point_count"], 15, 5, 19, 10, 24],
          "circle-stroke-color": "#fff",
          "circle-stroke-width": 2,
        },
      });
      map.addLayer({
        id: "report-cluster-count",
        type: "symbol",
        source: "report-points",
        filter: ["has", "point_count"],
        layout: {
          "text-field": ["get", "point_count_abbreviated"],
          "text-font": ["Open Sans Bold"],
          "text-size": 12,
          "text-allow-overlap": true,
        },
        paint: { "text-color": "#fff" },
      });
      map.addLayer({
        id: "report-unclustered",
        type: "circle",
        source: "report-points",
        filter: ["!has", "point_count"],
        paint: {
          "circle-color": [
            "match",
            ["get", "kind"],
            "confirmed",
            "#3472d6",
            "#8996aa",
          ],
          "circle-radius": 5,
          "circle-stroke-color": "#fff",
          "circle-stroke-width": 2,
        },
      });
      map.on("click", "report-clusters", (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        const clusterId = feature?.properties?.cluster_id;
        const coordinates = (feature?.geometry as PointGeometry | undefined)
          ?.coordinates;
        const source = map.getSource("report-points") as
          | GeoJSONSource
          | undefined;
        if (typeof clusterId !== "number" || !coordinates || !source) return;
        source.getClusterExpansionZoom(clusterId).then((zoom) => {
          map.easeTo({ center: coordinates, zoom, duration: 320 });
        });
      });
      map.on("mouseenter", "report-clusters", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "report-clusters", () => {
        map.getCanvas().style.cursor = "";
      });
      map.addSource("incident-footprint", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "incident-footprint-fill",
        type: "fill",
        source: "incident-footprint",
        paint: {
          "fill-color": mode === "incident" ? "#d9574f" : "#3f72d8",
          "fill-opacity": 0.1,
        },
      });
      map.addLayer({
        id: "incident-footprint-line",
        type: "line",
        source: "incident-footprint",
        paint: {
          "line-color": mode === "incident" ? "#d9574f" : "#3f72d8",
          "line-width": 2,
          "line-dasharray": [2, 2],
        },
      });

      map.on("click", "report-unclustered", (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        const coordinates = (feature?.geometry as PointGeometry | undefined)
          ?.coordinates;
        const label = String(feature?.properties?.label ?? "Обращение");
        if (!coordinates) return;
        popupRef.current?.remove();
        popupRef.current = new Popup({ closeButton: false, offset: 10 })
          .setLngLat(coordinates as [number, number])
          .setText(label)
          .addTo(map);
      });
      map.on("mouseenter", "report-unclustered", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "report-unclustered", () => {
        map.getCanvas().style.cursor = "";
      });
    };
    if (map.isStyleLoaded()) setupLayers();
    else map.once("style.load", setupLayers);

    return () => {
      popupRef.current?.remove();
      map.remove();
      mapRef.current = null;
    };
  }, [mode]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const updateSources = () => {
      const source = map.getSource("report-points") as
        | GeoJSONSource
        | undefined;
      const areaSource = map.getSource("incident-footprint") as
        | GeoJSONSource
        | undefined;
      source?.setData(geometry as MapData);
      areaSource?.setData(footprint as MapData);
    };
    if (map.getSource("report-points")) updateSources();
    else map.once("style.load", updateSources);
  }, [geometry, footprint]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const drawMarkers = () => {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      const located = points.filter(
        (point) =>
          Number.isFinite(point.longitude) && Number.isFinite(point.latitude),
      );
      located.forEach((point) => {
        const pin = document.createElement("button");
        pin.type = "button";
        pin.className = `report-map-point-marker report-map-point-marker-${point.kind ?? "candidate"}`;
        pin.setAttribute("aria-label", point.label ?? "Обращение на карте");
        pin.title = point.label ?? "Обращение";
        pin.addEventListener("click", (event) => {
          event.stopPropagation();
          popupRef.current?.remove();
          popupRef.current = new Popup({ closeButton: false, offset: 10 })
            .setLngLat([point.longitude, point.latitude])
            .setText(point.label ?? "Обращение")
            .addTo(map);
        });
        markersRef.current.push(
          new Marker({ element: pin, anchor: "center" })
            .setLngLat([point.longitude, point.latitude])
            .addTo(map),
        );
      });

      if (located.length > 1) {
        const center =
          mode !== "overview" && centroid
            ? centroid
            : {
                longitude:
                  located.reduce((sum, point) => sum + point.longitude, 0) /
                  located.length,
                latitude:
                  located.reduce((sum, point) => sum + point.latitude, 0) /
                  located.length,
              };
        const bubble = document.createElement("div");
        bubble.className = `report-map-cluster-marker${mode === "incident" ? " report-map-cluster-marker-incident" : ""}`;
        bubble.textContent = String(located.length);
        bubble.setAttribute("role", "img");
        bubble.setAttribute(
          "aria-label",
          locale === "ru"
            ? `${located.length} обращений`
            : `${located.length} өтініш`,
        );
        markersRef.current.push(
          new Marker({ element: bubble, anchor: "center" })
            .setLngLat([center.longitude, center.latitude])
            .addTo(map),
        );
      }

      if (centroid && spreadMetres && mode !== "overview") {
        const halo = document.createElement("div");
        halo.className = `report-map-selected-halo${mode === "incident" ? " report-map-selected-halo-incident" : ""}`;
        halo.setAttribute("aria-hidden", "true");
        markersRef.current.push(
          new Marker({ element: halo, anchor: "center" })
            .setLngLat([centroid.longitude, centroid.latitude])
            .addTo(map),
        );
      }
    };
    drawMarkers();
    return () => {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
    };
  }, [centroid, locale, mode, points, spreadMetres]);

  useEffect(() => {
    if (!centroid || mode === "overview") return;
    mapRef.current?.easeTo({
      center: [centroid.longitude, centroid.latitude],
      duration: 420,
      essential: false,
    });
  }, [centroid, mode]);

  if (points.length === 0 && mode !== "overview") {
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

  return (
    <figure
      className={`report-map report-map-${mode}`}
      aria-label={
        ariaLabel ??
        (locale === "ru"
          ? "Карта обращений Алматы"
          : "Алматы өтініштерінің картасы")
      }
    >
      <div ref={containerRef} className="report-map-canvas" />
      {mode === "incident" ? (
        <span className="report-map-state">
          {locale === "ru" ? "Инцидент создан" : "Оқиға құрылды"}
        </span>
      ) : null}
      {countLabel ? (
        <figcaption className="report-map-count">{countLabel}</figcaption>
      ) : null}
      <div
        className="report-map-controls"
        aria-label={
          locale === "ru"
            ? "Управление масштабом карты"
            : "Карта масштабын басқару"
        }
      >
        <button
          type="button"
          aria-label={locale === "ru" ? "Приблизить" : "Жақындату"}
          onClick={() => mapRef.current?.zoomIn({ duration: 180 })}
        >
          +
        </button>
        <button
          type="button"
          aria-label={locale === "ru" ? "Отдалить" : "Алыстату"}
          onClick={() => mapRef.current?.zoomOut({ duration: 180 })}
        >
          −
        </button>
      </div>
    </figure>
  );
}
