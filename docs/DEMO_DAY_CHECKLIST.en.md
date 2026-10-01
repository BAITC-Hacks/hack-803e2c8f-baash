[Русский](DEMO_DAY_CHECKLIST.md) · [English](DEMO_DAY_CHECKLIST.en.md) · [Қазақша](DEMO_DAY_CHECKLIST.kk.md)

# Demo Day checklist

Check the real PostgreSQL-backed demo before presenting. Scenario freshness is valid only at the time of verification.

## 60–30 minutes before presenting

- Run preflight and resolve every NOT READY reason. Low quota headroom requires a quota increase or safe cleanup of Pulse-owned files; preserve rollback-critical data.
- If the water scenario is stale, run the demo_refresh.py command printed by preflight with a new verified backup. Refresh is never automatic.
- Repeat preflight: 120+ history days, six fresh water appeals, Radar, Ask Pulse RU/KK, PDF/XLSX and 30/60/90-day forecasts.
- Open public / and /demo, refresh the page and walk through the main scenario.

## 10 minutes before presenting

- Repeat preflight and check all seven services are healthy.
- Freeze the verified state: no further code, image, dependency, migration or data changes. Finish documentation mass edits in advance.

## During the presentation

- Do not deploy, pull/build, reset the database or refresh.
- For local service failure, use demo_recover.sh; it starts missing services without builds, migrations or resets.
- If the local stack is healthy but HTTPS is unavailable, check the external proxy/network. Restarting PostgreSQL does not address that failure.

## Presentation fallback

- Public URL: https://baash.govtech-kz.com/demo.
- Local PostgreSQL-backed /demo, if prepared and verified on the laptop beforehand; this is a separate fallback environment.
- Browser-only mock is the last visual fallback and must be labelled mock.
- Prepare and verify a two-minute recording. The presenter confirms the recording and local environment exist; this document does not claim they are already ready.

## Operator commands

```bash
cd ~/pulse109-final
python3 scripts/demo_preflight.py
./scripts/demo_recover.sh
```

Detailed procedure: [demo runbook](DEMO_RUNBOOK.en.md), [public deployment](../infra/runbooks/PUBLIC_DEPLOYMENT.en.md), [Golden Demo](GOLDEN_DEMO.en.md).
