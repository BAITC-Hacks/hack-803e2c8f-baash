"use client";

import {
  Database,
  Flag,
  History,
  KeyRound,
  Network,
  ShieldCheck,
} from "lucide-react";

type Locale = "ru" | "kk";

const text = {
  ru: {
    eyebrow: "Управление",
    title: "Контуры пилота",
    intro:
      "Только просмотр синтетической конфигурации. Изменения требуют автора и проверяющего.",
    policies: "Версии политик",
    sources: "Источники и карантин",
    models: "Реестр моделей",
    access: "Роли и область доступа",
    flags: "Функциональные флаги",
    audit: "Поиск аудита",
  },
  kk: {
    eyebrow: "Басқару",
    title: "Пилот контурлары",
    intro:
      "Синтетикалық конфигурация тек оқуға арналған. Өзгеріске автор мен тексеруші қажет.",
    policies: "Саясат нұсқалары",
    sources: "Дереккөздер және карантин",
    models: "Модельдер тізілімі",
    access: "Рөлдер және қолжетімділік аясы",
    flags: "Функция жалаушалары",
    audit: "Аудитті іздеу",
  },
} as const;

export function AdminPanel({ locale }: { locale: Locale }) {
  const copy = text[locale];
  return (
    <section className="admin-shell" aria-labelledby="admin-title">
      <header className="admin-heading">
        <div>
          <p className="eyebrow">{copy.eyebrow}</p>
          <h1 id="admin-title">{copy.title}</h1>
          <p>{copy.intro}</p>
        </div>
        <span className="state-stale">Synthetic · read only</span>
      </header>

      <div className="admin-grid">
        <section aria-labelledby="policy-admin-title">
          <Database aria-hidden="true" size={20} />
          <h2 id="policy-admin-title">{copy.policies}</h2>
          <ul>
            <li>routing · synthetic-routing-1.0.0 · approved</li>
            <li>confidence · synthetic-confidence-1.0.0 · approved</li>
            <li>SLA · unavailable · policy not approved</li>
          </ul>
          <small>Effective 1 Jan 2026 UTC · rollback target required</small>
        </section>

        <section aria-labelledby="sources-admin-title">
          <Network aria-hidden="true" size={20} />
          <h2 id="sources-admin-title">{copy.sources}</h2>
          <dl>
            <div>
              <dt>Replay</dt>
              <dd className="state-present">healthy</dd>
            </div>
            <div>
              <dt>Open311 sandbox</dt>
              <dd>synthetic only</dd>
            </div>
            <div>
              <dt>First region</dt>
              <dd className="state-missing">not configured</dd>
            </div>
            <div>
              <dt>Unknown statuses</dt>
              <dd>mapping review</dd>
            </div>
          </dl>
        </section>

        <section aria-labelledby="models-admin-title">
          <ShieldCheck aria-hidden="true" size={20} />
          <h2 id="models-admin-title">{copy.models}</h2>
          <dl>
            <div>
              <dt>Champion</dt>
              <dd>synthetic-linear-baseline-1.0.0</dd>
            </div>
            <div>
              <dt>Rollback</dt>
              <dd>mock-rules-1.0.0</dd>
            </div>
            <div>
              <dt>Quality claim</dt>
              <dd className="state-missing">not allowed</dd>
            </div>
          </dl>
        </section>

        <section aria-labelledby="access-admin-title">
          <KeyRound aria-hidden="true" size={20} />
          <h2 id="access-admin-title">{copy.access}</h2>
          <dl>
            <div>
              <dt>Actor</dt>
              <dd>local-operator</dd>
            </div>
            <div>
              <dt>Region</dt>
              <dd>ALA</dd>
            </div>
            <div>
              <dt>Purpose</dt>
              <dd>synthetic-development</dd>
            </div>
            <div>
              <dt>Production OIDC</dt>
              <dd className="state-missing">not configured</dd>
            </div>
          </dl>
        </section>

        <section aria-labelledby="flags-admin-title">
          <Flag aria-hidden="true" size={20} />
          <h2 id="flags-admin-title">{copy.flags}</h2>
          <ul>
            <li>Manual path — enabled</li>
            <li>CPU/lexical fallback — enabled</li>
            <li>Generated replies — disabled</li>
            <li>Automatic duplicate merge — prohibited</li>
          </ul>
        </section>

        <section aria-labelledby="audit-admin-title">
          <History aria-hidden="true" size={20} />
          <h2 id="audit-admin-title">{copy.audit}</h2>
          <label htmlFor="audit-correlation">Correlation ID</label>
          <input id="audit-correlation" placeholder="e.g. e2e-…" />
          <button className="secondary-action" type="button">
            {copy.audit}
          </button>
          <small>Search is bounded by verified region and role.</small>
        </section>
      </div>
    </section>
  );
}
