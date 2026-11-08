# QA Multi-Agent System для OpenCode

Мультиагентная система для анализа требований, проектирования задач Jira и тестовой модели Qase. Собрана на базе Agent Instructions и трёх Skills: `requirement-review`, `task-design`, `test-design`.

## Что делает система

1. Оркестратор получает требования из Confluence и сохраняет исходный артефакт.
2. Агент `requirement-reviewer` анализирует требования и проверяет Quality Gate 1.
3. После прохождения ворот параллельно запускаются `task-designer` и `test-designer`.
4. Каждый этап сохраняет результат в `artifacts/<run_id>/`.
5. Оркестратор собирает трассируемость, проверяет QG2-QG4 и формирует итоговый отчёт.

## Архитектура

| Компонент | Роль | Файл |
| --- | --- | --- |
| `qa-orchestrator` | ведёт флоу, проверяет Quality Gates, собирает отчёт | `.opencode/agent/qa-orchestrator.md` |
| `requirement-reviewer` | анализирует требования | `.opencode/agent/requirement-reviewer.md` |
| `task-designer` | проектирует задачи Jira | `.opencode/agent/task-designer.md` |
| `test-designer` | проектирует проверки Qase | `.opencode/agent/test-designer.md` |
| Skill `requirement-review` | методика анализа требований | `.opencode/skills/requirement-review/SKILL.md` |
| Skill `task-design` | методика проектирования задач | `.opencode/skills/task-design/SKILL.md` |
| Skill `test-design` | методика проектирования тестов | `.opencode/skills/test-design/SKILL.md` |
| Command `/qa-flow` | запуск полного флоу | `.opencode/command/qa-flow.md` |
| MCP `qa-mock` | Confluence, Jira и Qase для локального запуска | `scripts/mock_qa_mcp.py` |
| Валидатор | проверка артефактов и связей | `scripts/validate_artifacts.py` |

Оркестратор ничего не проектирует сам: он управляет специализированными агентами и отвечает за порядок этапов и качество результата.

## Схема флоу

```text
Запрос пользователя
        |
        v
qa-orchestrator: получение требований из Confluence
        |
        v
requirements-source.json
        |
        v
requirement-reviewer + skill requirement-review
        |
        v
requirements-review.json  -->  QG1
        |                        |
        |                        +-- FAIL --> вопрос пользователю, статус BLOCKED
        v PASS
   +---------------------------+
   |                           |
   v                           v
task-designer               test-designer
skill task-design           skill test-design
   |                           |
   v                           v
task-design.json            test-design.json
   |                           |
   +-------> QG2, QG3 <--------+
                |
                v
traceability.json  -->  QG4
                |
                v
gate-results.json, run-manifest.json, final-report.md
```

## Структура репозитория

