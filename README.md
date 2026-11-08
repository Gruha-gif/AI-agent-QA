# QA Multi-Agent System для OpenCode

Мультиагентная система для анализа требований, создания задач Jira и тестовой модели Qase. Построена на Agent Instruction, трёх Skills и инструментах доступа к внешним системам.

## Что делает система

1. Оркестратор получает требования из Confluence и сохраняет исходный артефакт.
2. Агент `requirement-reviewer` анализирует требования и проверяет Quality Gate 1.
3. После прохождения ворот параллельно запускаются `task-designer` и `test-designer`.
4. Каждый этап сохраняет результат: markdown-артефакт для чтения и JSON для проверки.
5. Оркестратор собирает трассируемость, проверяет QG2-QG4 и формирует итоговый отчёт.
6. В режиме `publish` создаются записи в Jira и Qase, сохраняются их идентификаторы.

## Агенты

| Агент | Роль | Режим |
| --- | --- | --- |
| `qa-orchestrator` | ведёт флоу, управляет субагентами, проверяет Quality Gates, собирает отчёт | primary |
| `requirement-reviewer` | анализ требований на противоречия, неоднозначности, пробелы и проверяемость | subagent |
| `task-designer` | проектирование задач Jira по проверенным требованиям | subagent |
| `test-designer` | проектирование проверок Qase: positive, negative, boundary | subagent |

Оркестратор не выполняет работу субагентов сам. Субагенты не вызывают друг друга и не изменяют внешние системы.

## Skills

| Skill | Назначение | Артефакт |
| --- | --- | --- |
| `requirement-review` | методика анализа требований | Requirement Review |
| `task-design` | методика проектирования задач | Jira Tasks |
| `test-design` | методика проектирования проверок | Test Model |

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
│   └── runs/
│       ├── run-001/
│       └── run-20261108-120000/
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

## Требования

- OpenCode 1.19 или новее
- Python 3.10 или новее
- Модель, настроенная в вашем OpenCode

## Запуск

```bash
cd C:\work\oc\qa-multi-agent
opencode
```

После изменения конфигурации или файлов агентов перезапустите OpenCode.

В интерактивной сессии:

```text
/qa-flow page=BOOK-101 scope="создание закладки на Android" mode=draft
```

Без аргументов используются значения по умолчанию из `inputs/`.

Неинтерактивный запуск:

```bash
opencode run "page=BOOK-101 scope=создание закладки на Android mode=draft"
```

## Режимы

- `draft` - результаты сохраняются только в артефакты, записи в Jira и Qase не создаются. Значение по умолчанию.
- `publish` - после прохождения QG4 оркестратор создаёт задачи и проверки через MCP и сохраняет реальные ID и ссылки.

## Результаты

### Markdown-артефакты

- `artifacts/requirement-review/1.md` - результат анализа требований.
- `artifacts/jira-tasks/1.md` - подготовленные задачи.
- `artifacts/test-model/1.md` - тестовая модель с покрытием и применимостью.

### Прогоны

`artifacts/runs/run-20261108-120000` - живой прогон агентов:

- 6 требований разобрано, только неблокирующие замечания;
- 6 задач: TASK-001 - TASK-006;
- 14 проверок: 4 позитивные, 5 негативных, 5 граничных;
- трассируемость по всем требованиям;
- QG1-QG4 = PASS, итоговый статус SUCCESS, режим draft.

`artifacts/runs/run-001` - эталонный набор артефактов по контрактам Skills: 6 требований, 3 задачи, 11 проверок.

## Проверка

```bash
python scripts/validate_artifacts.py artifacts/runs/run-20261108-120000
python evals/evaluator.py artifacts/runs/run-20261108-120000
python scripts/export_artifacts.py artifacts/runs/run-20261108-120000
```

Ожидаемый результат:

- валидатор: 33 проверки, 0 ошибок;
- evaluator: 7 проверок, 0 провалов.

## Интеграции

### MCP qa-mock

Локальный сервер  `scripts/mock_qa_mcp.py` предоставляет:

| Инструмент | Назначение |
| --- | --- |
| `confluence_get_page` | чтение страницы требований из `inputs/confluence` |
| `jira_create_issue` | запись задачи в `artifacts/published/jira-issues.json` |
| `qase_create_case` | запись проверки в `artifacts/published/qase-cases.json` |

Проверка сервера: `python scripts/mock_qa_mcp.py`.

### Custom Tool для Confluence

`.opencode/tools/confluence.ts` читает страницу Confluence напрямую через REST API по `pageId`. Требует переменные окружения `CONFLUENCE_URL`, `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN`. Инструмент выполняет только чтение.

### Настоящие Jira и Qase

1. Добавьте MCP-серверы в `opencode.json` и передайте токены через переменные окружения.
2. Отключите `qa-mock`: `"qa-mock": { "enabled": false }`.
3. Сверьте имена инструментов в промптах агентов с вашим MCP-сервером.

## Quality Gates

| Ворота | Что проверяется |
| --- | --- |
| QG1 | все требования разобраны, замечания подтверждены цитатами, блокирующих проблем нет |
| QG2 | задачи связаны с требованиями, покрытие полное, поля заполнены |
| QG3 | проверки покрывают требования, применимые типы сценариев обоснованы |
| QG4 | единая версия требований, ссылки существуют, артефакты валидны |

## Соответствие заданию

| Пункт задания | Реализация |
| --- | --- |
| Декомпозиция инструкции на агентов | 4 агента в `.opencode/agents` |
| Подключение Skills и интеграций | 3 Skills, MCP `qa-mock`, Custom Tool `confluence.ts` |
| Настройка взаимодействия агентов | субагенты вызываются оркестратором, обмен через артефакты |
| Запуск флоу и проверка | живой прогон `run-20261108-120000`, валидатор и evaluator |

## Ограничения

- `qa-mock` не является настоящей Jira или Qase: он пишет локальные журналы и не проверяет права доступа.
- Живой прогон выполнялся на модели по умолчанию текущего окружения; на другой модели формулировки и количество замечаний могут отличаться.
- Артефакты `run-001` собраны вручную по контрактам Skills и служат эталоном структуры.
- В режиме `draft` внешние ID не создаются, поэтому ссылки на Jira и Qase в отчёте отсутствуют.

## Публикация в GitHub

Репозиторий: <https://github.com/Gruha-gif/AI-agent-QA>

```bash
cd C:\work\oc\qa-multi-agent
git remote add origin https://github.com/Gruha-gif/AI-agent-QA.git
git fetch origin
git pull origin main --allow-unrelated-histories --no-rebase
```

При конфликте в `README.md` оставьте версию проекта:

```bash
git checkout --ours README.md
git add README.md
git commit -m "Merge GitHub README with project"
git push -u origin main
```
