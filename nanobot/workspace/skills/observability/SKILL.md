# Observability Skill

You have access to observability tools that let you query logs and traces from the LMS system.

## Available Tools

### Log Tools (VictoriaLogs)

- **`logs_search`** — Search logs using LogsQL query
  - `query`: LogsQL query string (use "*" for all logs, or filter like `_stream:{service="Learning Management Service"} AND level:error`)
  - `limit`: Max results to return (default 10)

- **`logs_error_count`** — Count errors per service over a time window
  - `service`: Service name to filter (use "*" for all services)
  - `minutes`: Time window in minutes (default 60)

### Trace Tools (VictoriaTraces)

- **`traces_list`** — List recent traces for a service
  - `service`: Service name (default "Learning Management Service")
  - `limit`: Max traces to return (default 5)

- **`traces_get`** — Fetch a specific trace by ID
  - `trace_id`: Trace ID to fetch

## When to Use These Tools

### User asks about errors
When the user asks "Any errors in the last hour?" or "What errors occurred?":
1. Call `logs_error_count` with `service="*"` and `minutes=60`
2. If errors are found, call `logs_search` with `query="level:error OR severity:ERROR"` to get details
3. Summarize findings: which services had errors, how many, and what the errors were

### User asks about a specific service
When the user asks "Is the backend working?" or "Any issues with the database?":
1. Call `logs_search` with a query filtering by that service
2. Look for error-level logs or exceptions
3. Report the status

### User asks to debug a problem
When the user reports an issue or asks "What went wrong?":
1. Call `logs_search` with `query="level:error OR severity:ERROR OR exception.type:*"` and `limit=20`
2. Look for recent errors and their stack traces
3. If you find a trace_id in the error logs, call `traces_get` to see the full trace
4. Explain what failed and where

### User asks about performance
When the user asks "Why is it slow?" or "Show me trace data":
1. Call `traces_list` to see recent traces
2. Look for traces with long durations
3. Call `traces_get` on slow traces to see which spans took the longest
4. Report which operations are slow

## Response Style

- **Be concise**: Don't dump raw JSON. Summarize findings in plain language.
- **Include counts**: "Found 3 errors in the last hour" is better than listing errors without context.
- **Highlight patterns**: "All errors are database connection failures" helps the user understand the root cause.
- **Offer next steps**: "Would you like me to fetch the full trace for the most recent error?"

## Example Interactions

**User**: "Any errors in the last hour?"

**You**: (Call `logs_error_count` with service="*", minutes=60)
"I found 5 errors in the last hour:
- 3 errors in 'Learning Management Service' (database connection failures)
- 2 errors in 'backend' (timeout exceptions)

The most recent error was a database connection failure at 08:23. Would you like me to show the full error details?"

**User**: "Show me recent traces"

**You**: (Call `traces_list` with service="Learning Management Service")
"Here are the 5 most recent traces for the Learning Management Service:
- Trace abc123: 12 spans, 450ms duration
- Trace def456: 8 spans, 120ms duration
- ...

The first trace took the longest. Would you like me to fetch its details?"
