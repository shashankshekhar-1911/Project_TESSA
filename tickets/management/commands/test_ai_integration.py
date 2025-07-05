from django.core.management.base import BaseCommand
from tickets.models import Ticket
from tickets.utils import process_ticket_with_ai, extract_ai_reasoning
from django.utils import timezone
import json


class Command(BaseCommand):
    help = 'Test AI request processor integration with ticket updates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ticket-id',
            type=int,
            help='Specific ticket ID to test AI processing'
        )
        parser.add_argument(
            '--create-test',
            action='store_true',
            help='Create a test ticket for AI processing'
        )
        parser.add_argument(
            '--show-reasoning',
            action='store_true',
            help='Show AI reasoning for field assignments'
        )

    def handle(self, *args, **options):
        self.stdout.write("🤖 Testing AI Request Processor Integration")
        
        if options['create_test']:
            ticket = self.create_test_ticket()
            self.stdout.write(f"✅ Created test ticket {ticket.encoded_id}")
        elif options['ticket_id']:
            try:
                ticket = Ticket.objects.get(id=options['ticket_id'])
                self.stdout.write(f"📋 Using existing ticket {ticket.encoded_id}")
            except Ticket.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Ticket {options['ticket_id']} not found"))
                return
        else:
            # Use most recent ticket
            ticket = Ticket.objects.order_by('-id').first()
            if not ticket:
                self.stdout.write(self.style.ERROR("No tickets found. Use --create-test to create one."))
                return
            self.stdout.write(f"📋 Using latest ticket {ticket.encoded_id}")
        
        # Show original ticket data
        self.show_ticket_before(ticket)
        
        # Process with AI
        self.stdout.write("\n🔄 Processing ticket through AI request processor...")
        
        try:
            # Import and test AI processing
            from agents.request_processor import process_ticket
            
            # Prepare ticket data
            ticket_metadata = {
                "plain_body": ticket.description or "",
                "subject": ticket.subject or "",
                "priority": ticket.priority or "",
                "status": ticket.status or "",
                "tags": ticket.tags or []
            }
            
            # Process through AI
            self.stdout.write("  🧠 Running AI analysis...")
            ai_state = process_ticket(ticket_metadata)
            
            # Update ticket with AI results
            from tickets.utils import update_ticket_from_ai_analysis
            updates = update_ticket_from_ai_analysis(ticket, ai_state)
            ticket.last_rag_processed = timezone.now()
            ticket.save()
            
            # Show results
            self.show_results(ticket, ai_state, updates, options['show_reasoning'])
            
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"AI processing dependencies not available: {str(e)}"))
            self.stdout.write("Make sure langgraph, langchain, and groq are installed")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during AI processing: {str(e)}"))

    def create_test_ticket(self):
        """Create a test ticket for AI processing"""
        test_data = {
            'subject': 'IVMS Login Issues - Cannot Access Work Orders',
            'description': '''User reports unable to login to IVMS system since yesterday. 
            Getting error message "Authentication failed" when entering credentials.
            User: john.doe@asplundh.com
            Browser: Chrome Version 120
            Environment: Production
            Steps attempted:
            1. Cleared browser cache
            2. Tried different browser (Firefox)
            3. Reset password
            Still unable to access work orders and timesheet functionality.
            This is blocking daily work activities for the crew.
            Priority: High - affecting multiple users''',
            'status': 'new',
            'priority': 'high',
            'tags': ['ivms', 'login', 'authentication', 'blocker'],
            'ticket_id': 888890,
            'encoded_id': f'TEST-{timezone.now().strftime("%Y%m%d-%H%M%S")}'
        }
        
        return Ticket.objects.create(**test_data)

    def show_ticket_before(self, ticket):
        """Show ticket data before AI processing"""
        self.stdout.write("\n📋 TICKET BEFORE AI PROCESSING:")
        self.stdout.write(f"  ID: {ticket.encoded_id}")
        self.stdout.write(f"  Subject: {ticket.subject[:80]}...")
        self.stdout.write(f"  Priority: {ticket.priority}")
        self.stdout.write(f"  Product: {ticket.product or 'Not set'}")
        self.stdout.write(f"  Support Theme: {ticket.support_theme or 'Not set'}")
        self.stdout.write(f"  Severity: {ticket.severity or 'Not set'}")
        self.stdout.write(f"  Type: {ticket.ticket_type or 'Not set'}")

    def show_results(self, ticket, ai_state, updates, show_reasoning):
        """Show AI processing results"""
        self.stdout.write("\n✅ AI PROCESSING COMPLETED!")
        
        # Show updated fields
        self.stdout.write("\n📊 TICKET AFTER AI PROCESSING:")
        self.stdout.write(f"  ID: {ticket.encoded_id}")
        self.stdout.write(f"  Priority: {ticket.priority}")
        self.stdout.write(f"  Product: {ticket.product or 'Not set'}")
        self.stdout.write(f"  Support Theme: {ticket.support_theme or 'Not set'}")
        self.stdout.write(f"  Summary: {ticket.summary or 'Not set'}")
        self.stdout.write(f"  Severity: {ticket.severity or 'Not set'}")
        self.stdout.write(f"  Type: {ticket.ticket_type or 'Not set'}")
        self.stdout.write(f"  Interface: {ticket.interface_affected or 'Not set'}")
        self.stdout.write(f"  Module: {ticket.module or 'Not set'}")
        self.stdout.write(f"  Urgency: {ticket.urgency or 'Not set'}")
        
        # Show what was updated
        if updates:
            self.stdout.write(f"\n🔄 FIELDS UPDATED: {', '.join(updates.keys())}")
        else:
            self.stdout.write("\n⚠️  No fields were updated")
        
        # Show AI reasoning if requested
        if show_reasoning:
            self.show_ai_reasoning(ai_state)

    def show_ai_reasoning(self, ai_state):
        """Show AI reasoning for each field"""
        self.stdout.write("\n🧠 AI REASONING:")
        
        for field_name, field_data in ai_state.items():
            if isinstance(field_data, dict) and 'reasoning' in field_data:
                value = field_data.get('value', 'N/A')
                reasoning = field_data.get('reasoning', 'No reasoning provided')
                
                self.stdout.write(f"\n  {field_name.upper()}:")
                self.stdout.write(f"    Value: {value}")
                self.stdout.write(f"    Reasoning: {reasoning}")

    def style_field_update(self, field_name, old_value, new_value):
        """Style field updates for better readability"""
        if old_value != new_value:
            return self.style.SUCCESS(f"  {field_name}: {old_value} → {new_value}")
        else:
            return f"  {field_name}: {old_value} (unchanged)" 