```text
.
├── opencode.json
├── AGENTS.md
├── README.md
├── .opencode
│   ├── agent
│   │   ├── qa-orchestrator.md
│   │   ├── requirement-reviewer.md
│   │   ├── task-designer.md
│   │   └── test-designer.md
│   ├── command
│   │   └── qa-flow.md
│   └── skills
│       ├── requirement-review/SKILL.md
│       ├── task-design/SKILL.md
│       └── test-design/SKILL.md
├── inputs
│   ├── confluence/BOOK-101.md
│   ├── jira-context.json
│   └── qase-context.json
├── scripts
│   ├── mock_qa_mcp.py
│   └── validate_artifacts.py
└── artifacts
    └── run-001
        ├── requirements-source.json
        ├── requirements-review.json
        ├── task-design.json
        ├── test-design.json
        ├── traceability.json
        ├── gate-results.json
        ├── run-manifest.json
        └── final-report.md
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

После изменения конфигурации или файлов агентов перезапустите OpenCode: конфигурация читается один раз при старте.

В интерактивной сессии выполните команду:

```text
/qa-flow page=BOOK-101 scope="создание закладки на Android" jira_project=QA qase_project=QA mode=draft
```

Без аргументов команда использует значения по умолчанию из `inputs/`.

Можно обратиться к агенту обычным текстом:

```text
Запусти QA-флоу для страницы BOOK-101 в режиме draft
```

## Режимы работы

- `draft` - результаты сохраняются только в артефакты, записи в Jira и Qase не создаются. Значение по умолчанию.
- `publish` - после прохождения QG4 оркестратор создаёт задачи и проверки через MCP и сохраняет реальные ID и ссылки.

## Контрольный прогон

В репозитории лежит прогон `artifacts/run-001`:

- 6 требований проанализированы, найдено 1 незначительное замечание;
- спроектированы 3 задачи Jira;
- спроектированы 11 проверок Qase: позитивные, негативные и граничные;
- покрытие требований задачами и проверками - 100%;
- все ворота QG0-QG4 пройдены;
- итоговый статус - SUCCESS, публикация не запрашивалась.

Проверка артефактов:

```bash
python scripts/validate_artifacts.py artifacts/run-001
```

Ожидаемый результат: 30 проверок, 0 ошибок, сообщение «артефакты согласованы».

## Интеграции

### Локальный демонстрационный MCP

`qa-mock` запускается как локальный MCP-сервер и предоставляет три инструмента:

| Инструмент | Назначение |
| --- | --- |
| `confluence_get_page` | читает страницу требований из `inputs/confluence` |
| `jira_create_issue` | записывает задачу в `artifacts/published/jira-issues.json` |
| `qase_create_case` | записывает проверку в `artifacts/published/qase-cases.json` |

Проверить сервер вручную:

```bash
python scripts/mock_qa_mcp.py
```

Сервер обменивается JSON-RPC сообщениями через stdio и поддерживает `initialize`, `tools/list`, `tools/call` и `ping`.

### Реальные системы

В текущем окружении уже подключён MCP-сервер `atlassian` с инструментами вида `atlassian_confluence_get_page` и `atlassian_jira_create_issue`. Чтобы использовать его вместо демо-сервера:

1. В промптах оркестратора замените имя инструмента `confluence_get_page` на `atlassian_confluence_get_page`.
2. Для создания задач используйте `atlassian_jira_create_issue`, для чтения метаданных - остальные инструменты Jira.
3. Отключите `qa-mock` в `opencode.json`: `"qa-mock": { "enabled": false }`.

Для отдельного запуска с настоящими Confluence, Jira и Qase:

1. Добавьте MCP-серверы в `opencode.json` в раздел `mcp` и передайте токены через переменные окружения.
2. Отключите `qa-mock`: `"qa-mock": { "enabled": false }`.
3. Убедитесь, что имена инструментов в промптах агентов соответствуют вашему MCP-серверу.

Пример удалённого сервера:

```json
{
  "mcp": {
    "atlassian": {
      "type": "remote",
      "url": "https://your-mcp-host/mcp",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer {env:ATLASSIAN_TOKEN}"
      }
    }
  }
}
```

## Quality Gates

| Ворота | Что проверяется |
| --- | --- |
| QG1 | все требования разобраны, замечания подтверждены цитатами, блокирующих проблем нет |
| QG2 | задачи связаны с требованиями, покрытие полное, поля заполнены |
| QG3 | проверки покрывают требования, применимые типы сценариев обоснованы |
| QG4 | единая версия требований, все ссылки существуют, артефакты валидны |

Ворота не пройдены - переход к следующему этапу запрещён, статус фиксируется в `gate-results.json`.

## Соответствие домашнему заданию

| Пункт задания | Реализация |
| --- | --- |
| Декомпозиция инструкции на агентов | 4 агента в `.opencode/agent` |
| Подключение Skills и интеграций | 3 Skills и MCP `qa-mock` в `opencode.json` |
| Настройка взаимодействия агентов | субагенты вызываются оркестратором, обмен через артефакты |
| Запуск флоу и проверка | контрольный прогон `artifacts/run-001` и валидатор |

## Ограничения

- `qa-mock` не является настоящей Jira или Qase: он пишет локальные журналы и не проверяет права доступа.
- В демонстрационном прогоне не выполнялся live-запуск модели: артефакты собраны по контрактам Skills и проверены валидатором. Для живого прогона используйте `/qa-flow`.
- В режиме `draft` внешние ID не создаются, поэтому ссылки на Jira и Qase в отчёте отсутствуют.

## Публикация в GitHub

```bash
cd C:\work\oc\qa-multi-agent
git init
git add .
git commit -m "QA multi-agent system for OpenCode"
git branch -M main
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```

Ссылку на репозиторий можно сдавать после успешного `git push`.
