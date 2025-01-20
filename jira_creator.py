import os
import requests
import json
from requests.auth import HTTPBasicAuth


def jira_fields(email_context):
    jira_project_key = os.getenv('JIRA_PROJECT_KEY')
    jira_fields = {
       "fields":{
         "project": {
          "key": jira_project_key
        },
        "summary": email_context["querySummary"],
        "description": email_context["queryDescription"],
        "issuetype":{
          "name": "Task" 
        }
      }
    }
    return jira_fields


def create_ticket(jira_fields):
    email = os.getenv('email')
    api_token = os.getenv('JIRA_API_KEY')
    site_name = os.getenv('SITE_NAME')
    url = f"https://{site_name}/rest/api/2/issue/"
    auth = HTTPBasicAuth(email,api_token)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, auth=auth, headers=headers, json=jira_fields)
    if response.status_code in [200,201]:
      print(response.json())
    else:
      print(f"Failed to create issue: {response.status_code} {response.text}")


