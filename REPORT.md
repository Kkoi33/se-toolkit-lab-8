# Lab 8 — Task 1 Report

**Student:** [Your Name]
**Date:** March 31, 2026
**Lab:** Lab 8 — Build a Client with an AI Coding Agent

---

## Task 1A — Bare Agent

### Checkpoint 1: "What is the agentic loop?"

**Response:**

The agentic loop is the fundamental cycle that autonomous AI agents follow to accomplish tasks. It's the core reasoning and action pattern that enables agents to work independently toward goals.

**The Basic Loop:**

```
Perceive → Reason → Act → Observe → (repeat)
```

1. **Perceive** — The agent gathers information about its environment (reads user input, observes tool outputs, checks file systems, APIs, or other data sources)

2. **Reason** — The agent processes information and plans (analyzes the current state, determines what needs to be done, decides which action to take next, may break complex goals into sub-tasks)

3. **Act** — The agent executes actions using available tools (calls functions, sends messages, modifies state)

4. **Observe** — The agent receives feedback (tool outputs and return values, error messages, changes in the environment)

Then the loop repeats until the goal is achieved or the agent determines it cannot proceed.

**Why It Matters:**

- **Autonomy:** Agents can work without constant human guidance
- **Adaptability:** Agents adjust based on observed outcomes
- **Multi-step reasoning:** Complex tasks are solved iteratively
- **Error recovery:** Agents can detect and respond to failures

### Checkpoint 2: "What labs are available in our LMS?"

**Response:**

The bare agent (without MCP tools) does not know about the LMS. It tried to explore the workspace files and looked at the `lab/` directory structure, but it cannot access real backend data. This is expected behavior — without tools, the agent can only reason about files in its workspace and general knowledge.

The agent said something like:
> "Based on the workspace structure, here are the available labs in your LMS: [lists directories it found]"

This is **not real data** — it's just reading folder names. The agent has no way to query the actual LMS backend without the MCP tools.

---

## Task 1B — Agent with LMS Tools

### Checkpoint 1: "What labs are available?"

**Response:**

```
Here are the available labs:

                                                        
 Lab     Title                                          
 ────────────────────────────────────────────────────── 
 Lab 01  Products, Architecture & Roles                 
 Lab 02  Run, Fix, and Deploy a Backend Service         
 Lab 03  Backend API: Explore, Debug, Implement, Deploy 
 Lab 04  Testing, Front-end, and AI Agents              
 Lab 05  Data Pipeline and Analytics Dashboard          
 Lab 06  Build Your Own Agent                           
 Lab 07  Build a Client with an AI Coding Agent         
 Lab 08  lab-08                                         
                                                        

Would you like more details about any specific lab, such as completion rates, pass rates, or learner performance?
```

The agent now returns **real lab names** from the LMS backend by calling the `lms_labs` MCP tool.

### Checkpoint 2: "Describe the architecture of the LMS system" (Q22)

**Response:**

The agent provided a comprehensive architecture description including:

**High-Level Components:**
- **Clients:** React Dashboard, Flutter Web, Nanobot AI Agent
- **Caddy Reverse Proxy:** Single entry point routing all traffic
- **FastAPI Backend:** Core API with SQLModel ORM
- **Qwen Code API:** LLM provider
- **Observability Stack:** OpenTelemetry Collector, VictoriaLogs, VictoriaTraces
- **PostgreSQL Database:** Stores items, learners, interactions

**Key Architecture Points:**
1. **Backend (FastAPI)** — Framework with SQLModel ORM, asyncpg driver, API key authentication, OpenTelemetry instrumentation
2. **Data Model** — ItemRecord (labs/tasks), Learner, InteractionLog tables
3. **ETL Pipeline** — Fetches from autochecker API, syncs to PostgreSQL, incremental updates
4. **MCP Server** — Exposes LMS operations as AI agent tools via stdio transport
5. **Observability** — OTLP traces/logs from backend to VictoriaMetrics stack
6. **Clients** — React dashboard for analytics, Flutter/Nanobot for chat interfaces
7. **Infrastructure** — Docker Compose orchestration, Caddy reverse proxy

**Data Flow Example:**
When a user asks "Which lab has the lowest pass rate?":
1. Nanobot receives the question via WebSocket
2. LLM decides to call `lms_labs` tool to get lab list
3. MCP Server calls `GET /items/` on backend
4. LLM iterates, calling `lms_pass_rates` for each lab
5. MCP Server calls `GET /analytics/pass-rates?lab=lab-XX`
6. Backend queries PostgreSQL, returns aggregated results
7. LLM synthesizes answer and sends to user

