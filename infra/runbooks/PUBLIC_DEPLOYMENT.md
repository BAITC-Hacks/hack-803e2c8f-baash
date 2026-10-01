# Публичное демо: размещение и эксплуатация

Текущая запись о развёртывании [лендинга](https://baash.govtech-kz.com/) и [рабочего пространства](https://baash.govtech-kz.com/demo), проверенная **1 октября 2026 года**. Стенд — `PULSE109_PROFILE=demo`: реальные FastAPI/PostgreSQL/migrations/audit/outbox/worker, синтетические записи ALA, демонстрационные учётные записи и синтетические квитанции replay-доставки. Региональная CRM и IdP не подключены; правовые основания и сроки хранения не согласованы. Это демонстрационный стенд.

## Проверенный стенд на общем сервере

| Параметр                                   | Проверенное состояние                                                                                                               |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| HTTPS                                      | Существующий proxy организаторов; свои Caddy/80/443 не запускаются                                                                  |
| Compose project / каталог                  | `pulse109-final` / `~/pulse109-final`                                                                                               |
| Overlay                                    | base + demo + behind-proxy + VPS-local `docker-compose.vps.yml`                                                                     |
| Web                                        | GHCR image `ghcr.io/baitc-hacks/pulse109-web:22d89e7`                                                                               |
| Web digest                                 | `sha256:60b1f83d318a0df90af5fecf403217bab171295760ac1ec22f4d6d8d863af8e2`                                                           |
| Proxy upstream                             | `127.0.0.1:8009` → Next.js 3000; порт хоста 3000 занят другим приложением                                                           |
| API                                        | `127.0.0.1:8080` → API 8080; доступ нужен для наполнения/проверок с хоста                                                           |
| PostgreSQL / worker / inference / adapters | Внутренняя сеть Docker; порты хоста не публикуются                                                                                  |
| Объектное хранилище                        | Тома `local`; S3 подключён в коде, частный bucket на этом VPS не проверен                                                           |
| Проверка                                   | Лендинг HTTP 200; web/API/БД готовы; семь постоянных сервисов здоровы                                                               |
| Restart                                    | Постоянные контейнеры `unless-stopped`; rootless Docker enabled, systemd Restart=always, Linger=yes; migrate — one-shot, restart=no |

Web собран через [publish-web workflow](../../.github/workflows/publish-web.yml), [успешный прогон](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36741389474). Поздние `41b6a1f`/`e494390` меняют документацию, поэтому README HEAD и тег web-образа различаются. Каждый новый main не развёртывается автоматически.

1 октября сайт давал 502: пользовательская служба Docker была штатно остановлена, контейнеры имели `restart=no`. Docker и стек восстановлены; политики перезапуска сохранены в VPS override. `OOMKilled=false`: нехватка RAM как причина этого сбоя не подтверждена. Неиспользуемый BuildKit cache и логи четырёх старых остановленных демо-контейнеров очищены, образы с тегами и тома сохранены. Квота при проверке — 4095M / soft 4096M / hard 5120M: запас до мягкого лимита почти отсутствует. Перед показом/обновлением нужен повторный контроль. Перезапуск не исправляет исчерпание диска или остановку внешнего proxy.

## Команды именно для этого стенда

Выполняйте команды в VPS-сессии владельца rootless Docker. Всегда передавайте `--env-file .env`: без него Compose при вложенной конфигурации может не найти обязательный пароль. Секреты не выводятся в журналы и не попадают в Git.

```bash
cd ~/pulse109-final
export DOCKER_HOST="unix:///run/user/$(id -u)/docker.sock"
compose=(docker compose --env-file .env -p pulse109-final
  -f infra/compose/docker-compose.yml
  -f infra/compose/docker-compose.demo.yml
  -f infra/compose/docker-compose.behind-proxy.yml
  -f docker-compose.vps.yml)

systemctl --user is-active docker
"${compose[@]}" ps -a
df -h
quota -s || true
docker system df
```

VPS override текущего стенда:

```yaml
services:
  web:
    restart: unless-stopped
    image: ghcr.io/baitc-hacks/pulse109-web:22d89e7
    ports: !override
      - "127.0.0.1:8009:3000"
  core-api:
    restart: unless-stopped
    image: pulse109-final-adapter-runtime:latest
    ports: !override
      - "127.0.0.1:8080:8080"
  worker:
    restart: unless-stopped
    image: pulse109-final-adapter-runtime:latest
  inference:
    restart: unless-stopped
    image: pulse109-final-adapter-runtime:latest
  open311-sandbox:
    restart: unless-stopped
    image: pulse109-final-adapter-runtime:latest
    environment:
      PYTHONPATH: /app/adapters/open311/src
  postgres:
    restart: unless-stopped
  adapter-runtime:
    restart: unless-stopped
```

Если daemon не запущен, восстановление без сборки:

```bash
systemctl --user start docker
"${compose[@]}" config --quiet
"${compose[@]}" up -d --no-build
curl -fsS http://127.0.0.1:8009/api/health
curl -fsS -H 'X-Region-Id: ALA' http://127.0.0.1:8080/v1/health/ready
```

С другого компьютера:

```bash
curl -fsS https://baash.govtech-kz.com/api/health
curl -fsS -H 'X-Region-Id: ALA' https://baash.govtech-kz.com/api/core/health/ready
```

Откройте лендинг и `/demo`, обновите страницу, проверьте сохранённое обращение, War Room и Replay Lab. Проверки доступности выше не доказывают свежесть Radar или работу частного S3.

## Golden World перед записью

На проверенном VPS есть **120 дней / 266 исторических обращений** на момент чтения 1 октября; общий объём меняется после действий. Шесть водных записей имеют `received_at` от 30 сентября и уже устарели для проверки свежести. Сохранённый кластер доступен как прошлый результат. Новое сканирование за шесть часов не обязано найти тот же кластер.

`seed` идемпотентен и сохраняет существующие даты. Локальные `scripts/demo_runtime.py prepare/verify/reset` управляют `pulse109-demo` и не обновляют `pulse109-final`. Обновление мира на VPS требует отдельного согласованного окна: резервная копия БД/выпуска и подготовка свежей фикстуры в правильном проекте. Не публикуйте endpoint сброса и не удаляйте тома ради обычной проверки доступности. В этом документационном проходе мир не обновлялся.

## Обновление и откат

Перед переключением: проверить квоту, создать резервную копию БД/манифеста объектов, записать digest текущих образов и проверить совместимость схемы. Web строится в GitHub Actions, публикуется с неизменяемым SHA-тегом и скачивается после успешного workflow. Для закрытого GHCR используйте токен с `read:packages` через `password-stdin` и временную конфигурацию авторизации Docker. Секрет не должен попасть в историю команд или репозиторий.

После скачивания кандидата замените тег web в VPS override, проверьте Compose и выполните `up -d --no-build web`. Затем проверьте доступность и браузерный сценарий. Образы backend обновляются отдельно с проверенными миграциями и контрактами. Откат сохраняет прежние образы и совместимую схему; применённые миграции не редактируются.

При нехватке квоты сначала изучите `docker system df` и именованные ресурсы. Неиспользуемый кэш сборки можно удалить командой `docker builder prune --all --force` внутри собственного rootless Docker. Не применяйте `docker system prune -a` на общем сервере; тома, чужие ресурсы и образы отката не относятся к кэшу сборки. Следите за ростом логов: политика перезапуска не задаёт их ротацию.

## Развёртывание на другом хосте

Эта секция описывает варианты, не состояние текущего VPS. Для нового хоста нужны DNS/TLS, Docker/Compose, квота/ёмкость, закрытое хранение секретов и заранее проверенные порты 80/443 и loopback.

- **Существующий HTTPS proxy:** base + demo + `docker-compose.behind-proxy.yml`, своё переопределение loopback-порта и соответствующий upstream. По умолчанию web-порт этого overlay — 3000; текущий стенд переопределяет его на 8009.
- **Отдельный хост без proxy:** base + demo + `docker-compose.public.yml` запускает Caddy. Только здесь занимают 80/443. Не используйте этот overlay на проверенном общем VPS.
- **Storage:** `PULSE109_OBJECT_STORAGE_MODE=local` сохраняет тома файловой системы; `s3` требует bucket/endpoint/region и учётные данные вне Git. Public overlay собирает S3 extra. Перед заявлением о частном S3 проверить запись → SHA/чтение → перезапуск → чтение → запрет анонимного доступа → восстановление.
- **Database:** `POSTGRES_PASSWORD` должен быть уникальным URL-safe секретом; migration/API/worker URLs выводятся из него. Для существующей БД изменение environment не меняет пароль роли само по себе.
- **Seed:** запускать против готового API соответствующего демонстрационного проекта; behind-proxy API обычно не публикуется, поэтому использовать внутренний процесс либо временную привязку к loopback. Не открывать API наружу ради seed.

Условия производственного пилота — [PILOT_DEPLOYMENT_REQUIREMENTS](PILOT_DEPLOYMENT_REQUIREMENTS.md). [BACKUP_RESTORE](BACKUP_RESTORE.md) задаёт процедуру, но не утверждённые RPO/RTO. [Golden Demo](../../docs/GOLDEN_DEMO.md) задаёт маршрут показа, [FEATURE_STATUS](../../docs/FEATURE_STATUS.md) — текущие границы. Демонстрационный scanner остаётся mock, B07/B08/B10 открыты.
