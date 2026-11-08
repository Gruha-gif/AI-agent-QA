#!/usr/bin/env python3
"""Минимальный MCP-сервер для демонстрации QA-флоу без внешних доступов.

Реализует JSON-RPC поверх stdio и три инструмента:
  - confluence_get_page  - читает страницу требований из inputs/confluence
  - jira_create_issue    - записывает задачу в artifacts/published/jira-issues.json
  - qase_create_case     - записывает тест-кейс в artifacts/published/qase-cases.json
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUTS = ROOT / "inputs" / "confluence"
ARTIFACTS = Path(os.environ.get("QA_ARTIFACTS_DIR", "artifacts"))
if not ARTIFACTS.is_absolute():
    ARTIFACTS = ROOT / ARTIFACTS
PUBLISHED = ARTIFACTS / "published"

TOOLS = [
    {
        "name": "confluence_get_page",
        "description": "Возвращает текст страницы требований из локального хранилища.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page": {"type": "string", "description": "Идентификатор страницы или ссылка"}
            },
            "required": ["page"],
        },
    },
    {
        "name": "jira_create_issue",
        "description": "Создаёт задачу в локальном журнале Jira (демо-режим).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_key": {"type": "string"},
                "summary": {"type": "string"},
                "description": {"type": "string"},
                "issue_type": {"type": "string"},
            },
            "required": ["project_key", "summary"],
        },
    },
    {
        "name": "qase_create_case",
        "description": "Создаёт тест-кейс в локальном журнале Qase (демо-режим).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "title": {"type": "string"},
                "suite": {"type": "string"},
                "steps": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["code", "title"],
        },
    },
]


def send(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def tool_result(data):
    return {
        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
        "isError": False,
    }


def tool_error(message):
    return {"content": [{"type": "text", "text": message}], "isError": True}


def read_frontmatter(text):
    meta = {}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip()
            return meta, parts[2].strip()
    return meta, text


def confluence_get_page(arguments):
    page = str(arguments.get("page", "")).strip().lower()
    files = sorted(INPUTS.glob("*.md"))
    if not files:
        return tool_error("Страницы требований не найдены в inputs/confluence")

    chosen = None
    for path in files:
        text = path.read_text(encoding="utf-8")
        meta, _ = read_frontmatter(text)
        haystack = " ".join([path.stem.lower(), meta.get("id", "").lower(), meta.get("title", "").lower()])
        if page and page in haystack:
            chosen = (path, text)
            break
    if chosen is None:
        chosen = (files[0], files[0].read_text(encoding="utf-8"))

    path, text = chosen
    meta, body = read_frontmatter(text)
    return tool_result(
        {
            "page_id": meta.get("id", path.stem),
            "title": meta.get("title", path.stem),
            "version": meta.get("version", "unknown"),
            "source": "local-mock",
            "content": body,
        }
    )


def append_record(filename, record):
    PUBLISHED.mkdir(parents=True, exist_ok=True)
    target = PUBLISHED / filename
    data = []
    if target.exists():
        data = json.loads(target.read_text(encoding="utf-8"))
    data.append(record)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(data)


def jira_create_issue(arguments):
    project = arguments.get("project_key", "QA")
    number = append_record(
        "jira-issues.json",
        {
            "project_key": project,
            "summary": arguments.get("summary", ""),
            "description": arguments.get("description", ""),
            "issue_type": arguments.get("issue_type", "Task"),
        },
    )
    key = f"{project}-{number}"
    return tool_result({"key": key, "url": f"https://jira.example/browse/{key}", "source": "local-mock"})


def qase_create_case(arguments):
    number = append_record(
        "qase-cases.json",
        {
            "code": arguments.get("code", "QA"),
            "title": arguments.get("title", ""),
            "suite": arguments.get("suite", ""),
            "steps": arguments.get("steps", []),
        },
    )
    return tool_result({"id": number, "url": f"https://qase.example/case/{number}", "source": "local-mock"})


def handle_call(name, arguments):
    if name == "confluence_get_page":
        return confluence_get_page(arguments)
    if name == "jira_create_issue":
        return jira_create_issue(arguments)
    if name == "qase_create_case":
        return qase_create_case(arguments)
    return tool_error(f"Неизвестный инструмент: {name}")


def main():
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            request = json.loads(raw)
        except json.JSONDecodeError:
            continue

        method = request.get("method")
        request_id = request.get("id")
        if request_id is None:
            continue

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "qa-mock", "version": "1.0.0"},
            }
            send({"jsonrpc": "2.0", "id": request_id, "result": result})
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            params = request.get("params", {})
            result = handle_call(params.get("name"), params.get("arguments", {}) or {})
            send({"jsonrpc": "2.0", "id": request_id, "result": result})
        elif method == "ping":
            send({"jsonrpc": "2.0", "id": request_id, "result": {}})
        elif method == "shutdown":
            send({"jsonrpc": "2.0", "id": request_id, "result": None})
            break
        else:
            send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Метод не поддерживается: {method}"},
                }
            )


if __name__ == "__main__":
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    main()
