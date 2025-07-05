import pandas as pd
from django.core.management.base import BaseCommand
from tickets.models import Ticket, User, Organization, Comment
from django.utils import timezone
from django.db import transaction

ORG_FILE = "/Users/balaji/Downloads/tessa_backend/zendesk_data/zendesk_organizations.xlsx"
USER_FILE = "/Users/balaji/Downloads/tessa_backend/zendesk_data/zendesk_users.xlsx"
TICKET_FILE = "/Users/balaji/Downloads/tessa_backend/zendesk_data/zendesk_tickets.xlsx"
COMMENT_FILE = "/Users/balaji/Downloads/tessa_backend/zendesk_data/zendesk_comments.xlsx"

def parse_datetime(dt):
    if pd.isnull(dt):
        return None
    try:
        return pd.to_datetime(dt)
    except Exception:
        return None

class Command(BaseCommand):
    help = 'Import Zendesk data into the database'

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            print("Importing Organizations...")
            org_df = pd.read_excel(ORG_FILE)
            org_map = {}
            for _, row in org_df.iterrows():
                org, created = Organization.objects.get_or_create(
                    id=row['id'],
                    defaults={
                        "name": row.get('name', ''),
                        "created_at": parse_datetime(row.get('created_at')),
                        "updated_at": parse_datetime(row.get('updated_at')),
                        "details": row.get('details', '')
                    }
                )
                org_map[org.id] = org

            print("Importing Users...")
            user_df = pd.read_excel(USER_FILE)
            user_map = {}
            for _, row in user_df.iterrows():
                org = org_map.get(row.get('organization_id')) if not pd.isnull(row.get('organization_id')) else None
                email = row.get('email', '')
                
                # Skip users with invalid or missing emails
                if pd.isnull(email) or email == '':
                    print(f"Skipping user with ID {row['id']} due to missing email.")
                    continue
                
                user, created = User.objects.get_or_create(
                    id=row['id'],
                    defaults={
                        "name": row.get('name', ''),
                        "email": email,
                        "role": row.get('role', ''),
                        "created_at": parse_datetime(row.get('created_at')),
                        "updated_at": parse_datetime(row.get('updated_at')),
                        "organization": org,
                        "active": bool(row.get('active', True)),
                        "suspended": bool(row.get('suspended', False)),
                        "timezone": row.get('timezone', ''),
                        "phone": row.get('phone', '')
                    }
                )
                user_map[user.id] = user

            print("Importing Tickets...")
            ticket_df = pd.read_excel(TICKET_FILE)
            ticket_map = {}
            for _, row in ticket_df.iterrows():
                requester = user_map.get(row.get('requester_id')) if not pd.isnull(row.get('requester_id')) else None
                assignee = user_map.get(row.get('assignee_id')) if not pd.isnull(row.get('assignee_id')) else None
                org = org_map.get(row.get('organization_id')) if not pd.isnull(row.get('organization_id')) else None
                ticket, created = Ticket.objects.get_or_create(
                    id=row['id'],
                    defaults={
                        "subject": row.get('subject', ''),
                        "description": row.get('description', ''),
                        "status": row.get('status', ''),
                        "priority": row.get('priority', ''),
                        "created_at": parse_datetime(row.get('created_at')),
                        "updated_at": parse_datetime(row.get('updated_at')),
                        "requester": requester,
                        "assignee": assignee,
                        "organization": org,
                        "type": row.get('type', ''),
                        "tags": row.get('tags', ''),
                    }
                )
                ticket_map[ticket.id] = ticket

            print("Importing Comments...")
            comment_df = pd.read_excel(COMMENT_FILE)
            for _, row in comment_df.iterrows():
                ticket = ticket_map.get(row.get('ticket_id')) if not pd.isnull(row.get('ticket_id')) else None
                author = user_map.get(row.get('author_id')) if not pd.isnull(row.get('author_id')) else None
                if not ticket:
                    continue
                Comment.objects.get_or_create(
                    id=row['id'],
                    defaults={
                        "ticket": ticket,
                        "author": author,
                        "body": row.get('body', ''),
                        "public": bool(row.get('public', True)),
                        "created_at": parse_datetime(row.get('created_at')),
                        "updated_at": parse_datetime(row.get('updated_at')),
                        "attachments": row.get('attachments', ''),
                    }
                )
            print("Data import complete.") 