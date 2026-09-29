type Locale = "ru" | "kk";

const topics: Record<string, Record<Locale, string>> = {
  "topic:water": { ru: "Водоснабжение", kk: "Сумен жабдықтау" },
  "topic:roads": { ru: "Дороги", kk: "Жолдар" },
  "topic:utilities": { ru: "Городское освещение", kk: "Қала жарығы" },
  "topic:waste": { ru: "Вывоз мусора", kk: "Қоқыс шығару" },
  "topic:heating": { ru: "Отопление", kk: "Жылыту" },
};

const services: Record<string, Record<Locale, string>> = {
  "service:water": { ru: "Водоканал", kk: "Су қызметі" },
  "service:roads": { ru: "Дорожная служба", kk: "Жол қызметі" },
  "service:utilities": { ru: "Коммунальная служба", kk: "Коммуналдық қызмет" },
  "service:waste": { ru: "Служба вывоза", kk: "Қоқыс шығару қызметі" },
};

export function incidentTopicLabel(topicId: string, locale: Locale): string {
  return topics[topicId]?.[locale] ?? topicId;
}

export function incidentServiceLabel(
  serviceId: string,
  locale: Locale,
): string {
  return services[serviceId]?.[locale] ?? serviceId;
}

export function incidentStateLabel(state: string, locale: Locale): string {
  const labels: Record<string, Record<Locale, string>> = {
    open: { ru: "Открыт", kk: "Ашық" },
    active: { ru: "В работе", kk: "Жұмыста" },
    proposed: { ru: "Предложен", kk: "Ұсынылған" },
    confirmed: { ru: "Подтверждён", kk: "Расталған" },
    monitoring: { ru: "Наблюдение", kk: "Бақылауда" },
    resolved: { ru: "Решён", kk: "Шешілген" },
  };
  return (
    labels[state.toLowerCase()]?.[locale] ??
    (locale === "ru" ? "Статус обновлён" : "Күй жаңартылды")
  );
}

export function incidentReportCount(count: number, locale: Locale): string {
  if (locale === "kk") return `${count} өтініш`;
  const lastTwo = count % 100;
  const last = count % 10;
  const noun =
    lastTwo >= 11 && lastTwo <= 14
      ? "обращений"
      : last === 1
        ? "обращение"
        : last >= 2 && last <= 4
          ? "обращения"
          : "обращений";
  return `${count} ${noun}`;
}

export function incidentDuration(minutes: number, locale: Locale): string {
  if (minutes < 60)
    return locale === "ru" ? `${minutes} мин` : `${minutes} мин`;
  if (minutes < 1440) {
    const hours = Math.round(minutes / 60);
    return locale === "ru" ? `${hours} ч` : `${hours} сағ`;
  }
  const days = Math.round(minutes / 1440);
  return locale === "ru" ? `${days} дн` : `${days} күн`;
}
