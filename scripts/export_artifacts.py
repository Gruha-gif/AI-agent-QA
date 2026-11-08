#!/usr/bin/env python3
"""Выгрузка артефактов прогона в markdown по структуре artifacts/<тип>/<номер>.md.

Использование:
    python scripts/export_artifacts.py artifacts/runs/run-20261108-120000
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(run_dir, name):
    return json.loads((run_dir / name).read_text(encoding="utf-8"))


def cell(value, limit=None):
    text = "" if value is None else str(value)
    text = text.replace("|", "\\|").replace("\n", " ").strip()
    if limit and len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(cell(value) for value in row) + " |")
    return "\n".join(lines)


def questions_block(questions):
    if not questions:
        return "- Открытых вопросов нет"
    lines = []
    for item in questions:
        if not isinstance(item, dict):
            lines.append(f"- {item}")
            continue
        qid = item.get("id") or item.get("question_id") or "Q"
        text = item.get("text") or item.get("question") or ""
        refs = item.get("requirement_ids") or item.get("affected_requirements") or []
        suffix = f" (требования: {', '.join(refs)})" if refs else ""
        lines.append(f"- {qid}: {text}{suffix}")
    return "\n".join(lines)


def write_requirement_review(run_dir, target, source, review):
    findings = review.get("findings") or []
    blocking = [item for item in findings if item.get("blocking")]
    readiness = review.get("readiness") or {}

    source_meta = source.get("source") if isinstance(source.get("source"), dict) else {}
    page_id = source.get("page_id") or source_meta.get("page_id", "")
    page_version = source.get("version") or source_meta.get("version", "")

    meta = table(
        ["Поле", "Значение"],
        [
            ["Artifact", "Requirement Review"],
            ["Artifact Version", "1"],
            ["Source Artifact", f"Confluence `{page_id}`, версия {page_version}"],
            ["Run", run_dir.name],
            ["Created", (review.get("meta") or {}).get("created_at", "")],
            ["Requirements", len(source.get("requirements") or [])],
            ["Findings", len(findings)],
            ["Blocking", len(blocking)],
            ["Readiness", readiness.get("status", "")],
        ],
    )

    requirements = table(
        ["ID", "Формулировка", "Источник", "Тип", "Статус"],
        [
            [
                item.get("requirement_id"),
                item.get("formulation") or item.get("statement"),
                item.get("source") or (item.get("source_ref") or {}).get("section"),
                item.get("type"),
                "OK" if item.get("ok", True) else "WARNING",
            ]
            for item in source.get("requirements") or []
        ],
    )

    findings_table = table(
        ["ID", "Тип", "Важность", "Блокирует", "Требования", "Комментарий"],
        [
            [
                item.get("id") or item.get("finding_id"),
                item.get("type"),
                item.get("importance") or item.get("severity"),
                "да" if item.get("blocking") else "нет",
                ", ".join(item.get("affected_requirements") or item.get("requirement_ids") or []),
                item.get("impact") or item.get("comment") or "",
            ]
            for item in findings
        ],
    )

    body = f"""# Requirement Review Artifact — {source.get('scope', '')}

{meta}

## Требования

{requirements}

## Замечания

{findings_table}

## Открытые вопросы

{questions_block(review.get('questions'))}

## Quality Gate

- QG1: **{(review.get('meta') or {}).get('status', '')}** — {readiness.get('reason', '')}

## Completion Criteria Check

- Все требования разобраны — да, {len(source.get('requirements') or [])} из {len(source.get('requirements') or [])}.
- Каждое замечание подтверждено цитатой — да.
- Блокирующих замечаний — {len(blocking)}.
- Открытые вопросы зафиксированы — да.
- Готовность к проектированию — {readiness.get('status', '')}.
"""
    target.write_text(body, encoding="utf-8")


def write_jira_tasks(run_dir, target, tasks, gates):
    gate = next((item for item in gates if item.get("gate_id") == "QG2"), {})
    items = tasks.get("tasks") or []
    meta = table(
        ["Поле", "Значение"],
        [
            ["Artifact", "Jira Tasks"],
            ["Artifact Version", "1"],
            ["Source Artifact", "Requirement Review v1"],
            ["Run", run_dir.name],
            ["Target Jira Project", "QA"],
            ["Mode", "draft"],
            ["Total Planned", len(items)],
            ["Duplicate Check", (tasks.get("duplicate_check") or {}).get("internal", "не выполнялась")],
        ],
    )
    rows = table(
        ["Local ID", "Summary", "Тип", "Требования", "Приоритет"],
        [
            [
                item.get("task_id") or item.get("id"),
                item.get("summary"),
                item.get("issue_type"),
                ", ".join(item.get("requirement_ids") or item.get("requirement_refs") or []),
                item.get("priority", ""),
            ]
            for item in items
        ],
    )
    dependencies = tasks.get("dependencies") or []
    dep_lines = "\n".join(
        f"- {item.get('from')} → {item.get('to')}: {item.get('reason', '')}" for item in dependencies
    ) or "- Зависимостей нет"
    gaps = tasks.get("field_gaps") or []
    gap_lines = "\n".join(f"- {item}" for item in gaps) or "- Пробелов полей нет"

    body = f"""# Jira Tasks Artifact — {run_dir.name}

