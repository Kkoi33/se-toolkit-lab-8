"""Observability MCP tools for VictoriaLogs and VictoriaTraces."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

server = Server("observability")

# Configuration from environment
VICTORIALOGS_URL = os.environ.get("VICTORIALOGS_URL", "http://localhost:42010")
VICTORIATRACES_URL = os.environ.get("VICTORIATRACES_URL", "http://localhost:42011")


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class _LogsSearchArgs(BaseModel):
    query: str = Field(
        default="*",
        description="LogsQL query string. Use '*' for all logs, or filter by service/level.",
    )
    limit: int = Field(default=10, ge=1, le=100, description="Max results to return.")


class _LogsErrorCountArgs(BaseModel):
    service: str = Field(
        default="*",
        description="Service name to filter (use '*' for all services).",
    )
    minutes: int = Field(
        default=60, ge=1, description="Time window in minutes to search."
    )


class _TracesListArgs(BaseModel):
    service: str = Field(
        default="Learning Management Service",
        description="Service name to filter traces.",
    )
    limit: int = Field(default=5, ge=1, le=20, description="Max traces to return.")


class _TracesGetArgs(BaseModel):
    trace_id: str = Field(description="Trace ID to fetch.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _http_get(url: str, params: dict[str, Any] | None = None) -> Any:
    """Make an async HTTP GET request and return parsed JSON."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def _text(data: Any) -> list[TextContent]:
    """Serialize data to a JSON text block."""
    if isinstance(data, (dict, list)):
        text = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        text = str(data)
    return [TextContent(type="text", text=text)]


# ---------------------------------------------------------------------------
# Log tool handlers
# ---------------------------------------------------------------------------


async def _logs_search(args: _LogsSearchArgs) -> list[TextContent]:
    """Search logs using VictoriaLogs LogsQL query."""
    url = f"{VICTORIALOGS_URL}/select/logsql/query"
    params = {"query": args.query, "limit": args.limit}
    try:
        # VictoriaLogs returns newline-delimited JSON
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            lines = resp.text.strip().split("\n")
            results = []
            for line in lines:
                if line.strip():
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        results.append({"raw": line})
        return _text({"query": args.query, "results": results[: args.limit]})
    except Exception as e:
        return _text({"error": str(e), "query": args.query})


async def _logs_error_count(args: _LogsErrorCountArgs) -> list[TextContent]:
    """Count errors per service over a time window."""
    # Build LogsQL query for errors
    if args.service == "*":
        query = "level:error OR severity:ERROR OR exception.type:*"
    else:
        query = f'_stream:{{service="{args.service}"}} AND (level:error OR severity:ERROR)'

    url = f"{VICTORIALOGS_URL}/select/logsql/query"
    params = {"query": query, "limit": 1000}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            lines = resp.text.strip().split("\n")
            errors = []
            service_counts: dict[str, int] = {}
            for line in lines:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        errors.append(entry)
                        # Extract service name
                        svc = entry.get("service.name", entry.get("service", "unknown"))
                        service_counts[svc] = service_counts.get(svc, 0) + 1
                    except json.JSONDecodeError:
                        pass

            return _text({
                "query": query,
                "total_errors": len(errors),
                "by_service": service_counts,
                "time_window_minutes": args.minutes,
            })
    except Exception as e:
        return _text({"error": str(e)})


# ---------------------------------------------------------------------------
# Trace tool handlers
# ---------------------------------------------------------------------------


async def _traces_list(args: _TracesListArgs) -> list[TextContent]:
    """List recent traces for a service."""
    # VictoriaTraces Jaeger-compatible API
    url = f"{VICTORIATRACES_URL}/api/traces"
    params = {"service": args.service, "limit": args.limit}

    try:
        data = await _http_get(url, params)
        # Jaeger API returns {"data": [...]}
        traces = data.get("data", []) if isinstance(data, dict) else []
        simplified = []
        for trace in traces[: args.limit]:
            simplified.append({
                "trace_id": trace.get("traceID", "unknown"),
                "spans": len(trace.get("spans", [])),
                "start_time": trace.get("startTime", 0),
                "duration": trace.get("duration", 0),
            })
        return _text({"service": args.service, "traces": simplified})
    except Exception as e:
        return _text({"error": str(e), "service": args.service})


async def _traces_get(args: _TracesGetArgs) -> list[TextContent]:
    """Fetch a specific trace by ID."""
    url = f"{VICTORIATRACES_URL}/api/traces/{args.trace_id}"
    try:
        data = await _http_get(url)
        trace_data = data.get("data", [])
        if not trace_data:
            return _text({"error": f"Trace not found: {args.trace_id}"})

        trace = trace_data[0] if isinstance(trace_data, list) else trace_data
        spans = trace.get("spans", [])
        span_summary = []
        for span in spans:
            span_summary.append({
                "span_id": span.get("spanID", "unknown"),
                "operation": span.get("operationName", "unknown"),
                "service": span.get("process", {}).get("serviceName", "unknown"),
                "duration": span.get("duration", 0),
                "tags": len(span.get("tags", [])),
            })

        return _text({
            "trace_id": args.trace_id,
            "trace_duration": trace.get("duration", 0),
            "total_spans": len(spans),
            "spans": span_summary,
        })
    except Exception as e:
        return _text({"error": str(e), "trace_id": args.trace_id})


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_Registry = tuple[type[BaseModel], Callable[..., Awaitable[list[TextContent]]], Tool]

_TOOLS: dict[str, _Registry] = {}


def _register(
    name: str,
    description: str,
    model: type[BaseModel],
    handler: Callable[..., Awaitable[list[TextContent]]],
) -> None:
    schema = model.model_json_schema()
    schema.pop("$defs", None)
    schema.pop("title", None)
    _TOOLS[name] = (
        model,
        handler,
        Tool(name=name, description=description, inputSchema=schema),
    )


_register(
    "logs_search",
    "Search logs using LogsQL query. Use '*' for all logs, or filter like '_stream:{service=\"backend\"} AND level:error'.",
    _LogsSearchArgs,
    _logs_search,
)
_register(
    "logs_error_count",
    "Count errors per service over a time window. Returns total errors and breakdown by service.",
    _LogsErrorCountArgs,
    _logs_error_count,
)
_register(
    "traces_list",
    "List recent traces for a service. Returns trace IDs, span counts, and durations.",
    _TracesListArgs,
    _traces_list,
)
_register(
    "traces_get",
    "Fetch a specific trace by ID. Returns span hierarchy and timing information.",
    _TracesGetArgs,
    _traces_get,
)


# ---------------------------------------------------------------------------
# MCP handlers
# ---------------------------------------------------------------------------


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [entry[2] for entry in _TOOLS.values()]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    entry = _TOOLS.get(name)
    if entry is None:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    model_cls, handler, _ = entry
    try:
        args = model_cls.model_validate(arguments or {})
        return await handler(args)
    except Exception as exc:
        return [TextContent(type="text", text=f"Error: {type(exc).__name__}: {exc}")]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
