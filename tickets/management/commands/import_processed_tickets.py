import pandas as pd
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from tickets.models import Ticket
import numpy as np


class Command(BaseCommand):
    help = 'Import processed tickets from zendesk_tickets_processed.xlsx'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default='zendesk_tickets_processed.xlsx',
                          help='Path to the Excel file (default: zendesk_tickets_processed.xlsx)')
        parser.add_argument('--dry-run', action='store_true',
                          help='Perform a dry run without actually saving data')

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']
        
        self.stdout.write(f"Reading data from {file_path}...")
        
        try:
            df = pd.read_excel(file_path)
            self.stdout.write(f"Found {len(df)} tickets to import")
            
            if dry_run:
                self.stdout.write(self.style.WARNING("DRY RUN MODE - No data will be saved"))
            
            imported_count = 0
            skipped_count = 0
            
            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        # Handle JSON fields
                        via_data = self.parse_json_field(row.get('via'))
                        tags_data = self.parse_json_field(row.get('tags'))
                        collaborator_ids_data = self.parse_json_field(row.get('collaborator_ids'))
                        follower_ids_data = self.parse_json_field(row.get('follower_ids'))
                        email_cc_ids_data = self.parse_json_field(row.get('email_cc_ids'))
                        sharing_agreement_ids_data = self.parse_json_field(row.get('sharing_agreement_ids'))
                        followup_ids_data = self.parse_json_field(row.get('followup_ids'))
                        satisfaction_rating_data = self.parse_json_field(row.get('satisfaction_rating'))
                        
                        # Handle datetime fields
                        created_at = self.parse_datetime(row.get('created_at'))
                        updated_at = self.parse_datetime(row.get('updated_at'))
                        due_at = self.parse_datetime(row.get('due_at'))
                        
                        # Handle nullable integer fields
                        def safe_int(value):
                            if pd.isna(value) or value == '':
                                return None
                            return int(value) if not pd.isna(value) else None
                        
                        def safe_str(value):
                            if pd.isna(value) or value == '':
                                return None
                            return str(value) if not pd.isna(value) else None
                        
                        def safe_bool(value):
                            if pd.isna(value):
                                return False
                            return bool(value)
                        
                        # Create ticket data
                        ticket_data = {
                            'ticket_id': safe_int(row.get('ticket_id')),
                            'zendesk_url': safe_str(row.get('zendesk_url')),
                            'external_id': safe_str(row.get('external_id')),
                            'via': via_data,
                            'created_at': created_at,
                            'updated_at': updated_at,
                            'generated_timestamp': safe_int(row.get('generated_timestamp')),
                            'type': safe_str(row.get('type')),
                            'subject': str(row.get('subject', '')),
                            'raw_subject': safe_str(row.get('raw_subject')),
                            'description': str(row.get('description', '')),
                            'priority': str(row.get('priority', 'normal')),
                            'status': str(row.get('status', 'new')),
                            'recipient': safe_str(row.get('recipient')),
                            'requester_id': safe_int(row.get('requester_id')),
                            'submitter_id': safe_int(row.get('submitter_id')),
                            'assignee_id': safe_int(row.get('assignee_id')),
                            'organization_id': safe_int(row.get('organization_id')),
                            'group_id': safe_int(row.get('group_id')),
                            'collaborator_ids': collaborator_ids_data,
                            'follower_ids': follower_ids_data,
                            'email_cc_ids': email_cc_ids_data,
                            'sharing_agreement_ids': sharing_agreement_ids_data,
                            'followup_ids': followup_ids_data,
                            'forum_topic_id': safe_int(row.get('forum_topic_id')),
                            'problem_id': safe_int(row.get('problem_id')),
                            'has_incidents': safe_bool(row.get('has_incidents')),
                            'is_public': safe_bool(row.get('is_public')),
                            'due_at': due_at,
                            'tags': tags_data,
                            'satisfaction_rating': satisfaction_rating_data,
                                                    'custom_status_id': safe_int(row.get('custom_status_id')),
                        'encoded_id': safe_str(row.get('encoded_id')),
                        'ticket_form_id': safe_int(row.get('ticket_form_id')),
                            'brand_id': safe_int(row.get('brand_id')),
                            'allow_channelback': safe_bool(row.get('allow_channelback')),
                            'allow_attachments': safe_bool(row.get('allow_attachments')),
                            'from_messaging_channel': safe_bool(row.get('from_messaging_channel')),
                            'source_channel': safe_str(row.get('source_channel')),
                            'product': safe_str(row.get('product')),
                            'support_theme': safe_str(row.get('support_theme')),
                            'summary': safe_str(row.get('summary')),
                            'severity': safe_str(row.get('severity')),
                            'ticket_type': safe_str(row.get('ticket_type')),
                            'interface_affected': safe_str(row.get('interface_affected')),
                            'code_change': safe_str(row.get('code_change')),
                            'module': safe_str(row.get('module')),
                            'workaround': safe_str(row.get('workaround')),
                            'effort_aidash': safe_str(row.get('effort_aidash')),
                            'urgency': safe_str(row.get('urgency')),
                        }
                        
                        if not dry_run:
                            # Check if ticket already exists
                            if Ticket.objects.filter(ticket_id=ticket_data['ticket_id']).exists():
                                self.stdout.write(f"Skipping duplicate ticket ID: {ticket_data['ticket_id']}")
                                skipped_count += 1
                                continue
                            
                            ticket = Ticket.objects.create(**ticket_data)
                            imported_count += 1
                            
                            if imported_count % 50 == 0:
                                self.stdout.write(f"Imported {imported_count} tickets...")
                        else:
                            imported_count += 1
                            if imported_count % 50 == 0:
                                self.stdout.write(f"Processed {imported_count} tickets (dry run)...")
                    
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error processing row {index}: {str(e)}")
                        )
                        skipped_count += 1
                        continue
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f"DRY RUN COMPLETE: Would import {imported_count} tickets, skip {skipped_count}")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully imported {imported_count} tickets, skipped {skipped_count}")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error reading file {file_path}: {str(e)}")
            )

    def parse_json_field(self, value):
        """Parse JSON-like string fields into proper JSON objects"""
        if pd.isna(value) or value == '':
            return None
        
        if isinstance(value, str):
            try:
                # Handle string representations of lists and dicts
                if value in ['[]', '{}', 'nan']:
                    return None
                
                # Replace single quotes with double quotes for JSON parsing
                value = value.replace("'", '"')
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                # If parsing fails, return the original string
                return value
        
        return value

    def parse_datetime(self, value):
        """Parse datetime strings into datetime objects"""
        if pd.isna(value) or value == '':
            return None
        
        if isinstance(value, str):
            try:
                # Handle ISO format datetime strings
                if 'T' in value and 'Z' in value:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        
        return value 