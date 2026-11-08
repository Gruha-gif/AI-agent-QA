# Правила проекта

Этот репозиторий содержит мультиагентную QA-систему для opencode.

## Агенты

- `qa-orchestrator` - основной агент, ведёт флоу и проверяет Quality Gates.
- `requirement-reviewer` - анализ требований.
- `task-designer` - проектирование задач Jira.
- `test-designer` - проектирование тестовой модели Qase.

## Артефакты

Каждый запуск пишет результаты в `artifacts/<run_id>/`:

- `requirements-source.json`
- `requirements-review.json`
- `task-design.json`
- `test-design.json`
- `traceability.json`
- `gate-results.json`
- `run-manifest.json`
- `final-report.md`

Схемы и обязательные поля описаны в Skills и в задании агента. Артефакт без метаданных считается недействительным.

## Правила работы

- источники требований только из Confluence или `inputs/confluence`;
- требования не изменяются, отсутствующие данные не выдумываются;
- номера `REQ-`, `TASK-`, `TEST-` уникальны в пределах запуска;
- задачи и тесты всегда ссылаются на требования;
- записи в Jira и Qase создаются только в режиме `publish`;
- результат считается готовым только после прохождения Quality Gates и проверки `scripts/validate_artifacts.py`.

## Команды

```bash
python scripts/validate_artifacts.py artifacts/run-001
python scripts/mock_qa_mcp.py
```

## Язык

Документация, артефакты и отчёты - на русском языке. Имена полей и идентификаторы - на английском.
