"""Entrypoint for nanobot Docker deployment.

Resolves environment variables into the config at runtime, then launches nanobot gateway.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Resolve environment variables and launch nanobot gateway."""
    # Paths
    config_dir = Path("/app/nanobot")
    config_file = config_dir / "config.json"
    resolved_config = config_dir / "config.resolved.json"
    workspace_dir = config_dir / "workspace"
    venv_bin = Path("/app/.venv/bin")  # venv is at /app/.venv, not in nanobot dir

    if not config_file.exists():
        print(f"Error: Config file not found: {config_file}", file=sys.stderr)
        sys.exit(1)

    # Load the base config
    with open(config_file) as f:
        config = json.load(f)

    # Resolve LLM provider settings from environment
    llm_api_key = os.environ.get("LLM_API_KEY", "")
    llm_api_base_url = os.environ.get("LLM_API_BASE_URL", "")
    llm_api_model = os.environ.get("LLM_API_MODEL", "coder-model")

    if "providers" not in config:
        config["providers"] = {}
    if "custom" not in config["providers"]:
        config["providers"]["custom"] = {}

    if llm_api_key:
        config["providers"]["custom"]["apiKey"] = llm_api_key
    if llm_api_base_url:
        config["providers"]["custom"]["apiBase"] = llm_api_base_url

    # Set default model in agents
    if "agents" not in config:
        config["agents"] = {"defaults": {}}
    if "defaults" not in config["agents"]:
        config["agents"]["defaults"] = {}
    config["agents"]["defaults"]["model"] = llm_api_model

    # Resolve gateway settings
    gateway_address = os.environ.get("NANOBOT_GATEWAY_CONTAINER_ADDRESS", "0.0.0.0")
    gateway_port = os.environ.get("NANOBOT_GATEWAY_CONTAINER_PORT", "18790")

    if "gateway" not in config:
        config["gateway"] = {}
    config["gateway"]["host"] = gateway_address
    config["gateway"]["port"] = int(gateway_port)

    # Resolve webchat channel settings
    webchat_address = os.environ.get("NANOBOT_WEBCHAT_CONTAINER_ADDRESS", "0.0.0.0")
    webchat_port = os.environ.get("NANOBOT_WEBCHAT_CONTAINER_PORT", "8765")
    access_key = os.environ.get("NANOBOT_ACCESS_KEY", "")

    if "channels" not in config:
        config["channels"] = {}
    if "webchat" not in config["channels"]:
        config["channels"]["webchat"] = {}
    config["channels"]["webchat"]["enabled"] = True
    config["channels"]["webchat"]["host"] = webchat_address
    config["channels"]["webchat"]["port"] = int(webchat_port)
    if access_key:
        config["channels"]["webchat"]["accessKey"] = access_key
    config["channels"]["webchat"]["allowFrom"] = ["*"]

    # Resolve MCP server environment variables
    lms_backend_url = os.environ.get("NANOBOT_LMS_BACKEND_URL", "")
    lms_api_key = os.environ.get("NANOBOT_LMS_API_KEY", "")

    if "tools" not in config:
        config["tools"] = {}
    if "mcpServers" not in config["tools"]:
        config["tools"]["mcpServers"] = {}
    if "lms" not in config["tools"]["mcpServers"]:
        config["tools"]["mcpServers"]["lms"] = {}

    # Use full path to uv in the venv
    config["tools"]["mcpServers"]["lms"]["command"] = "/app/.venv/bin/uv"
    config["tools"]["mcpServers"]["lms"]["args"] = ["run", "python", "-m", "mcp_lms"]

    if "env" not in config["tools"]["mcpServers"]["lms"]:
        config["tools"]["mcpServers"]["lms"]["env"] = {}
    if lms_backend_url:
        config["tools"]["mcpServers"]["lms"]["env"]["NANOBOT_LMS_BACKEND_URL"] = lms_backend_url
    if lms_api_key:
        config["tools"]["mcpServers"]["lms"]["env"]["NANOBOT_LMS_API_KEY"] = lms_api_key

    # Add observability MCP server if not already present
    if "observability" not in config["tools"]["mcpServers"]:
        config["tools"]["mcpServers"]["observability"] = {
            "command": "/app/.venv/bin/uv",
            "args": ["run", "python", "-m", "mcp_lms.observability"],
            "env": {
                "VICTORIALOGS_URL": "http://victorialogs:9428",
                "VICTORIATRACES_URL": "http://victoriatraces:10428"
            }
        }

    # Write the resolved config
    with open(resolved_config, "w") as f:
        json.dump(config, f, indent=2)

    print(f"Resolved config written to {resolved_config}")

    # Set PATH to include venv bin
    env = os.environ.copy()
    env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
    env["PYTHONPATH"] = str(config_dir)

    # Launch nanobot gateway
    nanobot_exe = venv_bin / "nanobot"
    if not nanobot_exe.exists():
        print(f"Error: nanobot executable not found at {nanobot_exe}", file=sys.stderr)
        print(f"Contents of {venv_bin}:", file=sys.stderr)
        if venv_bin.exists():
            for f in venv_bin.iterdir():
                print(f"  {f}", file=sys.stderr)
        sys.exit(1)

    subprocess.run([str(nanobot_exe), "gateway", "--config", str(resolved_config), "--workspace", str(workspace_dir)], env=env)


if __name__ == "__main__":
    main()
