#!/usr/bin/env python3
"""Проверка артефактов прогона QA-флоу.

Использование:
    python scripts/validate_artifacts.py artifacts/run-001
"""

import json
import sys
from collections import Counter
from pathlib import Path

REQUIRED_FILES = [
    "requirements-source.json",
    "requirements-review.json",
    "task-design.json",
    "test-design.json",
    "traceability.json",
    "gate-results.json",
    "run-manifest.json",
    "final-report.md",
]

META_FIELDS = ["run_id", "baseline_id", "artifact_version", "producer", "created_at", "status"]

results = []


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))


def load(run_dir, filename):
    path = run_dir / filename
    if not path.exists():
        return None
    if filename.endswith(".json"):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return path.read_text(encoding="utf-8")


def require_meta(name, data):
    if not isinstance(data, dict):
        check(f"{name}: читается", False, "файл отсутствует или не JSON")
        return
    meta = data.get("meta", {})
    missing = [field for field in META_FIELDS if field not in meta]
    check(f"{name}: метаданные", not missing, f"нет полей: {missing}" if missing else "все поля на месте")


def main():
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/runs/run-001")
    if not run_dir.exists():
        print(f"Каталог не найден: {run_dir}")
        return 1

    for filename in REQUIRED_FILES:
        check(f"файл {filename}", (run_dir / filename).exists())

    source = load(run_dir, "requirements-source.json")
    review = load(run_dir, "requirements-review.json")
    tasks = load(run_dir, "task-design.json")
    tests = load(run_dir, "test-design.json")
    trace = load(run_dir, "traceability.json")
    gates = load(run_dir, "gate-results.json")
    manifest = load(run_dir, "run-manifest.json")
    report = load(run_dir, "final-report.md")

    for name, data in [
        ("requirements-source", source),
        ("requirements-review", review),
        ("task-design", tasks),
        ("test-design", tests),
        ("traceability", trace),
        ("gate-results", gates),
        ("run-manifest", manifest),
    ]:
        require_meta(name, data)

    if all(isinstance(item, dict) for item in [source, review, tasks, tests, trace, gates]):
        req_ids = [item["requirement_id"] for item in source.get("requirements", []) if isinstance(item, dict)]
        check("уникальность REQ", len(req_ids) == len(set(req_ids)), f"всего {len(req_ids)}")
        check("требования не пустые", len(req_ids) > 0)

        known = set(req_ids)
        task_ids = [item["task_id"] for item in tasks.get("tasks", []) if isinstance(item, dict) and item.get("task_id")]
        test_ids = [
            item["test_id"] for item in tests.get("test_cases", []) if isinstance(item, dict) and item.get("test_id")
        ]
        check("уникальность TASK", len(task_ids) == len(set(task_ids)), f"всего {len(task_ids)}")
        check("уникальность TEST", len(test_ids) == len(set(test_ids)), f"всего {len(test_ids)}")

        scenario_types = Counter(
            case.get("scenario_type") or case.get("type")
            for case in tests.get("test_cases", [])
            if isinstance(case, dict)
        )
        for scenario in ("positive", "negative", "boundary"):
            check(
                f"есть проверки типа {scenario}",
                scenario_types.get(scenario, 0) > 0,
                f"найдено: {scenario_types.get(scenario, 0)}",
            )

        task_refs = {
            ref
            for item in tasks.get("tasks", [])
            if isinstance(item, dict)
            for ref in (item.get("requirement_ids") or [])
        }
        test_refs = {
            ref
            for item in tests.get("test_cases", [])
            if isinstance(item, dict)
            for ref in (item.get("requirement_ids") or [])
        }
        review_refs = {
            item.get("requirement_id")
            for item in review.get("requirements", [])
            if isinstance(item, dict) and item.get("requirement_id")
        }

        check("задачи ссылаются на известные требования", task_refs <= known, f"лишние: {sorted(task_refs - known)}")
        check("тесты ссылаются на известные требования", test_refs <= known, f"лишние: {sorted(test_refs - known)}")
        check("анализ покрывает все требования", review_refs == known, f"разница: {sorted(known ^ review_refs)}")

        task_coverage = set(task_refs)
        test_coverage = set(test_refs)
        check(
            "покрытие задач 100%",
            task_coverage == known,
            f"без задач: {sorted(known - task_coverage)}",
        )
        check(
            "покрытие тестов 100%",
            test_coverage == known,
            f"без тестов: {sorted(known - test_coverage)}",
        )

        rows = trace.get("rows", [])
        trace_reqs = [row.get("requirement_id") for row in rows]
        check("трассируемость покрывает все требования", set(trace_reqs) == known, f"разница: {sorted(known ^ set(trace_reqs))}")
        broken = []
        for row in rows:
            for ref in row.get("task_ids", []):
                if ref not in task_ids:
                    broken.append(ref)
            for ref in row.get("test_ids", []):
                if ref not in test_ids:
                    broken.append(ref)
        check("ссылки трассируемости существуют", not broken, f"битые ссылки: {broken}")

        statuses = {gate.get("gate_id"): gate.get("status") for gate in gates.get("gates", [])}
        expected_gates = {"QG1", "QG2", "QG3", "QG4"}
        check("все ворота описаны", expected_gates <= set(statuses), f"нет: {sorted(expected_gates - set(statuses))}")
        failed = [gate for gate, status in statuses.items() if status != "PASS"]
        check("все ворота пройдены", not failed, f"не пройдены: {failed}")

        artifact_ids = {item.get("artifact_id") for item in manifest.get("artifacts", [])}
        check("манифест содержит ключевые артефакты", len(artifact_ids) >= 4, f"записей: {len(artifact_ids)}")

    check("итоговый отчёт не пустой", bool(report and len(report) > 300))

    print(f"Проверка артефактов: {run_dir}")
    print("-" * 60)
    failed_total = 0
    for name, ok, detail in results:
        mark = "OK  " if ok else "FAIL"
        if not ok:
            failed_total += 1
        suffix = f" - {detail}" if detail and not ok else ""
        print(f"[{mark}] {name}{suffix}")
    print("-" * 60)
    print(f"Всего проверок: {len(results)}, ошибок: {failed_total}")

    if failed_total:
        return 1
    print("Результат: артефакты согласованы")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    sys.exit(main())
