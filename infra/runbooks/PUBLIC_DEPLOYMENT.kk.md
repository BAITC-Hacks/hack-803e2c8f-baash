[Русский](PUBLIC_DEPLOYMENT.md) · [English](PUBLIC_DEPLOYMENT.en.md) · [Қазақша](PUBLIC_DEPLOYMENT.kk.md)

# Қоғамдық демо: орналастыру және пайдалану

[Лендингті](https://baash.govtech-kz.com/) және [оператордың жұмыс кеңістігін](https://baash.govtech-kz.com/demo) орналастыру туралы ағымдағы жазба, **2026 жылғы 1 қазанда** тексерілген. Стенд — `PULSE109_PROFILE=demo`: нақты FastAPI/PostgreSQL/migrations/audit/outbox/worker, ALA синтетикалық жазбалары, демонстрациялық тіркелгілер және replay-жеткізудің синтетикалық түбіртектері. Өңірлік CRM және IdP қосылмаған; құқықтық негіздер мен сақтау мерзімдері келісілмеген. Бұл демонстрациялық стенд.

## Ортақ сервердегі тексерілген стенд

| Параметр                                   | Тексерілген күй                                                                                                                     |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| HTTPS                                      | Ұйымдастырушылардың қолданыстағы proxy-і; жеке Caddy/80/443 іске қосылмайды                                                         |
| Compose project / каталог                  | `pulse109-final` / `~/pulse109-final`                                                                                               |
| Overlay                                    | base + demo + behind-proxy + VPS-local `docker-compose.vps.yml`                                                                     |
| Web                                        | GHCR image `ghcr.io/baitc-hacks/pulse109-web:22d89e7`                                                                               |
| Web digest                                 | `sha256:60b1f83d318a0df90af5fecf403217bab171295760ac1ec22f4d6d8d863af8e2`                                                           |
| Proxy upstream                             | `127.0.0.1:8009` → Next.js 3000; хосттың 3000 порты басқа қолданбамен бос емес                                                     |
| API                                        | `127.0.0.1:8080` → API 8080; қолжетімділік хосттан толтыру/тексеру үшін қажет                                                       |
| PostgreSQL / worker / inference / adapters | Docker-дің ішкі желісі; хост порттары жарияланбайды                                                                                 |
| Объектілік қойма                           | `local` томдары; S3 кодта қосылған, осы VPS-тегі жеке bucket тексерілмеген                                                           |
| Тексеру                                    | Лендинг HTTP 200; web/API/ДҚ дайын; жеті тұрақты қызмет сау                                                                         |
| Restart                                    | Тұрақты контейнерлер `unless-stopped`; rootless Docker қосулы, systemd Restart=always, Linger=yes; migrate — one-shot, restart=no   |

Web [publish-web workflow](../../.github/workflows/publish-web.yml) арқылы жинақталған, [сәтті іске қосылу](https://github.com/BAITC-Hacks/hack-803e2c8f-baash/actions/runs/36741389474). Кейінгі `41b6a1f`/`e494390` құжаттаманы өзгертеді, сондықтан README HEAD пен web-образ тегі ерекшеленеді. Әрбір жаңа main автоматты түрде орналастырылмайды.

1 қазанда сайт 502 қатесін берді: пайдаланушының Docker қызметі штаттық түрде тоқтатылған, контейнерлерде `restart=no` болған. Docker мен стек қалпына келтірілді; қайта іске қосу саясаттары VPS override ішінде сақталды. `OOMKilled=false`: RAM жетіспеушілігі осы ақаудың себебі ретінде расталмады. Пайдаланылмаған BuildKit кэші мен төрт ескі тоқтатылған демо-контейнердің логтары тазартылды, тегі бар образдар мен томдар сақталды. Stabilization кейін квота — 4083M / soft 4096M / hard 5120M. Ескі жүктеу архиві SHA тексеруімен жұмыс станциясында сақталды, оның көшірмесі VPS-тен жойылды. Жұмсақ лимитке дейінгі қор шамамен 13M құрайды; жаңа image rollout үшін сыйымдылықты бөлек тексеру қажет. Көрсетілім/жаңарту алдында қайта бақылау жүргізу қажет. Қайта іске қосу дискінің таусылуын немесе сыртқы proxy-дің тоқтауын түзетпейді.

## Дәл осы стендке арналған командалар

Командаларды rootless Docker иесінің VPS сессиясында орындаңыз. Әрқашан `--env-file .env` параметрін беріңіз: онсыз Compose кірістірілген конфигурацияда міндетті құпиясөзді таба алмауы мүмкін. Құпия деректер журналдарға шығарылмайды және Git-ке түспейді.

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

Ағымдағы стендтің VPS override коды:

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

Егер daemon іске қосылмаған болса, құрастырусыз қалпына келтіру:

```bash
systemctl --user start docker
"${compose[@]}" config --quiet
"${compose[@]}" up -d --no-build
curl -fsS http://127.0.0.1:8009/api/health
curl -fsS -H 'X-Region-Id: ALA' http://127.0.0.1:8080/v1/health/ready
```

Басқа компьютерден:

```bash
curl -fsS https://baash.govtech-kz.com/api/health
curl -fsS -H 'X-Region-Id: ALA' https://baash.govtech-kz.com/api/core/health/ready
```

Лендинг пен `/demo` бетін ашыңыз, бетті жаңартыңыз, сақталған өтінішті, War Room және Replay Lab-ты тексеріңіз. Жоғарыдағы қолжетімділік тексерулері Radar-дың жаңа екенін немесе жеке S3 жұмысын дәлелдемейді.

## Жазба алдындағы Golden World

Су сценарийі **2026 жылғы 1 қазан, 21:13 Asia/Qyzylorda (16:13 UTC)** уақытында жаңартылды, генерация `20261001T161258Z`. Тексерілді:

- 121 күнтізбелік күн / 268 тарихи өтініш: алдыңғы тарих сақталды, келесі күнге екі өтініш қосылды;
- синтетикалық координаттары бар, Radar арқылы алты сағат ішінде топтастырылған алты жаңа су хабарламасы;
- Ask Pulse RU/KK, сандық график, деректердің шығу тегі және бастапқы жазбалар;
- PDF/XLSX және 30/60/90 болжамдары;
- landing, `/demo` және екі денсаулық тексеру endpoint-і жұмыс станциясынан қолжетімді; барлық жеті қызмет healthy күйінде.

Алғашқы жазбаға дейін 600 құқықтарымен `pg_dump -Fc` жасалды, `pg_restore --list` және SHA-256 арқылы тексерілді. Backup VPS пен жұмыс станциясында сақталды; көшірмелердің SHA мәндері сәйкес келді. Алдыңғы өтініштер, күндер, шешімдер, оқиғалар мен нысандар сақталды. Қосу әдеттегі HTTP endpoints арқылы орындалды; деректер шынайы деп қайта аталған жоқ. Образдар мен сыртқы proxy бұрынғы конфигурациясында қалды.

### Келесі көрсетілімге арналған операторлық команда

`scripts/demo_refresh.py` тек Docker хостында қолмен іске қосылады. Стандартты Python 3.10+ және Docker CLI қажет; httpx пен seed VPS-ке пакеттерді орнатпай немесе web-ті құрастырмай, core-api ішіндегі бар Python арқылы орындалады.

Қалыпты checkout кезінде барлық алты модуль қатар қолжетімді: `demo_refresh.py`, `demo_clock.py`, `demo_pagination.py`, `demo_runtime.py`, `demo_world.py` және `verify_demo_world.py`. Тексерілген VPS-те олардың `135680a` нұсқасындағы көшірмесі бөлек орналасқан:

```bash
cd ~/pulse109-final/stabilization-135680a
export DOCKER_HOST="unix:///run/user/$(id -u)/docker.sock"
python3 scripts/demo_refresh.py \
  --compose-project pulse109-final \
  --backup-file "backups/pre-refresh-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

Команда екі контейнердің Compose labels, API/ДҚ дайындығын және `demo` профилін тексереді. Басқа project немесе профиль жазу алдында қабылданбайды. Backup эксклюзивті түрде жасалады: бар файл қайта жазылмайды, бос/оқылмайтын архив процесті тоқтатады. Содан кейін жетіспейтін күнтізбелік fixtures және `-refresh-<UTCgeneration>` жұрнағы бар алты жаңа су хабарламасы қосылады. Бұрын жасалған күйлер мен күндер сақталады; басқа көзбен fixture ID қақтығысы қабылданбайды.

Қосқаннан кейін жоғарыдағы толық smoke сынағы орындалады; кластер оның сәттілігінен кейін ғана Radar-да сақталады. Жартылай ақау кезінде backup пен бұрынғы әлем сақталады. Бір сағат ішінде дәл сол генерацияны қайталауды `--generation <басып шығарылған UTCtoken>` және **жаңа** backup файлымен орындаңыз: бұрын жасалған жазбалар өткізіп жіберіледі. Жаңа қалыпты іске қосу келесі генерацияны жасайды. Сәтті жол — `fresh synthetic water generation: ...; existing world preserved`.

Жаңалық тексеру уақытымен шектелген: жазу/көрсету алдында іске қосу керек. Қалыпты `seed` күндерді жаңартпайды. Жергілікті `demo_runtime.py prepare/verify/reset` `pulse109-demo` жобасын басқарады және `pulse109-final` жобасын жаңартпайды. Қалпына келтіру endpoint-і жарияланбайды; бұл процедура томдарды жоймайды және Radar терезесін өзгертпейді.

## Жаңарту және кері қайтару

Ауыстыру алдында: квотаны тексеру, ДҚ/нысандар манифесінің резервтік көшірмесін жасау, ағымдағы образдардың digest-ін жазып алу және сұлба үйлесімділігін тексеру. Web GitHub Actions ішінде құрастырылады, өзгермейтін SHA тегімен жарияланады және сәтті workflow-дан кейін жүктеледі. Жабық GHCR үшін `password-stdin` арқылы `read:packages` құқығы бар токенді және уақытша Docker авторизациялау конфигурациясын пайдаланыңыз. Құпия сөз командалар тарихына немесе репозиторийге түспеуі тиіс.

Үміткерді жүктегеннен кейін VPS override ішіндегі web тегін ауыстырыңыз, Compose-ты тексеріңіз және `up -d --no-build web` орындаңыз. Содан кейін қолжетімділік пен браузерлік сценарийді тексеріңіз. Backend образдары тексерілген миграциялармен және келісім-шарттармен бөлек жаңартылады. Кері қайтару алдыңғы образдар мен үйлесімді сұлбаны сақтайды; қолданылған миграциялар өңделмейді.

Квота жетіспеген жағдайда, алдымен `docker system df` пен атаулы ресурстарды зерттеңіз. Пайдаланылмаған құрастыру кэшін жеке rootless Docker ішінде `docker builder prune --all --force` командасымен жоюға болады. Ортақ серверде `docker system prune -a` командасын қолданбаңыз; томдар, бөтен ресурстар және кері қайтару образдары құрастыру кэшіне жатпайды. Логтардың өсуін қадағалаңыз: қайта іске қосу саясаты олардың ротациясын орнатпайды.

## Басқа хостта орналастыру

Бұл бөлім ағымдағы VPS күйін емес, нұсқаларды сипаттайды. Жаңа хост үшін DNS/TLS, Docker/Compose, квота/сыйымдылық, құпияларды жабық сақтау және алдын ала тексерілген 80/443 және loopback порттары қажет.

- **Қолданыстағы HTTPS proxy:** base + demo + `docker-compose.behind-proxy.yml`, жеке loopback порт қайта анықтауы және сәйкес upstream. Әдепкіде бұл overlay-дің web порты — 3000; ағымдағы стенд оны 8009-ға қайта анықтайды.
- **Proxy-сіз жеке хост:** base + demo + `docker-compose.public.yml` Caddy-ді іске қосады. Тек осы жерде 80/443 порттары алынады. Бұл overlay-ді тексерілген ортақ VPS-те қолданбаңыз.
- **Storage:** `PULSE109_OBJECT_STORAGE_MODE=local` файлдық жүйе томдарын сақтайды; `s3` үшін Git-тен тыс bucket/endpoint/region және тіркелгі деректері қажет. Public overlay S3 extra құрастырады. Жеке S3 туралы мәлімдемес бұрын мыналарды тексеріңіз: жазу → SHA/оқу → қайта іске қосу → оқу → анонимді кіруге тыйым салу → қалпына келтіру.
- **Database:** `POSTGRES_PASSWORD` бірегей URL-safe құпия сөз болуы тиіс; migration/API/worker URLs содан алынады. Қолданыстағы ДҚ үшін environment өзгерісі рөлдің құпиясөзін өздігінен өзгертпейді.
- **Seed:** сәйкес демонстрациялық жобаның дайын API-ына қарсы іске қосу; behind-proxy API әдетте жарияланбайды, сондықтан ішкі процесті немесе loopback-ке уақытша байлауды қолданыңыз. Seed үшін API-ды сыртқа ашпаңыз.

Өндірістік пилот шарттары — [PILOT_DEPLOYMENT_REQUIREMENTS](PILOT_DEPLOYMENT_REQUIREMENTS.kk.md). [BACKUP_RESTORE](BACKUP_RESTORE.kk.md) процедураны белгілейді, бірақ бекітілген RPO/RTO емес. [Golden Demo](../../docs/GOLDEN_DEMO.kk.md) көрсету маршрутын, [FEATURE_STATUS](../../docs/FEATURE_STATUS.kk.md) — ағымдағы шекараларды анықтайды. Демонстрациялық scanner mock болып қала береді, B07/B08/B10 ашық.
