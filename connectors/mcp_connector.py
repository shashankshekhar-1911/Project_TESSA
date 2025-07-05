import requests
import os

USE_MCP = os.getenv("USE_MCP", "False") == "True"
MCP_URL = os.getenv("MCP_URL")
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN")
MCP_TIMEOUT = int(os.getenv("MCP_TIMEOUT", "10"))

def call_mcp(ticket: dict, endpoint="categorization") -> dict:
    url = MCP_URL
    headers = {"Authorization": f"Bearer {MCP_AUTH_TOKEN}"}
    try:
        resp = requests.post(url, json={**ticket, "endpoint": endpoint}, headers=headers, timeout=MCP_TIMEOUT)
        resp.raise_for_status()
        return {**ticket, **resp.json()}
    except Exception as e:
        print(f"MCP call failed: {e}")
        return ticket

def call_mcp_categorization(ticket: dict) -> dict:
    return call_mcp(ticket, endpoint="categorization")

def call_mcp_prioritization(ticket: dict) -> dict:
    return call_mcp(ticket, endpoint="prioritization")

def call_mcp_resolution(ticket: dict) -> dict:
    return call_mcp(ticket, endpoint="resolution")

def call_mcp_feedback(ticket: dict) -> dict:
    return call_mcp(ticket, endpoint="feedback")
