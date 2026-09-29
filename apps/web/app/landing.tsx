"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  CircleHelp,
  FileDown,
  MapPinned,
  Network,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import { ArrivalChart, type Bucket } from "./arrival-chart";
import styles from "./landing.module.css";

type Locale = "ru" | "kk";

const arrivals: Bucket[] = [
  { start: "2026-09-26T08:00:00Z", count: 2, by_topic: { water: 2 } },
  { start: "2026-09-26T09:00:00Z", count: 3, by_topic: { water: 2, roads: 1 } },
  { start: "2026-09-26T10:00:00Z", count: 4, by_topic: { water: 3, roads: 1 } },
  { start: "2026-09-26T11:00:00Z", count: 3, by_topic: { water: 2, roads: 1 } },
  { start: "2026-09-26T12:00:00Z", count: 7, by_topic: { water: 5, roads: 2 } },
  { start: "2026-09-26T13:00:00Z", count: 5, by_topic: { water: 3, roads: 2 } },
  { start: "2026-09-26T14:00:00Z", count: 9, by_topic: { water: 6, roads: 3 } },
];

const copy = {
  ru: {
    navProduct: "Продукт",
    navArchitecture: "Архитектура",
    navDemo: "Демо",
    heroKicker: "Pulse 109 · городские операции",
    language: "Язык страницы",
    heroTitleEditorial: "Intelligence for",
    heroTitleSystem: "every city signal.",
    heroText:
      "Превращайте обращения жителей в понятные действия, связанные инциденты и ранние операционные сигналы.",
    openDemo: "Open Interactive Demo",
    howItWorks: "Как это работает",
    synthetic: "Синтетический пример",
    opsTitle: "Операционный центр",
    arrivals: "Обращения за сутки",
    attention: "Требует внимания",
    emerging: "Похожие обращения растут",
    reports: "обращений",
    incidents: "инциденты",
    intake: "Умный приём",
    intakeText:
      "Собирайте контекст обращения и показывайте оператору прозрачную подсказку для проверки.",
    assistant: "Помощник оператора",
    assistantText:
      "Связывайте похожие сигналы и подсказывайте следующий шаг. Решение остаётся у человека.",
    situation: "Ситуационный центр",
    situationText:
      "Следите за обращениями, инцидентами и операционными изменениями в одном рабочем пространстве.",
    proposed: "Предложено для проверки",
    confirmed: "Подтверждает оператор",
    nextAction: "Следующее действие",
    inspect: "Проверить связанные обращения",
    advisory: "Подсказка, не автоматическое решение",
    workflowKicker: "Связанный процесс оператора",
    workflowTitle: "От обращения — к ответу города.",
    workflowIntro:
      "Один рабочий путь связывает приём обращения, решение оператора и реакцию на городскую ситуацию.",
    stepIntake: "Обращение поступило",
    stepReview: "Оператор проверил",
    stepResponse: "Команда действует",
    askKicker: "Ask Pulse · аналитика с проверяемым источником",
    askTitle: "Спросите о ситуации. Проверьте каждый ответ.",
    askText:
      "Ask Pulse отвечает на вопросы по разрешённым метрикам, показывает источник и ограничения, а затем открывает путь к данным.",
    askQuestion: "Как менялось число обращений за последние 7 дней?",
    result: "Фактическая динамика",
    resultTotal: "142 обращения",
    sampleTotal: "Обращений в синтетическом примере",
    provenance: "Как рассчитано",
    trustedTime: "Использовано достоверное время поступления",
    excluded: "Записи с неизвестным временем остаются вне графика",
    drilldown: "Посмотреть обращения",
    export: "PDF / XLSX",
    forecast: "Прогноз на 1–3 месяца доступен только при достаточной истории.",
    incidentKicker: "От обращений — к подтверждённому инциденту",
    manyTitle: "109 получает обращения. Pulse помогает увидеть общий инцидент.",
    manyText:
      "Система выявляет похожие сигналы. Оператор проверяет группу и вручную решает, создавать ли инцидент.",
    appeal: "Обращение",
    cluster: "Группа для проверки",
    human: "Решение оператора",
    incident: "Инцидент",
    noAuto: "Без автоматического объединения",
    factsTitle: "Создано для реального процесса 109.",
    factsIntro:
      "Вместо логотипов клиентов — прозрачные возможности и границы демо.",
    factCoverage:
      "7 из 20 регионов представлены в предоставленных исторических данных",
    factCoverageNote: "Полный манифест источников ещё не утверждён",
    factControlValue: "Решает человек",
    factLanguages: "Вопросы к аналитике на русском и казахском",
    factControl: "Маршрутизацию и действия подтверждает человек",
    factExports: "PDF и XLSX среза показанного результата",
    factForecast: "Прогноз только при достаточной достоверной истории",
    architectureKicker: "Федеративная архитектура",
    architectureTitle: "Слой помощи поверх региональных систем.",
    architectureText:
      "Pulse 109 поддерживает существующий процесс и не заменяет региональную CRM. Контракты и адаптеры задают путь подключения, когда появится подтверждённый источник.",
    sourceSystem: "Региональная система",
    pulseCore: "Канонический слой Pulse",
    adapters: "Изолированный адаптер",
    noLiveCrm: "В демо нет подключённой региональной CRM",
    openApi: "OpenAPI и JSON Schema",
    auditable: "Аудит и происхождение данных",
    faqKicker: "Границы возможностей видны сразу",
    faqTitle: "Частые вопросы",
    faqLiveQ: "Демо подключено к реальной системе 109?",
    faqLiveA:
      "Нет. Демо использует синтетические обращения и детерминированный replay-адаптер. Реальная CRM не подключена.",
    faqSyntheticQ: "Что в демо настоящее?",
    faqSyntheticA:
      "API, PostgreSQL, миграции, рабочие процессы, аудит и worker реальны. Обращения, demo-идентичности, каталог и delivery receipts синтетические.",
    faqAiQ: "Что AI решает сам?",
    faqAiA:
      "Система не выполняет значимые действия автоматически. Подсказки носят рекомендательный характер; оператор подтверждает маршрутизацию и действия с инцидентами.",
    faqPrivacyQ: "Как обрабатываются персональные данные?",
    faqPrivacyA:
      "Демо содержит синтетические записи. Правовое основание, сроки хранения и производственная идентификация требуют решения владельца системы до реального запуска.",
    faqForecastQ: "Всегда ли доступен прогноз?",
    faqForecastA:
      "Нет. Прогноз возможен на один, два или три месяца только при достаточной непрерывной истории с достоверным временем. Иначе система показывает, что данных недостаточно.",
    finalTitle: "От сигналов жителей — к понятным действиям города.",
    finalText: "Откройте интерактивное демо на синтетических данных.",
    footerNote:
      "Синтетические муниципальные данные · региональная CRM не подключена",
    skip: "Перейти к содержимому",
  },
  kk: {
    navProduct: "Өнім",
    navArchitecture: "Архитектура",
    navDemo: "Демо",
    heroKicker: "Pulse 109 · қалалық операциялар",
    language: "Бет тілі",
    heroTitleEditorial: "Intelligence for",
    heroTitleSystem: "every city signal.",
    heroText:
      "Тұрғындардың өтініштерін түсінікті әрекеттерге, байланысқан оқиғаларға және ерте операциялық белгілерге айналдырыңыз.",
    openDemo: "Open Interactive Demo",
    howItWorks: "Қалай жұмыс істейді",
    synthetic: "Синтетикалық мысал",
    opsTitle: "Операциялық орталық",
    arrivals: "Тәуліктегі өтініштер",
    attention: "Назар аудару керек",
    emerging: "Ұқсас өтініштер көбейді",
    reports: "өтініш",
    incidents: "оқиғалар",
    intake: "Ақылды қабылдау",
    intakeText:
      "Өтініш мәнмәтінін жинап, операторға тексеруге болатын түсінікті ұсыныс беріңіз.",
    assistant: "Оператор көмекшісі",
    assistantText:
      "Ұқсас белгілерді байланыстырып, келесі қадамды ұсыныңыз. Шешімді адам қабылдайды.",
    situation: "Ситуациялық орталық",
    situationText:
      "Өтініштерді, оқиғаларды және операциялық өзгерістерді бір жұмыс кеңістігінде бақылаңыз.",
    proposed: "Тексеруге ұсынылды",
    confirmed: "Оператор растайды",
    nextAction: "Келесі әрекет",
    inspect: "Байланысты өтініштерді тексеру",
    advisory: "Ұсыныс қана, автоматты шешім емес",
    workflowKicker: "Оператордың байланысқан жұмыс процесі",
    workflowTitle: "Өтініштен — қаланың жауабына дейін.",
    workflowIntro:
      "Бір жұмыс жолы өтінішті қабылдауды, оператор шешімін және қалалық жағдайға жауапты байланыстырады.",
    stepIntake: "Өтініш келді",
    stepReview: "Оператор тексерді",
    stepResponse: "Команда әрекет етеді",
    askKicker: "Ask Pulse · дереккөзі тексерілетін аналитика",
    askTitle: "Жағдай туралы сұраңыз. Әр жауапты тексеріңіз.",
    askText:
      "Ask Pulse рұқсат етілген метрикалар бойынша жауап беріп, дереккөз бен шектеулерді көрсетеді және дерекке өтуге мүмкіндік береді.",
    askQuestion: "Соңғы 7 күндегі өтініштер саны қалай өзгерді?",
    result: "Нақты динамика",
    resultTotal: "142 өтініш",
    sampleTotal: "Синтетикалық мысалдағы өтініштер",
    provenance: "Қалай есептелді",
    trustedTime: "Түсу уақыты сенімді жазбалар пайдаланылды",
    excluded: "Уақыты белгісіз жазбалар графиктен тыс қалады",
    drilldown: "Өтініштерді көру",
    export: "PDF / XLSX",
    forecast: "1–3 айлық болжам тек жеткілікті тарих болғанда қолжетімді.",
    incidentKicker: "Өтініштерден — расталған оқиғаға",
    manyTitle:
      "109 өтініштерді алады. Pulse ортақ оқиғаны байқауға көмектеседі.",
    manyText:
      "Жүйе ұқсас белгілерді табады. Оператор топты тексеріп, оқиға ашу туралы өзі шешім қабылдайды.",
    appeal: "Өтініш",
    cluster: "Тексерілетін топ",
    human: "Оператор шешімі",
    incident: "Оқиға",
    noAuto: "Автоматты біріктірусіз",
    factsTitle: "109 жұмысына сай жасалған.",
    factsIntro:
      "Клиент логотиптерінің орнына — мүмкіндіктер мен демо шектеулері ашық көрсетіледі.",
    factCoverage: "Берілген тарихи деректерде 20 өңірдің 7-еуі бар",
    factCoverageNote: "Дереккөздердің толық манифесті әлі бекітілмеген",
    factControlValue: "Шешімді адам қабылдайды",
    factLanguages: "Орыс және қазақ тіліндегі аналитикалық сұрақтар",
    factControl: "Бағыттау мен әрекеттерді адам растайды",
    factExports: "Көрсетілген нәтижені PDF және XLSX түрінде шығару",
    factForecast: "Болжам тек жеткілікті сенімді тарих болғанда беріледі",
    architectureKicker: "Федеративті архитектура",
    architectureTitle: "Өңірлік жүйелерге арналған көмек қабаты.",
    architectureText:
      "Pulse 109 бар жұмыс процесін қолдайды және өңірлік CRM-ді алмастырмайды. Келісілген дереккөз пайда болғанда қосылу жолын келісімшарттар мен адаптерлер анықтайды.",
    sourceSystem: "Өңірлік жүйе",
    pulseCore: "Pulse канондық қабаты",
    adapters: "Оқшауланған адаптер",
    noLiveCrm: "Демода өңірлік CRM қосылмаған",
    openApi: "OpenAPI және JSON Schema",
    auditable: "Аудит және дерек шығу тегі",
    faqKicker: "Мүмкіндіктер шегі ашық көрсетіледі",
    faqTitle: "Жиі қойылатын сұрақтар",
    faqLiveQ: "Демо нақты 109 жүйесіне қосылған ба?",
    faqLiveA:
      "Жоқ. Демо синтетикалық өтініштер мен детерминделген replay адаптерін пайдаланады. Нақты CRM қосылмаған.",
    faqSyntheticQ: "Демода не нақты?",
    faqSyntheticA:
      "API, PostgreSQL, миграциялар, жұмыс ағындары, аудит және worker нақты. Өтініштер, демо сәйкестендірулері, каталог және жеткізу түбіртектері синтетикалық.",
    faqAiQ: "AI өздігінен нені шешеді?",
    faqAiA:
      "Маңызды ештеңені автоматты түрде шешпейді. Ұсыныстар кеңес ретінде беріледі; бағыттау мен оқиға әрекеттерін оператор растайды.",
    faqPrivacyQ: "Дербес деректер қалай өңделеді?",
    faqPrivacyA:
      "Демода синтетикалық жазбалар қолданылады. Нақты іске қосу алдында жүйе иесі құқықтық негізді, сақтау мерзімін және өндірістік сәйкестендіруді бекітуі керек.",
    faqForecastQ: "Болжам әрдайым қолжетімді ме?",
    faqForecastA:
      "Жоқ. Бір, екі немесе үш айлық болжам тек сенімді уақыты бар жеткілікті үздіксіз тарих болғанда жасалады. Әйтпесе дерек жеткіліксіз екені көрсетіледі.",
    finalTitle: "Тұрғындар сигналынан — қаланың нақты әрекеттеріне.",
    finalText: "Синтетикалық деректердегі интерактивті демоны ашыңыз.",
    footerNote: "Синтетикалық муниципалдық деректер · өңірлік CRM қосылмаған",
    skip: "Мазмұнға өту",
  },
} as const;

