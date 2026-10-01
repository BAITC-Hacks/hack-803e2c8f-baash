[Русский](GOVTECH_BUSINESS_QUESTIONS.md) · [English](GOVTECH_BUSINESS_QUESTIONS.en.md) · [Қазақша](GOVTECH_BUSINESS_QUESTIONS.kk.md)

# Questions for GovTech organizers

The questions below identify decisions that cannot be inferred from sample data or a demo. Please give an owner, authoritative document, effective date and example for each answer. We can continue the isolated synthetic demonstration while answers are pending.

## EN

1. **Service boundary.** Which appeal types may Pulse 109 accept, and which must go directly to another channel? Who owns incorrect classification or handoff?
2. **Regional source of truth.** Which system joins the first pilot, who owns it, and what sandbox API, documentation, limits, retry rules and request/event IDs are authoritative?
3. **Lifecycle.** Which statuses and transitions are binding, who may change or revoke them, and how should unknown or contradictory updates enter review?
4. **Routing.** Where are the approved topic, service, organization and unit catalogs? Who publishes versions and effective dates?
5. **Priority and deadlines.** Which events start or stop an SLA clock, and how are holidays, missing dates, inter-agency transfers and priority changes handled? Who approves exceptions?
6. **Incidents and duplicates.** What evidence permits linking, splitting or merging appeals? Who confirms a change while each citizen retains an independent appeal and response right?
7. **Human decisions.** Which AI suggestions are permitted, which require an operator or supervisor, how is disagreement recorded and who is accountable for a citizen response?
8. **Personal data.** Who is the controller, and what legal basis, purposes, allowed fields, retention, deletion, attachment access and export rules apply? Which storage and malware scanner are approved?
9. **Identity and region scope.** Which identity provider and claims define roles, regions, access purpose and auditor actions? May one operator work across regions?
10. **Quality and release.** Which real labeled data and acceptance criteria govern recommendations, false duplicate proposals and safety? Who authorizes model activation?
11. **Resilience.** What RPO/RTO, regional outage recovery procedure, queue wait and manual-mode triggers are required?
12. **Final defence.** Confirm the recording/live-demo format and required actions. Synthetic appeals and replay delivery are visibly labelled; the public demo runs the real API/PostgreSQL stack.
13. **Source records.** Which immutable source identifier and record must accompany each appeal? How are source corrections represented without rewriting history?
14. **Jurisdiction.** Who approves territorial and authority boundaries between district, city and region? What happens when an address is incomplete or disputed?
15. **Delivery confirmation.** Which regional response means accepted, transient failure or final rejection? How long may retries continue, and who handles dead letters?
16. **Closure evidence.** Which photos, reports or replies can support closure, who verifies that evidence belongs to the appeal, and may one item support multiple appeals?
17. **Reopening.** Who may challenge a closure or reopen an appeal, and within what period? When does a recurrence become a new appeal linked to an earlier incident?
18. **Citizen notifications.** Which channels and response templates are approved, how are delivery and failure recorded, and what incident information may a citizen see?
19. **Observability and audit.** Which events, errors and deadlines must regional operators and auditors see? Which fields must never enter logs or metrics?
20. **Release accountability.** Who approves the pilot, signs regional configuration, halts integration during an incident and authorizes restoration of service?

## RU

1. **Границы сервиса.** Какие типы обращений Pulse 109 принимает, а какие обязан передать без обработки в другой канал? Кто отвечает за ошибочную классификацию и передачу?
2. **Региональный источник истины.** Какая система первой участвует в пилоте, кто её владелец, есть ли тестовый API, документация, лимиты, правила повторной доставки и идентификаторы обращений/событий?
3. **Жизненный цикл.** Какие статусы и переходы являются обязательными, кто может изменить или отменить статус, как обрабатывать неизвестное значение и противоречивые обновления?
4. **Маршрутизация.** Где утверждённые справочники тем, услуг, организаций и подразделений, кто публикует их версии и как фиксировать дату вступления в силу?
5. **Приоритет и сроки.** Какие события запускают и останавливают SLA, как учитываются выходные, неполная дата, перевод между органами и пересмотр приоритета? Кто утверждает исключения?
6. **Инциденты и дубликаты.** Какой уровень доказательств нужен, чтобы связать обращения с одним инцидентом, разделить или объединить группы? Кто подтверждает операцию и как сохраняется независимое право гражданина на ответ?
7. **Человеческое решение.** Какие действия ИИ допустимо предложить, какие требуют оператора/руководителя, как записывать несогласие и кто отвечает за отправленный гражданину ответ?
8. **Персональные данные.** Кто оператор данных, каковы правовое основание, цели, допустимые поля, срок хранения, удаление, доступ к вложениям и экспорт? Где будет одобренное хранилище и антивирусное сканирование?
9. **Идентификация и границы региона.** Какая система идентификации и какие claims задают роли, регион, цель доступа и действия аудитора? Может ли оператор работать с несколькими регионами?
10. **Качество и запуск.** Какие реальные размеченные данные и критерии допуска нужны для оценки рекомендаций, ложных дубликатов и рисков? Кто принимает решение о включении модели?
11. **Доступность.** Каковы целевые RPO/RTO, процедура восстановления после сбоя региональной системы, допустимая очередь ожидания и условия перехода в ручной режим?
12. **Финальная защита.** Подтвердите формат записи/живого показа и какие действия жюри должно видеть. Синтетические обращения и replay-доставка явно обозначены; публичный demo использует настоящие API/PostgreSQL.
13. **Исходные записи.** Какой идентификатор и неизменяемый источник должны сопровождать каждое обращение? Как исправлять ошибку в региональном источнике, не переписывая историю?
14. **Границы юрисдикции.** Кто утверждает карту территорий и полномочий между районом, городом и областью? Что делать, если адрес неполный или граница спорная?
15. **Подтверждение доставки.** Какой ответ региональной системы означает принятие, временный сбой или окончательный отказ? В течение какого времени допустимы повторы и кто разбирает dead letter?
16. **Закрытие и доказательства.** Какие типы фото, актов или ответов допустимы для закрытия, кто проверяет их принадлежность обращению, и может ли один материал подтверждать несколько обращений?
17. **Повторное открытие.** Кто и в какой срок может оспорить закрытие или открыть обращение снова? Когда повтор становится новым обращением, связанным с прежним инцидентом?
18. **Уведомления гражданину.** Какой канал и шаблон ответа разрешены, как фиксируются отправка и недоставка, и какая информация об инциденте может быть показана заявителю?
19. **Наблюдаемость и аудит.** Какие события, ошибки и сроки должны быть доступны региональному оператору и аудитору? Какие поля категорически нельзя писать в логи и метрики?
20. **Запуск и ответственность.** Кто утверждает пилот, подписывает региональную конфигурацию, останавливает интеграцию при инциденте и принимает решение о восстановлении обслуживания?
