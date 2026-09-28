-- Synthetic demo catalog and adaptive-intake policies.
--
-- The adaptive intake module is implemented, but the demo database ships with an
-- empty catalog, so the citizen wizard could only report the feature as
-- unavailable. These rows give it something to resolve.
--
-- Every row sets synthetic_only, which the repository honours: these policies are
-- invisible outside the local, development, test and demo profiles. They are not
-- an official taxonomy. B06, the approved taxonomy and SLA, stays open.

BEGIN;

INSERT INTO catalog.topic_version (topic_id, version, effective_from, display_name, active, synthetic_only)
VALUES
  ('topic:water',     'synthetic-1.0.0', TIMESTAMPTZ '2026-01-01 00:00:00+00', '{"ru":"Водоснабжение","kk":"Сумен жабдықтау"}'::jsonb, TRUE, TRUE),
  ('topic:roads',     'synthetic-1.0.0', TIMESTAMPTZ '2026-01-01 00:00:00+00', '{"ru":"Дороги","kk":"Жолдар"}'::jsonb,                  TRUE, TRUE),
  ('topic:waste',     'synthetic-1.0.0', TIMESTAMPTZ '2026-01-01 00:00:00+00', '{"ru":"Вывоз отходов","kk":"Қалдықтарды шығару"}'::jsonb, TRUE, TRUE),
  ('topic:utilities', 'synthetic-1.0.0', TIMESTAMPTZ '2026-01-01 00:00:00+00', '{"ru":"Коммунальные услуги","kk":"Коммуналдық қызметтер"}'::jsonb, TRUE, TRUE)
ON CONFLICT (topic_id, version) DO NOTHING;

INSERT INTO catalog.service_version (service_id, region_id, version, effective_from, display_name, active, synthetic_only)
VALUES
  ('service:water',     'ALA', 'synthetic-1.0.0', TIMESTAMPTZ '2026-01-01 00:00:00+00', '{"ru":"Синтетический водоканал","kk":"Синтетикалық су арнасы"}'::jsonb, TRUE, TRUE),
  ('service:roads',     'ALA', 'synthetic-1.0.0', TIMESTAMPTZ '2026-01-01 00:00:00+00', '{"ru":"Синтетическая дорожная служба","kk":"Синтетикалық жол қызметі"}'::jsonb, TRUE, TRUE),
  ('service:waste',     'ALA', 'synthetic-1.0.0', TIMESTAMPTZ '2026-01-01 00:00:00+00', '{"ru":"Синтетический оператор отходов","kk":"Синтетикалық қалдық операторы"}'::jsonb, TRUE, TRUE),
  ('service:utilities', 'ALA', 'synthetic-1.0.0', TIMESTAMPTZ '2026-01-01 00:00:00+00', '{"ru":"Синтетическая коммунальная служба","kk":"Синтетикалық коммуналдық қызмет"}'::jsonb, TRUE, TRUE)
ON CONFLICT (service_id, region_id, version) DO NOTHING;