export function LandingPage() {
  const [locale, setLocale] = useState<Locale>("ru");
  const t = copy[locale];

  return (
    <div className={styles.landing}>
      <a className={styles.skipLink} href="#main">
        {t.skip}
      </a>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <a className={styles.brand} href="#top" aria-label="Pulse 109">
            <span className={styles.brandMark} aria-hidden="true">
              <span className={styles.brandMarkHex}>P</span>
            </span>
            <span>Pulse 109</span>
          </a>
          <nav className={styles.nav} aria-label={t.navProduct}>
            <a href="#product">{t.navProduct}</a>
            <a href="#architecture">{t.navArchitecture}</a>
            <a href="#demo">{t.navDemo}</a>
          </nav>
          <div className={styles.headerActions}>
            <div
              className={styles.localeSwitch}
              role="group"
              aria-label={t.language}
            >
              {(["ru", "kk"] as const).map((item) => (
                <button
                  key={item}
                  type="button"
                  aria-pressed={locale === item}
                  onClick={() => setLocale(item)}
                >
                  {item.toUpperCase()}
                </button>
              ))}
            </div>
            <Link className={styles.headerCta} href="/demo">
              {t.openDemo}
              <ArrowUpRight aria-hidden="true" size={15} />
            </Link>
          </div>
        </div>
      </header>

      <main id="main">
        <section className={styles.hero} id="top">
          <div className={styles.heroCopy}>
            <div className={styles.kickerBadge}>
              <span className={styles.kickerBadgeDot} aria-hidden="true" />
              {t.heroKicker}
            </div>
            <h1>
              <span className={styles.editorialHeadline}>
                {t.heroTitleEditorial}
              </span>
              <span className={styles.systemHeadline}>{t.heroTitleSystem}</span>
            </h1>
            <p className={styles.heroText}>{t.heroText}</p>
            <div className={styles.heroActions}>
              <Link className={styles.primaryButton} href="/demo">
                {t.openDemo}
                <ArrowRight aria-hidden="true" size={16} />
              </Link>
              <a className={styles.textButton} href="#product">
                {t.howItWorks}
                <ArrowDown aria-hidden="true" size={14} />
              </a>
            </div>
            <div className={styles.heroNote}>
              <span className={styles.kickerBadgeDot} aria-hidden="true" />
              <span>{t.footerNote}</span>
            </div>
          </div>

          <ProductStage t={t} />
        </section>

        <section className={styles.factsBar} aria-label={t.factsTitle}>
          <Fact
            icon={<MapPinned aria-hidden="true" />}
            value="7 / 20"
            text={t.factCoverage}
            note={t.factCoverageNote}
          />
          <Fact
            icon={<Network aria-hidden="true" />}
            value="RU + KK"
            text={t.factLanguages}
          />
          <Fact
            icon={<ShieldCheck aria-hidden="true" />}
            value={t.factControlValue}
            text={t.factControl}
          />
          <Fact
            icon={<FileDown aria-hidden="true" />}
            value="PDF + XLSX"
            text={t.factExports}
          />
        </section>

        <section className={styles.workflowSection} id="product">
          <div className={styles.sectionHeading}>
            <p className={styles.kicker}>{t.workflowKicker}</p>
            <h2>{t.workflowTitle}</h2>
            <p>{t.workflowIntro}</p>
          </div>
          <div className={styles.moduleGrid}>
            <ModuleCard
              index="01"
              title={t.intake}
              description={t.intakeText}
              t={t}
              kind="intake"
            />
            <ModuleCard
              index="02"
              title={t.assistant}
              description={t.assistantText}
              t={t}
              kind="assistant"
            />
            <ModuleCard
              index="03"
              title={t.situation}
              description={t.situationText}
              t={t}
              kind="situation"
            />
          </div>
        </section>

        <section className={styles.askSection}>
          <div className={styles.askCopy}>
            <p className={styles.kicker}>{t.askKicker}</p>
            <h2>{t.askTitle}</h2>
            <p>{t.askText}</p>
            <ul className={styles.checkList}>
              <li>
                <Check aria-hidden="true" />
                {t.provenance}
              </li>
              <li>
                <Check aria-hidden="true" />
                {t.drilldown}
              </li>
              <li>
                <Check aria-hidden="true" />
                {t.export}
              </li>
            </ul>
            <p className={styles.forecastNote}>{t.forecast}</p>
          </div>
          <AskPreview t={t} />
        </section>

        <section className={styles.incidentSection}>
          <div className={styles.incidentCopy}>
            <p className={styles.kicker}>{t.incidentKicker}</p>
            <h2>{t.manyTitle}</h2>
            <p>{t.manyText}</p>
            <p className={styles.guardrail}>
              <ShieldCheck aria-hidden="true" />
              {t.noAuto}
            </p>
          </div>
          <IncidentFlow t={t} />
        </section>

        <section className={styles.architectureSection} id="architecture">
          <div className={styles.architectureCopy}>
            <p className={styles.kicker}>{t.architectureKicker}</p>
            <h2>{t.architectureTitle}</h2>
            <p>{t.architectureText}</p>
            <div className={styles.architectureFacts}>
              <span>
                <Check aria-hidden="true" />
                {t.openApi}
              </span>
              <span>
                <Check aria-hidden="true" />
                {t.auditable}
              </span>
              <span className={styles.noLive}>
                <CircleHelp aria-hidden="true" />
                {t.noLiveCrm}
              </span>
            </div>
          </div>
          <div
            className={styles.architectureDiagram}
            aria-label={t.architectureTitle}
          >
            <div className={styles.architectureNode}>
              <span className={styles.nodeIcon}>
                <Workflow aria-hidden="true" />
              </span>
              <span>{t.sourceSystem}</span>
            </div>
            <span className={styles.connector} aria-hidden="true">
              <ArrowRight />
            </span>
            <div className={`${styles.architectureNode} ${styles.pulseNode}`}>
              <span className={styles.nodeIcon}>
                <span className={styles.brandMarkSmall}>P</span>
              </span>
              <span>{t.pulseCore}</span>
            </div>
            <span className={styles.connector} aria-hidden="true">
              <ArrowRight />
            </span>
            <div className={styles.architectureNode}>
              <span className={styles.nodeIcon}>
                <Network aria-hidden="true" />
              </span>
              <span>{t.adapters}</span>
            </div>
          </div>
        </section>

        <section className={styles.faqSection}>
          <div className={styles.faqHeading}>
            <p className={styles.kicker}>{t.faqKicker}</p>
            <h2>{t.faqTitle}</h2>
          </div>
          <div className={styles.faqList}>
            <Faq question={t.faqLiveQ} answer={t.faqLiveA} />
            <Faq question={t.faqSyntheticQ} answer={t.faqSyntheticA} />
            <Faq question={t.faqAiQ} answer={t.faqAiA} />
            <Faq question={t.faqForecastQ} answer={t.faqForecastA} />
            <Faq question={t.faqPrivacyQ} answer={t.faqPrivacyA} />
          </div>
        </section>

        <section className={styles.finalCta} id="demo">
          <div>
            <p className={styles.kicker}>Pulse 109</p>
            <h2>{t.finalTitle}</h2>
            <p>{t.finalText}</p>
          </div>
          <Link className={styles.primaryButton} href="/demo">
            {t.openDemo}
            <ArrowRight aria-hidden="true" size={17} />
          </Link>
        </section>
      </main>

      <footer className={styles.footer}>
        <a className={styles.brand} href="#top">
          <span className={styles.brandMark} aria-hidden="true">
            <span className={styles.brandMarkHex}>P</span>
          </span>
          <span>Pulse 109</span>
        </a>
        <p>{t.footerNote}</p>
        <a href="#top" className={styles.backTop}>
          Back to top ↑
        </a>
      </footer>
    </div>
  );
}

