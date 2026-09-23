export default function Unauthorized() {
  return (
    <main className="system-state" role="alert">
      <p className="eyebrow">401</p>
      <h1>Сессия не подтверждена</h1>
      <p>Войдите снова, чтобы продолжить работу с обращениями.</p>
    </main>
  );
}