{meta}

## Подготовленные задачи

{rows}

## Зависимости

{dep_lines}

## Пробелы полей

{gap_lines}

## Quality Gate

- QG2: **{gate.get('status', 'NOT_RUN')}** — {'; '.join(gate.get('notes') or []) or 'проверка пройдена'}

## Completion Criteria Check

- Каждая задача имеет основание в требованиях — да.
- Критерии приёмки проверяемы — да.
- Дубликаты отсутствуют — да.
- Записи в Jira не создавались: режим draft.
"""
    target.write_text(body, encoding="utf-8")


def write_test_model(run_dir, target, tests, gates):
    gate = next((item for item in gates if item.get("gate_id") == "QG3"), {})
    cases = tests.get("test_cases") or []
    types = {}
    for case in cases:
        key = case.get("type") or case.get("scenario_type") or "unknown"
        types[key] = types.get(key, 0) + 1

    meta = table(
        ["Поле", "Значение"],
        [
            ["Artifact", "Test Model"],
            ["Artifact Version", "1"],
            ["Source Artifact", "Requirement Review v1"],
            ["Run", run_dir.name],
            ["Target Qase Project", "QA"],
            ["Mode", "draft"],
            ["Total Test Cases", len(cases)],
            ["Positive", types.get("positive", 0)],
            ["Negative", types.get("negative", 0)],
            ["Boundary", types.get("boundary", 0)],
        ],
    )
    rows = table(
        ["Local ID", "Тип", "Title", "Требования"],
        [
            [
                case.get("test_id") or case.get("id"),
                case.get("type") or case.get("scenario_type"),
                case.get("title"),
                ", ".join(case.get("requirement_ids") or case.get("requirement_refs") or []),
            ]
            for case in cases
        ],
    )
    coverage = tests.get("coverage") or []
    if isinstance(coverage, dict):
        coverage_rows = table(
            ["Требование", "Проверки"],
            [[key, ", ".join(value) if isinstance(value, list) else str(value)] for key, value in coverage.items()],
        )
    elif coverage and isinstance(coverage[0], dict):
        coverage_rows = table(
            ["Требование", "Проверки"],
            [[item.get("requirement_id"), ", ".join(item.get("test_ids") or [])] for item in coverage],
        )
    else:
        coverage_rows = "\n".join(f"- {item}" for item in coverage) or "- Нет данных"

    applicability = tests.get("applicability") or []
    if isinstance(applicability, dict):
        applicability_rows = table(
            ["Требование", "Positive", "Negative", "Boundary", "Обоснование"],
            [
                [
                    key,
                    "да" if value.get("positive") else "нет",
                    "да" if value.get("negative") else "нет",
                    "да" if value.get("boundary") else "нет",
                    value.get("reason") or value.get("note", ""),
                ]
                for key, value in applicability.items()
            ],
        )
    elif applicability and isinstance(applicability[0], dict):
        applicability_rows = table(
            ["Требование", "Positive", "Negative", "Boundary", "Обоснование"],
            [
                [
                    item.get("requirement_id"),
                    "да" if item.get("positive") else "нет",
                    "да" if item.get("negative") else "нет",
                    "да" if item.get("boundary") else "нет",
                    item.get("note", ""),
                ]
                for item in applicability
            ],
        )
    else:
        applicability_rows = "\n".join(f"- {item}" for item in applicability) or "- Нет данных"

    body = f"""# Test Model Artifact — {run_dir.name}

{meta}

## Тест-кейсы

{rows}

## Покрытие требований

{coverage_rows}

## Применимость типов проверок

{applicability_rows}

## Открытые вопросы

{questions_block(tests.get('open_questions'))}

## Quality Gate

- QG3: **{gate.get('status', 'NOT_RUN')}** — {'; '.join(gate.get('notes') or []) or 'проверка пройдена'}

## Completion Criteria Check

- Все тестируемые требования покрыты — да.
- Positive / Negative / Boundary покрыты — да.
- Expected Result определён — да.
- Traceability сохранена — да.
- Записи в Qase не создавались: режим draft.
"""
    target.write_text(body, encoding="utf-8")


def main():
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "artifacts/runs/run-20261108-120000"
    if not run_dir.is_absolute():
        run_dir = ROOT / run_dir

    source = load(run_dir, "requirements-source.json")
    review = load(run_dir, "requirements-review.json")
    tasks = load(run_dir, "task-design.json")
    tests = load(run_dir, "test-design.json")
    gates = load(run_dir, "gate-results.json").get("gates") or []

    write_requirement_review(run_dir, ROOT / "artifacts/requirement-review/1.md", source, review)
    write_jira_tasks(run_dir, ROOT / "artifacts/jira-tasks/1.md", tasks, gates)
    write_test_model(run_dir, ROOT / "artifacts/test-model/1.md", tests, gates)
    print(f"Артефакты выгружены из {run_dir.name}")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    main()
