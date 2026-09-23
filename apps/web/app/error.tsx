"use client";

export default function Error({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="system-state" role="alert">
      <p className="eyebrow">Pulse 109</p>
      <h1>Временная ошибка сервиса</h1>
      <p>
        Данные не потеряны. Повторите попытку или продолжите в ручном режиме.
      </p>
      <button className="primary-action" type="button" onClick={() => reset()}>
        Повторить
      </button>
    </main>
  );
}
