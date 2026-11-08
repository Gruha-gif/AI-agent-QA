# QA Multi-Agent System

Глобальная инструкция проекта для работы с AI-агентами в OpenCode. Здесь зафиксированы цель, роли, структура, правила работы с артефактами и Quality Gates. Детальные методики вынесены в Skills.

## Цель

Получить требования из Confluence, проверить их качество, спроектировать задачи Jira и тестовую модель Qase, сохранить результат каждого этапа и подтвердить его Quality Gate.

## Роли агентов

| Агент | Роль | Режим |
| --- | --- | --- |
| `qa-orchestrator` | ведёт флоу, управляет субагентами, проверяет Quality Gates, собирает итоговый отчёт | primary |
| `requirement-reviewer` | анализ требований на противоречия, неоднозначности, пробелы и проверяемость | subagent |
| `task-designer` | проектирование задач Jira по проверенным требованиям | subagent |
| `test-designer` | проектирование тестовой модели Qase: positive, negative, boundary | subagent |

Оркестратор не выполняет работу субагентов сам. Субагенты не вызывают друг друга и не работают с внешними системами напрямую.

## Skills

| Skill | Назначение | Итоговый артефакт |
| --- | --- | --- |
| `requirement-review` | методика анализа требований | Requirement Review Artifact |
| `task-design` | методика проектирования задач | Jira Tasks Artifact |
| `test-design` | методика проектирования проверок | Test Model Artifact |

## Поток работ

```text
Confluence
    |
    v
qa-orchestrator: requirements-source.json
    |
    v
requirement-reviewer + skill requirement-review
    |
    v
Requirement Review  -->  QG1
    |                     |
    |                     +-- FAIL --> вопрос пользователю, статус BLOCKED
    v PASS
task-designer (skill task-design)   test-designer (skill test-design)
    |                                   |
    v                                   v
Jira Tasks Artifact (QG2)          Test Model Artifact (QG3)
    |                                   |
    +---------------+-------------------+
                    v
            traceability.json --> QG4
                    v
      gate-results.json, run-manifest.json, final-report.md
```

## Структура проекта

```text
qa-multi-agent/
├── AGENTS.md
├── opencode.json
├── .opencode/
│   ├── agents/
│   │   ├── qa-orchestrator.md
│   │   ├── requirement-reviewer.md
│   │   ├── task-designer.md
│   │   └── test-designer.md
│   ├── skills/
│   │   ├── requirement-review/SKILL.md
│   │   ├── task-design/SKILL.md
│   │   └── test-design/SKILL.md
│   └── tools/
│       └── confluence.ts
├── artifacts/
│   ├── requirement-review/1.md
│   ├── jira-tasks/1.md
│   ├── test-model/1.md
│   └── runs/<run_id>/*.json
├── inputs/
│   ├── confluence/BOOK-101.md
│   ├── jira-context.json
│   └── qase-context.json
├── scripts/
│   ├── mock_qa_mcp.py
│   ├── check_json.py
│   ├── validate_artifacts.py
│   └── export_artifacts.py
└── evals/
    ├── dataset/golden_dataset.json
    └── evaluator.py
```

## Артефакты

Markdown-артефакты лежат по типам этапов: `artifacts/requirement-review/`, `artifacts/jira-tasks/`, `artifacts/test-model/`. Номер файла увеличивается при появлении новой версии артефакта.

Машиночитаемые артефакты прогона лежат в `artifacts/runs/<run_id>/`:

- `requirements-source.json`
- `requirements-review.json`
- `task-design.json`
- `test-design.json`
- `traceability.json`
- `gate-results.json`
- `run-manifest.json`
- `final-report.md`

Артефакт без метаданных (`run_id`, `baseline_id`, `artifact_version`, `producer`, `created_at`, `status`) считается недействительным.

## Quality Gates

- **QG1** - требования разобраны, замечания подтверждены цитатами, нет блокирующих противоречий.
- **QG2** - задачи связаны с требованиями, покрытие полное, обязательные поля заполнены.
- **QG3** - проверки покрывают требования, применимые типы сценариев обоснованы.
- **QG4** - единая версия требований, все ссылки существуют, артефакты проходят валидацию.

Непройденный Quality Gate запрещает переход к следующему этапу.

## Инструменты

- MCP `qa-mock` - Confluence, Jira и Qase для локального запуска: `confluence_get_page`, `jira_create_issue`, `qase_create_case`.
- Custom Tool `.opencode/tools/confluence.ts` - чтение страницы Confluence напрямую через REST API, только чтение.
- `python scripts/check_json.py <file>` - проверка валидности JSON.
- `python scripts/validate_artifacts.py <run_dir>` - проверка связей и покрытия.
- `python scripts/export_artifacts.py <run_dir>` - выгрузка markdown-артефактов.

## Правила

- требования не изменяются, отсутствующие данные не выдумываются;
- секреты не хранятся в инструкциях и Skills, только в переменных окружения;
- операции чтения отделены от операций записи, запись выполняется только в режиме `publish`;
- повторная запись в Jira и Qase выполняется только после проверки, что сущность уже не создана;
- при частичном сбое сохраняется State и успешные результаты, итоговый статус `PARTIAL`;
- при неоднозначности, конфликте правил или отсутствии данных выполняется эскалация человеку;
- результат считается готовым только после прохождения Quality Gates и валидатора.

## Команды

```bash
opencode run "page=BOOK-101 scope=создание закладки на Android mode=draft"
python scripts/validate_artifacts.py artifacts/runs/run-20261108-120000
python scripts/export_artifacts.py artifacts/runs/run-20261108-120000
python evals/evaluator.py artifacts/runs/run-20261108-120000
```
