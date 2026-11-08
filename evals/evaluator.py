#!/usr/bin/env python3
"""Оценка прогона агента по golden dataset.

Использование:
    python evals/evaluator.py artifacts/runs/run-20261108-120000
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "evals" / "dataset" / "golden_dataset.json"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "artifacts/runs/run-20261108-120000"
    if not run_dir.is_absolute():
        run_dir = ROOT / run_dir
    if not run_dir.exists():
        print(f"Каталог прогона не найден: {run_dir}")
        return 1

    dataset = load(DATASET)
    expected = dataset["expectations"]

    source = load(run_dir / "requirements-source.json")
    review = load(run_dir / "requirements-review.json")
    tasks = load(run_dir / "task-design.json")
    tests = load(run_dir / "test-design.json")
    gates = load(run_dir / "gate-results.json")

    requirements = source.get("requirements") or []
    task_items = tasks.get("tasks") or []
    test_items = tests.get("test_cases") or []

    covered = {
        ref
        for case in test_items
        if isinstance(case, dict)
        for ref in (case.get("requirement_ids") or case.get("requirement_refs") or [])
    }
    total = len([item for item in requirements if isinstance(item, dict)])
    coverage = round(100 * len(covered & {item.get("requirement_id") for item in requirements}) / total) if total else 0

    types = Counter(
        case.get("type") or case.get("scenario_type") for case in test_items if isinstance(case, dict)
    )
    findings = [item for item in (review.get("findings") or []) if isinstance(item, dict)]
    blocking = [item for item in findings if item.get("blocking")]
    gate_status = {item.get("gate_id"): item.get("status") for item in gates.get("gates") or []}

    checks = [
        ("requirements_min", len(requirements) >= expected["requirements_min"], len(requirements)),
        ("tasks_min", len(task_items) >= expected["tasks_min"], len(task_items)),
        ("tests_min", len(test_items) >= expected["tests_min"], len(test_items)),
        (
            "required_types",
            all(types.get(name, 0) > 0 for name in expected["required_types"]),
            dict(types),
        ),
        ("coverage_percent_min", coverage >= expected["coverage_percent_min"], coverage),
        (
            "gates_required",
            all(gate_status.get(name) == "PASS" for name in expected["gates_required"]),
            gate_status,
        ),
        (
            "max_blocking_findings",
            len(blocking) <= expected["max_blocking_findings"],
            len(blocking),
        ),
    ]

    print(f"Оценка прогона: {run_dir.name}")
    print(f"Кейс: {dataset['name']}")
    print("-" * 60)
    failed = 0
    for name, ok, actual in checks:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"[{mark}] {name}: {actual}")
    print("-" * 60)
    print(f"Проверок: {len(checks)}, провалено: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    sys.exit(main())
