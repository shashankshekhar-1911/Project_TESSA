import requests
import os

JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

def fetch_jira_tickets():
    url = f"https://{JIRA_DOMAIN}/rest/api/2/search?jql=project=YOURPROJECTKEY"
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {"Accept": "application/json"}
    resp = requests.get(url, auth=auth, headers=headers, timeout=20)
    resp.raise_for_status()
    issues = resp.json().get("issues", [])
    result = []
    for issue in issues:
        fields = issue["fields"]
        result.append({
            "id": int(issue["id"]),
            "subject": fields.get("summary", ""),
            "description": fields.get("description", ""),
            "status": fields.get("status", {}).get("name", ""),
            "priority": fields.get("priority", {}).get("name", ""),
            "created_at": fields.get("created", None),
            "updated_at": fields.get("updated", None),
            "requester": str(fields.get("reporter", {}).get("displayName", "")),
            "assignee": str(fields.get("assignee", {}).get("displayName", "")) if fields.get("assignee") else "",
            "type": fields.get("issuetype", {}).get("name", ""),
            "tags": "",  # Add tag extraction logic if needed
        })
    return result