-- description and location arrive from the wizard as known, so they never produce a
-- question. The remaining fields are unknown at that point and become the plan.
-- photo_evidence is conditional on location being known, which exercises the
-- conditional branch of the policy engine during the walkthrough.
INSERT INTO intake.policy_version (
  region_id, service_id, service_version, topic_id, topic_version, version, state,
  effective_from, required_fields, source_ref, created_by_token, reviewed_by_token,
  approval_ref, synthetic_only
)
VALUES
  ('ALA', 'service:water', 'synthetic-1.0.0', 'topic:water', 'synthetic-1.0.0', 'synthetic-1.0.0', 'approved',
   TIMESTAMPTZ '2026-01-01 00:00:00+00',
   '[
     {"field_id":"description","questions":{"ru":"Опишите проблему.","kk":"Мәселені сипаттаңыз."}},
     {"field_id":"location","questions":{"ru":"Укажите адрес или ориентир.","kk":"Мекенжайды немесе бағдарды көрсетіңіз."}},
     {"field_id":"leak_scope","questions":{"ru":"Вода течёт на улице или внутри дома?","kk":"Су көшеде ме, әлде үй ішінде ме ағып жатыр?"}},
     {"field_id":"supply_state","questions":{"ru":"Есть ли сейчас вода в кране?","kk":"Қазір шүмекте су бар ма?"}},
     {"field_id":"photo_evidence","questions":{"ru":"Приложите фото места течи, если это безопасно.","kk":"Қауіпсіз болса, ағу орнының фотосын тіркеңіз."},"when_states":{"location":"known"},"evidence_type":"photo"}
   ]'::jsonb,
   'SYNTHETIC_DEMO_POLICY', 'synthetic-demo-author', 'synthetic-demo-reviewer', 'SYNTHETIC_DEMO_ONLY', TRUE),

  ('ALA', 'service:roads', 'synthetic-1.0.0', 'topic:roads', 'synthetic-1.0.0', 'synthetic-1.0.0', 'approved',
   TIMESTAMPTZ '2026-01-01 00:00:00+00',
   '[
     {"field_id":"description","questions":{"ru":"Опишите проблему.","kk":"Мәселені сипаттаңыз."}},
     {"field_id":"location","questions":{"ru":"Укажите адрес или ориентир.","kk":"Мекенжайды немесе бағдарды көрсетіңіз."}},
     {"field_id":"defect_size","questions":{"ru":"Насколько велика выбоина: меньше или больше колеса?","kk":"Шұңқыр дөңгелектен кіші ме, үлкен бе?"}},
     {"field_id":"traffic_risk","questions":{"ru":"Мешает ли это проезду или проходу людей?","kk":"Бұл көлік немесе жаяу жүргіншілерге кедергі ме?"}},
     {"field_id":"photo_evidence","questions":{"ru":"Приложите фото участка, если это безопасно.","kk":"Қауіпсіз болса, учаскенің фотосын тіркеңіз."},"when_states":{"location":"known"},"evidence_type":"photo"}
   ]'::jsonb,
   'SYNTHETIC_DEMO_POLICY', 'synthetic-demo-author', 'synthetic-demo-reviewer', 'SYNTHETIC_DEMO_ONLY', TRUE),

  ('ALA', 'service:waste', 'synthetic-1.0.0', 'topic:waste', 'synthetic-1.0.0', 'synthetic-1.0.0', 'approved',
   TIMESTAMPTZ '2026-01-01 00:00:00+00',
   '[
     {"field_id":"description","questions":{"ru":"Опишите проблему.","kk":"Мәселені сипаттаңыз."}},
     {"field_id":"location","questions":{"ru":"Укажите адрес или ориентир.","kk":"Мекенжайды немесе бағдарды көрсетіңіз."}},
     {"field_id":"container_state","questions":{"ru":"Контейнеры переполнены или повреждены?","kk":"Контейнерлер толып кеткен бе, әлде бүлінген бе?"}},
     {"field_id":"last_pickup","questions":{"ru":"Когда мусор вывозили в последний раз, по вашей памяти?","kk":"Қоқыс соңғы рет қашан шығарылды?"}},
     {"field_id":"photo_evidence","questions":{"ru":"Приложите фото площадки, если это безопасно.","kk":"Қауіпсіз болса, алаңның фотосын тіркеңіз."},"when_states":{"location":"known"},"evidence_type":"photo"}
   ]'::jsonb,
   'SYNTHETIC_DEMO_POLICY', 'synthetic-demo-author', 'synthetic-demo-reviewer', 'SYNTHETIC_DEMO_ONLY', TRUE),

  ('ALA', 'service:utilities', 'synthetic-1.0.0', 'topic:utilities', 'synthetic-1.0.0', 'synthetic-1.0.0', 'approved',
   TIMESTAMPTZ '2026-01-01 00:00:00+00',
   '[
     {"field_id":"description","questions":{"ru":"Опишите проблему.","kk":"Мәселені сипаттаңыз."}},
     {"field_id":"location","questions":{"ru":"Укажите адрес или ориентир.","kk":"Мекенжайды немесе бағдарды көрсетіңіз."}},
     {"field_id":"outage_scope","questions":{"ru":"Проблема в одной квартире или во всём доме?","kk":"Мәселе бір пәтерде ме, әлде бүкіл үйде ме?"}},
     {"field_id":"since_when","questions":{"ru":"Как давно это продолжается: сегодня, несколько дней или дольше?","kk":"Бұл қашаннан бері: бүгін бе, бірнеше күн бе, одан ұзақ па?"}},
     {"field_id":"photo_evidence","questions":{"ru":"Приложите фото, если это безопасно.","kk":"Қауіпсіз болса, фото тіркеңіз."},"when_states":{"location":"known"},"evidence_type":"photo"}
   ]'::jsonb,
   'SYNTHETIC_DEMO_POLICY', 'synthetic-demo-author', 'synthetic-demo-reviewer', 'SYNTHETIC_DEMO_ONLY', TRUE)
ON CONFLICT (region_id, service_id, topic_id, version) DO NOTHING;

-- Synthetic natural-language aliases reference existing canonical entities only.
-- The pilot supplies reviewed aliases with approval references; no official
-- regional manifest or taxonomy is created by these demonstration rows.
INSERT INTO analytics.intent_alias
    (entity_type,entity_id,alias,version,effective_from,synthetic_only,approval_ref)
VALUES
    ('topic','topic:water','вода','synthetic-1.0.0',TIMESTAMPTZ '2026-01-01 00:00:00+00',TRUE,'SYNTHETIC_DEMO_ONLY'),
    ('topic','topic:water','су','synthetic-1.0.0',TIMESTAMPTZ '2026-01-01 00:00:00+00',TRUE,'SYNTHETIC_DEMO_ONLY'),
    ('topic','topic:roads','дороги','synthetic-1.0.0',TIMESTAMPTZ '2026-01-01 00:00:00+00',TRUE,'SYNTHETIC_DEMO_ONLY'),
    ('topic','topic:roads','жол','synthetic-1.0.0',TIMESTAMPTZ '2026-01-01 00:00:00+00',TRUE,'SYNTHETIC_DEMO_ONLY')
ON CONFLICT DO NOTHING;

COMMIT;
