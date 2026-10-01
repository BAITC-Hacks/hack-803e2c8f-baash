[Русский](README.md) · [English](README.en.md) · [Қазақша](README.kk.md)

# Офлайн-сравнение кандидатов

В настоящее время в репозитории **нет весов PulseDM или реального размеченного бенчмарка на KK/RU/mixed**. Этот каталог описывает единый инструмент оценки; это не стек обслуживания моделей. Существующие эксперименты с синтетическим TF-IDF и поиском остаются в `ml/training` и `ml/evaluation`.

Запуск из корня репозитория с утверждённым датасетом и локально сгенерированными предсказаниями кандидатов:

```text
uv run python -m ml.evaluation.candidate_compare \
  --manifest /secure/eval/manifest.json \
  --cases /secure/eval/cases.jsonl \
  --submission /secure/eval/xlmr.json \
  --submission /secure/eval/pulsedm.json \
  --output /secure/eval/report.json
```

В PowerShell введите команду в одну строку или замените каждый `\` на символ переноса строки PowerShell. Храните приватные файлы оценки вне репозитория.

Файл `manifest.json` содержит строго `dataset_id`, `dataset_sha256`, `record_count`, `synthetic_only`, `approval_ref`. Файл `cases.jsonl` содержит по одному объекту на случай/вопрос со строго заданными полями `case_key`, `group_key` (псевдонимные 64-символьные hex-строки), `question_id`, `question_type` (`choice` или `boolean`), `options`, `gold`, `is_ood`, `language` (`ru`, `kk`, `mixed`), `region_id`, `split` (`train`, `calibration`, `test`), `decision_at`, `feature_snapshot_at`, `label_observed_at` (временные метки со смещением часового пояса). Текстовые или дополнительные поля не принимаются. Хеш датасета вычисляется по необработанным байтам JSONL.

Каждый JSON сабмита содержит строго `model_id`, `artifact_sha256`, `dataset_sha256`, `predictions`. Каждое предсказание содержит `case_key`, `question_id`, `probabilities` для **всех и только** объявленных вариантов с суммой, равной единице, и `ood_score` в диапазоне `[0,1]`. Передавайте ровно по одной строке для каждого тестового случая/вопроса и ни одной строки для train/calibration. Оценщик сравнивает кандидатов на этом идентичном тестовом наборе, не сохраняет веса моделей и никогда не авторизует промышленное использование. См. [протокол](../docs/ml/EVALUATION_PROTOCOL.md).
