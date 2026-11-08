---
description: Запускает полный QA-флоу - анализ требований, задачи Jira, тестовая модель Qase и итоговый отчёт.
agent: qa-orchestrator
---

Запусти полный QA-флоу по требованиям.

Параметры запуска:

$ARGUMENTS

Если параметры не указаны, используй значения по умолчанию:

- page: BOOK-101
- scope: создание закладки на Android
- jira_project: QA
- qase_project: QA
- mode: draft

Порядок работы:

1. Создай каталог `artifacts/<run_id>/`.
2. Получи требования через MCP `qa-mock` или из `inputs/confluence`.
3. Сохрани `requirements-source.json`.
4. Запусти субагента `requirement-reviewer` и проверь QG1.
5. После QG1 запусти параллельно `task-designer` и `test-designer`.
6. Проверь QG2 и QG3, собери `traceability.json` и проверь QG4.
7. В режиме `draft` ничего не публикуй, в режиме `publish` создай записи через MCP и сохрани ID.
8. Запусти `python scripts/validate_artifacts.py artifacts/<run_id>`.
9. Сохрани `gate-results.json`, `run-manifest.json` и `final-report.md`.

В конце покажи краткое резюме: статус, найденные проблемы, количество задач и проверок, путь к отчёту.
