export default function Forbidden() {
  return (
    <main className="system-state" role="alert">
      <p className="eyebrow">403</p>
      <h1>Нет доступа к региону</h1>
      <p>Ваша роль не разрешает просматривать эту запись.</p>
    </main>
  );
}
