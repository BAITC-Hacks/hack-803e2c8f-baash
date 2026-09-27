# Questions for GovTech organizers / Вопросы организаторам GovTech

The questions below identify decisions that cannot be inferred from sample data or a demo. Please give an owner, authoritative document, effective date and example for each answer. We can continue the isolated synthetic demonstration while answers are pending.

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
12. **Mock Demo Day.** Подтвердите, что синтетические обращения, replay-адаптер и отсутствие презентации будут явно обозначены. Какие действия и ответы организаторы хотят увидеть в работающем интерфейсе?

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
12. **Mock Demo Day.** Please confirm that synthetic appeals, replay delivery and the no-presentation format should be visibly labelled. Which live UI actions and responses should organizers inspect?