type Copy = (typeof copy)[Locale];

function ProductStage({ t }: { t: Copy }) {
  return (
    <div className={styles.productStage} aria-label={t.synthetic}>
      <article className={styles.operationsWindow}>
        <span className={`${styles.bentoCross} ${styles.bentoCrossTopLeft}`} aria-hidden="true">+</span>
        <span className={`${styles.bentoCross} ${styles.bentoCrossTopRight}`} aria-hidden="true">+</span>
        <span className={`${styles.bentoCross} ${styles.bentoCrossBottomLeft}`} aria-hidden="true">+</span>
        <span className={`${styles.bentoCross} ${styles.bentoCrossBottomRight}`} aria-hidden="true">+</span>
        
        <header className={styles.windowTopbar}>
          <div className={styles.windowBrand}>
            <span className={styles.brandMarkSmall}>P</span> Pulse 109 · Core
          </div>
          <div className={styles.windowPills}>
            <span>ALA</span>
            <span className={styles.syntheticTag}>{t.synthetic}</span>
          </div>
        </header>
        <div className={styles.windowLayout}>
          <nav className={styles.previewNav} aria-label={t.opsTitle}>
            <span className={styles.navActive}>
              <i />
              {t.opsTitle}
            </span>
            <span>
              <i />
              {t.incident}
            </span>
            <span>
              <i />
              {t.intake}
            </span>
            <span>
              <i />
              Data Lab
            </span>
          </nav>
          <div className={styles.previewContent}>
            <div className={styles.previewHeading}>
              <div>
                <span className={styles.previewKicker}>City pulse · Operations</span>
                <h3>{t.opsTitle}</h3>
              </div>
              <span className={styles.liveDot}>DEMO PIPELINE</span>
            </div>
            <div className={styles.previewMetrics}>
              <Metric label={t.reports} value="148" />
              <Metric label={t.incidents} value="06" />
              <Metric label={t.attention} value="03" />
            </div>
            <div className={styles.previewChartCard}>
              <div className={styles.previewCardHeading}>
                <strong>{t.arrivals}</strong>
                <span>{t.synthetic} · 24h</span>
              </div>
              <ArrivalChart
                buckets={arrivals}
                baseline={4}
                peakStart={arrivals[arrivals.length - 1].start}
                excluded={0}
                excludedLabel={t.excluded}
                emptyLabel="—"
                description={t.arrivals}
              />
            </div>
            <div className={styles.previewAttention}>
              <strong>{t.attention}</strong>
              <div>
                <span className={styles.severityMarker} />
                {t.emerging}
                <span className={styles.rowCount}>06</span>
              </div>
            </div>
          </div>
        </div>
      </article>

      <div className={styles.heroBentoCol}>
        <article className={styles.bentoCard}>
          <span className={`${styles.bentoCross} ${styles.bentoCrossTopLeft}`} aria-hidden="true">+</span>
          <span className={`${styles.bentoCross} ${styles.bentoCrossTopRight}`} aria-hidden="true">+</span>
          <div className={styles.floatingHeading}>
            <span>Ask Pulse · Studio</span>
            <span className={styles.syntheticTag}>{t.synthetic}</span>
          </div>
          <div className={styles.askPrompt}>
            <span>⌕</span>
            {t.askQuestion}
          </div>
          <div className={styles.askMiniResult}>
            <strong>142</strong>
            <span>{t.result}</span>
            <MiniLine />
          </div>
        </article>

        <article className={styles.bentoCard}>
          <span className={`${styles.bentoCross} ${styles.bentoCrossBottomLeft}`} aria-hidden="true">+</span>
          <span className={`${styles.bentoCross} ${styles.bentoCrossBottomRight}`} aria-hidden="true">+</span>
          <div className={styles.warRoomLabel}>
            <span className={styles.severityMarker} />
            {t.incident} · elevated signal
          </div>
          <h3>{t.emerging}</h3>
          <div className={styles.memberDots} aria-hidden="true">
            <i />
            <i />
            <i />
            <i />
            <i />
            <i />
          </div>
          <div className={styles.warRoomFooter}>
            <span>06 {t.reports}</span>
            <span className={styles.operatorCheck}>
              <ShieldCheck size={14} aria-hidden="true" />
              {t.confirmed}
            </span>
          </div>
        </article>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.metric}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function MiniLine() {
  return (
    <svg className={styles.miniLine} viewBox="0 0 120 34" aria-hidden="true">
      <path d="M2 27 20 24 37 26 56 16 74 20 92 9 118 5" />
    </svg>
  );
}

function Fact({
  icon,
  value,
  text,
  note,
}: {
  icon: ReactNode;
  value: string;
  text: string;
  note?: string;
}) {
  return (
    <article className={styles.fact}>
      <span className={styles.factIcon}>{icon}</span>
      <div className={styles.factContent}>
        <strong>{value}</strong>
        <p>{text}</p>
        {note ? <small>{note}</small> : null}
      </div>
    </article>
  );
}

function ModuleCard({
  index,
  title,
  description,
  t,
  kind,
}: {
  index: string;
  title: string;
  description: string;
  t: Copy;
  kind: "intake" | "assistant" | "situation";
}) {
  return (
    <article className={styles.moduleCard}>
      <div className={styles.modulePreview} data-kind={kind}>
        <div className={styles.moduleToolbar}>
          <span className={styles.moduleDot} />
          <span />
          <span />
        </div>
        {kind === "intake" ? (
          <div className={styles.intakePreview}>
            <span className={styles.previewKicker}>{t.synthetic}</span>
            <div className={styles.intakeField}>
              <small>{t.appeal}</small>
              <strong>{t.emerging}</strong>
            </div>
            <div className={styles.proposalRow}>
              <span className={styles.proposalIcon}>
                <Workflow size={15} aria-hidden="true" />
              </span>
              <span>
                {t.proposed}
                <small>water_service · routine</small>
              </span>
            </div>
            <div className={styles.confirmRow}>
              <Check size={14} aria-hidden="true" />
              {t.confirmed}
            </div>
          </div>
        ) : null}
        {kind === "assistant" ? (
          <div className={styles.assistantPreview}>
            <div className={styles.relatedAppeals}>
              <span />
              <span />
              <span />
              <span />
              <span />
            </div>
            <div className={styles.actionSurface}>
              <small>{t.nextAction}</small>
              <strong>{t.inspect}</strong>
              <span>
                <ShieldCheck size={13} aria-hidden="true" />
                {t.advisory}
              </span>
            </div>
          </div>
        ) : null}
        {kind === "situation" ? (
          <div className={styles.situationPreview}>
            <div className={styles.situationMetric}>
              <span>{t.incidents}</span>
              <strong>06</strong>
              <i />
            </div>
            <div className={styles.situationMetric}>
              <span>{t.attention}</span>
              <strong>03</strong>
              <i />
            </div>
            <div className={styles.situationTimeline}>
              <span />
              <span />
              <span />
              <span />
            </div>
            <div className={styles.situationCaption}>{t.noAuto}</div>
          </div>
        ) : null}
      </div>
      <div className={styles.moduleText}>
        <span className={styles.moduleIndex}>{index}</span>
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </div>
    </article>
  );
}

function AskPreview({ t }: { t: Copy }) {
  return (
    <article className={styles.askPreview}>
      <div className={styles.askPreviewTop}>
        <div className={styles.askPreviewBrand}>
          <span className={styles.brandMarkSmall}>P</span>
          <strong>Ask Pulse</strong>
        </div>
        <span className={styles.syntheticTag}>{t.synthetic}</span>
      </div>
      <div className={styles.queryBar}>
        <span className={styles.searchIcon}>⌕</span>
        <span>{t.askQuestion}</span>
        <span className={styles.submitQuery}>
          <ArrowRight aria-hidden="true" />
        </span>
      </div>
      <div className={styles.queryResult}>
        <div className={styles.resultHeader}>
          <div>
            <small>{t.result}</small>
            <strong>{t.resultTotal}</strong>
          </div>
          <span className={styles.resultScope}>ALA · 7 days</span>
        </div>
        <ArrivalChart
          buckets={arrivals}
          baseline={4}
          peakStart={arrivals[arrivals.length - 1].start}
          excluded={3}
          excludedLabel={t.excluded}
          emptyLabel="—"
          description={t.askTitle}
        />
        <div className={styles.provenancePanel}>
          <div>
            <ShieldCheck aria-hidden="true" />
            <strong>{t.provenance}</strong>
            <span>appeals_volume / 2.0.0</span>
          </div>
          <p>
            {t.trustedTime}. {t.excluded}.
          </p>
        </div>
        <div className={styles.resultActions}>
          <button type="button" disabled>
            {t.drilldown}
          </button>
          <button type="button" disabled>
            {t.export}
          </button>
        </div>
      </div>
    </article>
  );
}

function IncidentFlow({ t }: { t: Copy }) {
  return (
    <div className={styles.incidentFlow} aria-label={t.manyTitle}>
      <div className={styles.appealList}>
        {[0, 1, 2, 3, 4, 5].map((index) => (
          <div className={styles.appealRow} key={index}>
            <span className={styles.appealDot} />
            <span>
              {t.appeal} {String(index + 1).padStart(2, "0")}
            </span>
            <small>water · {t.synthetic}</small>
          </div>
        ))}
      </div>
      <div className={styles.flowConnector}>
        <span />
        <span />
        <span />
        <span />
        <span />
        <span />
      </div>
      <div className={styles.flowDecision}>
        <div className={styles.flowSignal}>
          <Network aria-hidden="true" />
          <span>{t.cluster}</span>
          <strong>06</strong>
        </div>
        <ArrowRight className={styles.flowArrow} aria-hidden="true" />
        <div className={styles.flowIncident}>
          <ShieldCheck aria-hidden="true" />
          <span>{t.human}</span>
          <strong>{t.incident}</strong>
        </div>
      </div>
      <p className={styles.flowFootnote}>{t.noAuto}</p>
    </div>
  );
}

function Faq({ question, answer }: { question: string; answer: string }) {
  return (
    <details className={styles.faqItem}>
      <summary>
        <span>{question}</span>
        <ChevronDown aria-hidden="true" size={17} />
      </summary>
      <p>{answer}</p>
    </details>
  );
}
