#!/usr/bin/env python3
"""Проверка, что файл содержит валидный JSON.

Использование:
    python scripts/check_json.py artifacts/<run_id>/requirements-review.json
"""

import json
import sys


def main():
    if len(sys.argv) < 2:
        print("Укажите путь к JSON-файлу")
        return 2
    path = sys.argv[1]
    try:
        with open(path, "r", encoding="utf-8") as handle:
            json.load(handle)
    except FileNotFoundError:
        print(f"MISSING {path}")
        return 1
    except json.JSONDecodeError as error:
        print(f"INVALID {path}: {error}")
        print("Проверьте кавычки, запятые и отсутствие переводов строк внутри строковых значений")
        return 1
    print(f"OK {path}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    sys.exit(main())
