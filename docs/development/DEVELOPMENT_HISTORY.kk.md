[Русский](DEVELOPMENT_HISTORY.md) · [English](DEVELOPMENT_HISTORY.en.md) · [Қазақша](DEVELOPMENT_HISTORY.kk.md)

# Pulse 109 даму тарихы

Сақталған бүкіл `main` тарихының хронологиясы; 2026 жылғы 1 қазанда `e494390` дейін тексерілген. Бұл — өзгерістер тарихы; ағымдағы күйді [FEATURE_STATUS](../submission/FEATURE_STATUS.kk.md) анықтайды. 12 қыркүйекке дейінгі жұмыс [Camp журналында](../submission/PROJECT_JOURNAL.kk.md) сипатталған; 3–11 қыркүйек үшін Git коммиттері мәлімделмейді.

| Күндер | Бағыт өзгерісі және себебі | Өкілдік коммиттер / авторлар |
| --- | --- | --- |
| 12 қыркүйекке дейін | Бастапқы кейсті талдау және деректер аудиті: жеті өңір, азамат мәтінінің жоқтығы және үйлеспейтін анықтамалықтар | Бастапқы журналда құжатталған, апта үшін Git растауы жоқ |
| 12 қыркүйек | Бөлек макеттер орнына келісімшарттар және алғашқы орындалатын негіз | `d199e16`, `9e3d86e` — Baktiyar |
| 13–15 қыркүйек | Канондық ingest және routing/retrieval/forecast эксперименттері; дерек шектеулері мен тасымалдану мүмкіндігін өлшеу | `666f369`, `d004b71`, `0ef5c50`, `0196030` — Arsen |
| 20 қыркүйек | Ортақ офлайн зерттеу сценарийі | `85216b4` — Arsen |
| 23–25 қыркүйек | Тұрақты PostgreSQL, outbox/restore және human governance: шешім ML/сыртқы жүйеге тәуелсіз сақталуға тиіс | `7534a5b`, `833c412`, `9bbc61b`, `23f87c2`, `a31c8a9`, `cb10f3e` — Baktiyar |
| 26–27 қыркүйек | Incident/control plane/privacy, нақты PostgreSQL демо; бір өтініштен ортақ қалалық мәселеге өту | `c82dcde`, `26b9243` — Baktiyar; `9106efd`, `69b5883`, `c87dc6b`, `98793e4` — Arsen |
| 28 қыркүйек | Өнім қабығы, оқиғалар тізімі, нәтижелер, policy replay diff, storage runtime/public overlays; есептелетін жауаптары бар Ask Pulse | `c61b322`, `8eba430`, `5c9d044`, `bf83bb8` — Arsen; `b3b4440` — Shyngyskhan; `ac21689`, `344ac69`, `5e3b8fa` — Baktiyar |
| 29–30 қыркүйек | Hex UI, Golden World, карталар және presenter flow; VPS хостында Next.js жинамау үшін browser recording helper және web image publishing | `4559a7d` — Shyngyskhan; `ca4c2dd` — Arsen; `d613a6b`, `b255bb6`, `c2effc5`, `766bd46`, `1c8ab77`, `22d89e7` — Baktiyar |
| 1 қазан | Қазыларға арналған README және суреттер; кейін тіл, тарих, CI және deployment келісімі | `41b6a1f`, `e494390` — Shyngyskhan; осы құжаттама жұмысы бұл кезеңді жалғастырады |

Авторлық және капитанның рөлі [PROJECT_JOURNAL](../submission/PROJECT_JOURNAL.kk.md) ішінде. Коммит саны команданың бүкіл еңбегін өлшемейді. Коммитті тексеру: `git show <hash>`; хронология: `git log --reverse --date=short --format='%h %ad %an %s' main`. Архитектура шешімдері және қайта қараулары — [DECISION_LOG](../governance/DECISION_LOG.kk.md).
