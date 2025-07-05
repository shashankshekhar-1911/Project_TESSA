import requests
import os

ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN")
ZENDESK_EMAIL = os.getenv("ZENDESK_EMAIL")
ZENDESK_TOKEN = os.getenv("ZENDESK_TOKEN")

def fetch_zendesk_tickets():
    url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/tickets.json"
    auth = (f"{ZENDESK_EMAIL}/token", ZENDESK_TOKEN)
    headers = {"Content-Type": "application/json"}
    resp = requests.get(url, auth=auth, headers=headers, timeout=20)
    resp.raise_for_status()
    tickets = resp.json().get("tickets", [])
    result = []
    for t in tickets:
        result.append({
            "id": t["id"],
            "subject": t.get("subject", ""),
            "description": t.get("description", ""),
            "status": t.get("status", ""),
            "priority": t.get("priority", ""),
            "created_at": t.get("created_at", None),
            "updated_at": t.get("updated_at", None),
            "requester": str(t.get("requester_id", "")),
            "assignee": str(t.get("assignee_id", "")),
            "type": t.get("type", ""),
            "tags": ",".join(t.get("tags", [])),
        })
    return result
