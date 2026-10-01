[Русский](PILOT_DEPLOYMENT_REQUIREMENTS.md) · [English](PILOT_DEPLOYMENT_REQUIREMENTS.en.md) · [Қазақша](PILOT_DEPLOYMENT_REQUIREMENTS.kk.md)

# Требования к развёртыванию пилота

Это эксплуатационная инструкция с требованиями к production-пилоту. Отдельный [отчёт о публичном демо](PUBLIC_DEPLOYMENT.md) описывает проверенный VPS/домен/HTTPS стенд с синтетическими данными. Он не предоставляет операционного провайдера идентификации, утверждённого bucket, региональных credentials, RPO/RTO, срока хранения или измеренной production-производительности. Эти входные данные пилота остаются B07/B08/B10.

## Предварительные условия вне репозитория

- Целевая сеть и профиль хоста, DNS-имя и жизненный цикл TLS-сертификатов.
- PostgreSQL, object-storage и backup credentials вне системы контроля версий.
- Утверждённые OIDC issuer, audience и JWKS endpoint, а также mapping ролей и региональных claims. API принимает `roles`, `realm_access.roles` и `regions`, `region_ids` или `region_id`; каждый аутентифицированный запрос затем проверяется по роли и региону.
- Решение о privacy/правовом основании и сроках хранения до поступления любого несинтетического обращения или вложения в исполняемый контур.
- Названный региональный API sandbox и credentials до замены replay-доставки.

## Граница конфигурации

Задавайте утверждённые значения только через управление секретами развёртывания:

```dotenv
PULSE109_ENVIRONMENT=pilot
PULSE109_PROFILE=pilot
PULSE109_DATABASE_URL=<managed outside repository>
PULSE109_LOCAL_IDENTITY_ENABLED=false
PULSE109_OIDC_ISSUER=<approved issuer>
PULSE109_OIDC_AUDIENCE=<approved audience>
PULSE109_OIDC_JWKS_URL=<approved JWKS endpoint>
PULSE109_OIDC_ALGORITHMS=["RS256"]
PULSE109_APPROVED_LEGAL_BASIS=<approved value>
PULSE109_APPROVED_RETENTION_CLASS=<approved value>
```

`PULSE109_LOCAL_IDENTITY_ENABLED=false` обязателен вне local, test и demo профилей. При отсутствии OIDC конфигурации доступ закрывается с `identity_provider_not_configured`; при отсутствии bearer token возвращается `authentication_required`.

## Граница объектного хранилища

Вложения и replay snapshots выбирают локальную файловую систему или S3-compatible storage через `PULSE109_OBJECT_STORAGE_MODE`. Подключение к исполняемому контуру и адаптеры существуют. Проверенное публичное демо использует локальные volumes; частный S3-провайдер и его свойства устойчивости/доступа на этом стенде не проверены. Вложения уже сохраняют неизменяемые ссылки на объекты, SHA-256, медиаметаданные и ссылки на обращение-владельца в PostgreSQL. До принятия storage adapter он должен проверять write/read/restore хеши, сохранять неизменяемость объектов, никогда не журналировать их содержимое и иметь интеграционное покрытие с утверждённым провайдером. Существующий scanner — mock, не антивирус.

## Процедура релиза, отката и восстановления

1. Создайте изолированную pilot database и пространство имён object storage. Не используйте demo volumes или общую интеграционную базу.
2. Выполните `alembic -c services/core/alembic.ini upgrade head`; миграции только вперёд. Зафиксируйте image digest и migration head.
3. Запустите Compose services с pilot secrets. До допуска трафика требуйте PostgreSQL readiness в `/v1/health/ready`.
4. Выполните аутентифицированные smoke checks для разрешённого региона и проверьте, что запрос с запрещённой ролью/регионом возвращает `403`.
5. Перед каждым релизом сделайте одобренный оператором database backup и неизменяемый object manifest. Восстановите их в изолированной среде, проверьте хеши и выполните там smoke flow. Ни одно значение репозитория не задаёт цели резервного копирования.
6. Откатывайте application images только после подтверждения совместимости схемы. Не редактируйте и не обращайте применённую миграцию. Если форма данных должна измениться, используйте новую корректирующую миграцию вперёд.

## Критерии выхода

Локальный Compose и проверенное публичное PostgreSQL-демо показывают механизмы исполняемого контура на синтетических записях. Ни одно не доказывает готовность production-пилота. Для пилотного развёртывания нужны одобрение внешнего владельца и доказательства выполнения каждого условия выше.
