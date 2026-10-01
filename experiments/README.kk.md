[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md)

# Үміткерлерді офлайн салыстыру

Қазіргі уақытта репозиторийде **PulseDM салмақтары немесе KK/RU/mixed тілдеріндегі нақты белгіленген бенчмарк жоқ**. Бұл каталог бір ортақ бағалаушыны сипаттайды; бұл модельдерге қызмет көрсету стегі емес. Синтетикалық TF-IDF және іздеу бойынша қолданыстағы эксперименттер `ml/training` және `ml/evaluation` ішінде қалады.

Мақұлданған датасетпен және жергілікті жасалған үміткерлердің болжамдарымен репозиторий түбірінен іске қосыңыз:

```text
uv run python -m ml.evaluation.candidate_compare \
  --manifest /secure/eval/manifest.json \
  --cases /secure/eval/cases.jsonl \
  --submission /secure/eval/xlmr.json \
  --submission /secure/eval/pulsedm.json \
  --output /secure/eval/report.json
```

PowerShell-де пәрменді бір жолға енгізіңіз немесе әр `\` таңбасын PowerShell жолын жалғастыру таңбасымен ауыстырыңыз. Жеке бағалау файлдарын репозиторийден тыс сақтаңыз.

`manifest.json` файлы тек `dataset_id`, `dataset_sha256`, `record_count`, `synthetic_only`, `approval_ref` өрістерін қамтиды. `cases.jsonl` файлында әр жағдайға/сұраққа бір нысаннан келеді және тек мына өрістер болады: `case_key`, `group_key` (бүркеншік 64-таңбалы hex-жолдар), `question_id`, `question_type` (`choice` немесе `boolean`), `options`, `gold`, `is_ood`, `language` (`ru`, `kk`, `mixed`), `region_id`, `split` (`train`, `calibration`, `test`), `decision_at`, `feature_snapshot_at`, `label_observed_at` (уақыт белдеуінің ығысуы бар уақыт белгілері). Мәтін немесе қосымша өрістер қабылданбайды. Датасет хэші бастапқы JSONL байттары бойынша есептеледі.

Әрбір сабмит JSON-ы тек `model_id`, `artifact_sha256`, `dataset_sha256`, `predictions` өрістерін қамтиды. Әрбір болжамда `case_key`, `question_id`, сомасы бірге тең болатын **тек және барлық** жарияланған нұсқалар үшін `probabilities` және `[0,1]` аралығындағы `ood_score` болады. Әр сынақ жағдайы/сұрағы үшін дәл бір жол жіберіңіз және train/calibration үшін ешбір жол жібермеңіз. Бағалаушы үміткерлерді осы бірдей сынақ жинағында салыстырады, модель салмақтарын жазбайды және өндірістік пайдалануға ешқашан рұқсат бермейді. [Хаттаманы](../docs/ml/EVALUATION_PROTOCOL.kk.md) қараңыз.
