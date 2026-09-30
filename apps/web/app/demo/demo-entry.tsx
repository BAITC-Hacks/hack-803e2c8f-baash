"use client";

import { useState, useSyncExternalStore } from "react";
import { ArrowRight, Activity, ShieldCheck } from "lucide-react";
import OperatorWorkspace from "../operator-workspace";

const ENTRY_KEY = "pulse109-demo-disclosure-v2";
const MOCK_DISCLOSURE =
  "Используются вымышленные муниципальные записи. Интерфейс и сценарии работают через локальный mock API; база данных и внешняя доставка не подключены.";
const CONNECTED_DISCLOSURE =
  "Используются синтетические муниципальные записи. Демо работает через API, PostgreSQL, аудит и worker. Региональная CRM не подключена; доставка воспроизводится demo adapter-ом.";

function subscribe(onChange: () => void) {
  window.addEventListener("storage", onChange);
  window.addEventListener("pulse109-demo-entry", onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener("pulse109-demo-entry", onChange);
  };
}

function getEntered() {
  try {
    return window.localStorage.getItem(ENTRY_KEY) === "accepted";
  } catch {
    return false;
  }
}

export default function DemoEntry({ mockMode }: { mockMode: boolean }) {
  const persistedEntry = useSyncExternalStore(
    subscribe,
    getEntered,
    () => false,
  );
  const [enteredThisVisit, setEnteredThisVisit] = useState(false);
  const entered = persistedEntry || enteredThisVisit;

  function enter() {
    try {
      window.localStorage.setItem(ENTRY_KEY, "accepted");
    } catch {
      // The disclosure remains visible on the next visit when storage is blocked.
    }
    setEnteredThisVisit(true);
    window.dispatchEvent(new Event("pulse109-demo-entry"));
  }

  if (entered) return <OperatorWorkspace />;

  return (
    <main className="demo-entry">
      <section className="demo-entry-card" aria-labelledby="demo-entry-title">
        <div className="demo-entry-brand">
          <span className="demo-entry-mark" aria-hidden="true">
            <Activity size={20} />
          </span>
          <span>Pulse 109</span>
          <span className="demo-entry-separator">/</span>
          <span>Interactive Demo</span>
        </div>
        <div className="demo-entry-content">
          <span className="demo-entry-icon" aria-hidden="true">
            <ShieldCheck size={21} />
          </span>
          <p className="demo-entry-eyebrow">Operations workspace</p>
          <h1 id="demo-entry-title">Перед началом</h1>
          <p className="demo-entry-disclosure">
            {mockMode ? MOCK_DISCLOSURE : CONNECTED_DISCLOSURE}
          </p>
          <button type="button" className="demo-entry-cta" onClick={enter}>
            Войти в Operations Center{" "}
            <ArrowRight size={16} aria-hidden="true" />
          </button>
        </div>
        <p className="demo-entry-footnote">Pulse 109 · Алматы</p>
      </section>
    </main>
  );
}