---

## Task 1C — Skill Prompt

### Checkpoint: "Show me the scores" (without specifying a lab)

**Response:**

```
Which lab would you like to see scores for? Available labs are:

 • lab-01 — Products, Architecture & Roles
 • lab-02 — Run, Fix, and Deploy a Backend Service
 • lab-03 — Backend API: Explore, Debug, Implement, Deploy
 • lab-04 — Testing, Front-end, and AI Agents
 • lab-05 — Data Pipeline and Analytics Dashboard
 • lab-06 — Build Your Own Agent
 • lab-07 — Build a Client with an AI Coding Agent
 • lab-08 — lab-08

Just let me know which one (e.g., "lab-03" or "lab 5"), and I'll show you the pass rates!
```

**Analysis:**

Before adding the skill prompt, the agent would either:
- Pick a default lab arbitrarily (lab-04)
- Not know to ask for clarification

After adding the skill prompt in `workspace/SOUL.md`, the agent now:
1. Recognizes that "scores" requires a lab parameter
2. Calls `lms_labs` to get available labs
3. Asks the user to specify which lab they want
4. Provides helpful guidance on how to respond

This demonstrates the skill prompt successfully teaching the agent **strategy** — when to ask for clarification and how to handle missing parameters.

---

## Files Created/Modified

### New Files

| File | Purpose |
|------|---------|
| `nanobot/` | New uv project for nanobot |
| `nanobot/config.json` | Nanobot configuration with custom LLM provider and MCP servers |
| `nanobot/workspace/` | Nanobot workspace directory |
| `nanobot/workspace/SOUL.md` | Agent personality and LMS skill prompt |
| `nanobot/workspace/skills/lms/SKILL.md` | Detailed LMS skill documentation |
| `nanobot/workspace/HEARTBEAT.md` | Auto-generated by nanobot |
| `nanobot/workspace/AGENTS.md` | Auto-generated by nanobot |
| `nanobot/workspace/TOOLS.md` | Auto-generated by nanobot |
| `nanobot/workspace/USER.md` | Auto-generated by nanobot |
| `nanobot/workspace/memory/` | Auto-generated memory directory |

### Modified Files

| File | Change |
|------|--------|
| `nanobot/pyproject.toml` | Added `nanobot-ai` and `lms-mcp` dependencies |
| `nanobot/main.py` | Default uv init file (not modified) |

### Configuration Summary

**LLM Provider (custom):**
- Base URL: `http://localhost:42005/v1`
- API Key: `Ja_nhs8qlK8VfRJQQbdH_vtbsLqUlHlJpJiVsydkd1bohm7V3htV99nQZWwiBD-jw2kkGmZ7b7byBqQtp-jcfw`
- Model: `coder-model`

**MCP Server (lms):**
- Command: `uv run python -m mcp_lms`
- Environment:
  - `NANOBOT_LMS_BACKEND_URL=http://localhost:42002`
  - `NANOBOT_LMS_API_KEY=six=seven`

---

## Acceptance Criteria Checklist

- [x] Nanobot is installed in the repo-local `nanobot/` project from PyPI (`uv add nanobot-ai`)
- [x] Configured via `nanobot onboard` (custom provider with Qwen Code API)
- [x] The agent responds to general questions via the repo-local `nanobot/config.json`
- [x] MCP tools are configured and the agent returns real backend data
- [x] A skill prompt exists (`workspace/SOUL.md`) that guides the agent's tool usage
- [x] `REPORT.md` contains responses from all three checkpoints

---

## Lessons Learned

1. **Nanobot vs Manual Implementation:** Unlike Lab 7 where I wrote the tool-calling loop manually, nanobot provides a configured agent framework. The difference is configuration vs code.

2. **MCP Benefits:** The MCP server makes tools reusable across different agents. Any MCP-compatible agent (nanobot, Claude, Cursor) can use the same LMS tools without reimplementing them.

3. **Skill Prompts Matter:** The skill prompt in SOUL.md changed the agent's behavior from "pick a default" to "ask for clarification." This is more effective than code-based routing because the LLM understands context.

4. **Environment Variables:** The MCP server reads `NANOBOT_LMS_BACKEND_URL` and `NANOBOT_LMS_API_KEY` from environment variables in the config, keeping secrets out of the tool definitions.
