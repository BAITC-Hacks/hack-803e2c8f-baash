"use client";

import { useEffect, useState } from "react";
import styles from "./presenter-panel.module.css";

export type PresenterPreset = {
  id: number;
  description: string;
  location: string;
  latitude: number;
  longitude: number;
};

type PresenterView = "intake" | "queue" | "operations" | "incidents";
type Check = { label: string; ready: boolean; detail: string };

const steps: { label: string; view: PresenterView; hint: string }[] = [
  {
    label: "Обращение",
    view: "intake",
    hint: "Загрузите пресет и отправьте вручную.",
  },
  {
    label: "Оператор",
    view: "queue",
    hint: "Проверьте совет и подтвердите решение.",
  },
  { label: "Radar", view: "operations", hint: "Запустите поиск за 6 часов." },
  {
    label: "War Room",
    view: "incidents",
    hint: "Создайте инцидент из кластера.",
  },
  {
    label: "Ask Pulse",
    view: "operations",
    hint: "Покажите цифру, прогноз и экспорт.",
  },
];

const waterSources = new Set(
  Array.from({ length: 6 }, (_, index) => `demo-emerging-water-0${index + 1}`),
);

async function readJson<T>(
  url: string,
  regionId: string,
  body?: object,
): Promise<T> {
  const response = await fetch(url, {
    method: body ? "POST" : "GET",
    headers: {
      "X-Region-Id": regionId,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return (await response.json()) as T;
}

async function readChecks(regionId: string): Promise<Check[]> {
  type RequestRow = { source_request_id: string; request_id: string };
  type ClusterReport = {
    clusters: { members: { request_id: string }[] }[];
  };
  type AskAnswer = {
    status: string;
    intent?: { horizon_days?: number };
    chart?: { type: string; rows: unknown[] };
  };

  const health = await readJson<{
    profile: string;
    checks?: { database?: string };
  }>("/api/core/health/ready", regionId);
  const checks: Check[] = [
    {
      label: "Приложение и БД",
      ready: health.profile === "demo" && health.checks?.database === "ready",
      detail: health.profile,
    },
  ];
  if (regionId !== "ALA") {
    return [
      ...checks,
      { label: "Сценарий", ready: false, detail: "Проверен только для ALA" },
    ];
  }

  const rows: RequestRow[] = [];
  for (let offset = 0; offset < 5000; offset += 100) {
    const page = await readJson<RequestRow[]>(
      `/api/core/requests?limit=100&offset=${offset}`,
      regionId,
    );
    rows.push(...page);
    if (page.length < 100) break;
  }
  const historyDays = new Set(
    rows
      .filter((row) => row.source_request_id.startsWith("DEMO-HISTORY-"))
      .map((row) => row.source_request_id.slice(13, 21)),
  );
  checks.push({
    label: "История",
    ready: historyDays.size >= 120,
    detail: `${historyDays.size} дней`,
  });
  const waterIds = new Set(
    rows
      .filter((row) => waterSources.has(row.source_request_id))
      .map((row) => row.request_id),
  );
  const radar = await readJson<ClusterReport>(
    "/api/core/discovery/scans?window_hours=6&persist=false",
    regionId,
    {},
  );
  const clusterReady =
    waterIds.size === 6 &&
    radar.clusters.some((cluster) => {
      const members = new Set(
        cluster.members.map((member) => member.request_id),
      );
      return [...waterIds].every((id) => members.has(id));
    });
  checks.push({
    label: "Сигнал Radar",
    ready: clusterReady,
    detail: clusterReady
      ? "6 сообщений в одном кластере"
      : "Сигнал не подтверждён",
  });

  const forecasts = await Promise.all(
    ([1, 2, 3] as const).map((months) =>
      readJson<AskAnswer>("/api/core/analytics/ask", regionId, {
        question: `Прогноз нагрузки по обращениям в Алматы на ${months} месяц`,
        locale: "ru-KZ",
      }),
    ),
  );
  const forecastReady = forecasts.every(
    (answer, index) =>
      answer.status === "available" &&
      answer.intent?.horizon_days === (index + 1) * 30 &&
      answer.chart?.type === "forecast" &&
      (answer.chart.rows.length ?? 0) > 120,
  );
  checks.push({
    label: "Прогноз",
    ready: forecastReady,
    detail: forecastReady ? "30 / 60 / 90 дней" : "Проверьте историю",
  });
  return checks;
}

export function PresenterPanel({
  regionId,
  onNavigate,
  onLoadPreset,
  onClose,
}: {
  regionId: string;
  onNavigate: (view: PresenterView) => void;
  onLoadPreset: (preset: PresenterPreset) => void;
  onClose: () => void;
}) {
  const [checks, setChecks] = useState<Check[] | null>(null);
  const [checkError, setCheckError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [step, setStep] = useState(0);

  useEffect(() => {
    let active = true;
    void readChecks(regionId)
      .then((result) => {
        if (active) {
          setChecks(result);
          setCheckError("");
        }
      })
      .catch(() => {
        if (active) {
          setChecks(null);
          setCheckError("Проверка недоступна; используйте demo.ps1 prepare.");
        }
      });
    return () => {
      active = false;
    };
  }, [regionId, refresh]);

  function loadWaterPreset() {
    onLoadPreset({
      id: Date.now(),
      description:
        "Синтетический пример: после ремонта вода стала мутной и появился металлический запах.",
      location: "Условный квартал Алмалы, Алматы",
      latitude: 43.2414,
      longitude: 76.8951,
    });
    onNavigate("intake");
    setStep(0);
  }

  return (
    <aside className={styles.panel} aria-label="Помощник ведущего демо">
      <div className={styles.header}>
        <div>
          <span className={styles.kicker}>PULSE 109 · PRESENTER</span>
          <h2>Сценарий показа</h2>
        </div>
        <button type="button" onClick={onClose} aria-label="Скрыть помощник">
          ×
        </button>
      </div>
      <p className={styles.notice}>
        Только синтетические данные. Это помощник, не статус реального пилота.
      </p>
      <div className={styles.checks} aria-live="polite">
        {checks ? (
          checks.map((check) => (
            <div className={styles.check} key={check.label}>
              <span className={check.ready ? styles.ready : styles.notReady}>
                {check.ready ? "✓" : "!"}
              </span>
              <span>{check.label}</span>
              <small>{check.detail}</small>
            </div>
          ))
        ) : (
          <p>{checkError || "Проверяем API…"}</p>
        )}
      </div>
      <button
        className={styles.textButton}
        type="button"
        onClick={() => setRefresh((value) => value + 1)}
      >
        Проверить ещё раз
      </button>
      <div className={styles.stepCard}>
        <span>
          ШАГ {step + 1} / {steps.length}
        </span>
        <h3>{steps[step].label}</h3>
        <p>{steps[step].hint}</p>
        <div className={styles.actions}>
          <button
            type="button"
            disabled={step === 0}
            onClick={() => setStep(step - 1)}
          >
            Назад
          </button>
          <button type="button" onClick={() => onNavigate(steps[step].view)}>
            Открыть
          </button>
          <button
            type="button"
            disabled={step === steps.length - 1}
            onClick={() => setStep(step + 1)}
          >
            Далее
          </button>
        </div>
      </div>
      <button
        className={styles.presetButton}
        type="button"
        onClick={loadWaterPreset}
      >
        Заполнить пример: качество воды
      </button>
      <p className={styles.footnote}>
        Форма только заполняется. Отправка и решения остаются ручными.
      </p>
    </aside>
  );
}
