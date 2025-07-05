from django.core.management.base import BaseCommand
from tickets.models import Ticket, AuditLog
from tickets.utils import process_ticket_with_ai, log_audit_event, get_audit_logs_for_ticket
from django.utils import timezone
import json


class Command(BaseCommand):
    help = 'Test audit log integration with AI processing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ticket-id',
            type=int,
            help='Specific ticket ID to test audit logging'
        )
        parser.add_argument(
            '--create-test',
            action='store_true',
            help='Create a test ticket for audit logging'
        )

    def handle(self, *args, **options):
        self.stdout.write("🔍 Testing Audit Log Integration")
        
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
        
        # Show audit logs before processing
        self.show_audit_logs_before(ticket)
        
        # Test manual audit logging
        self.test_manual_audit_logging(ticket)
        
        # Test AI processing with audit logging
        self.test_ai_processing_with_audit(ticket)
        
        # Show final audit log summary
        self.show_audit_logs_after(ticket)

    def create_test_ticket(self):
        """Create a test ticket for audit logging"""
        test_data = {
            'subject': 'IVMS Performance Issues - Slow Loading',
            'description': '''System experiencing significant performance degradation.
            Users reporting slow loading times across all modules.
            Environment: Production
            Browser: Multiple (Chrome, Firefox, Safari)
            Affected Users: ~50+ users
            Impact: High - Daily operations affected
            Error logs show timeout issues on database queries.
            Need immediate investigation and resolution.''',
            'status': 'new',
            'priority': 'high',
            'tags': ['ivms', 'performance', 'database', 'urgent'],
            'ticket_id': int(timezone.now().timestamp()) + 1000000,  # Unique ID
            'encoded_id': f'AUDIT-TEST-{timezone.now().strftime("%Y%m%d-%H%M%S")}'
        }
        
        return Ticket.objects.create(**test_data)

    def test_manual_audit_logging(self, ticket):
        """Test manual audit log creation"""
        self.stdout.write("\n🧪 Testing manual audit logging...")
        
        # Test different types of audit logs
        test_logs = [
            {
                'function': 'manual_test_function',
                'response': {'status': 'success', 'operation': 'test'},
                'context': {'test_type': 'manual'}
            },
            {
                'function': 'ticket_validation',
                'response': {'valid': True, 'fields_checked': ['subject', 'description']},
                'context': {'validation_stage': 'pre_processing'}
            }
        ]
        
        for log_data in test_logs:
            audit_log = log_audit_event(
                function_name=log_data['function'],
                ticket_id=ticket.id,
                response_data=log_data['response'],
                additional_context=log_data['context']
            )
            
            if audit_log:
                self.stdout.write(f"  ✅ Created audit log for {log_data['function']}")
            else:
                self.stdout.write(f"  ❌ Failed to create audit log for {log_data['function']}")

    def test_ai_processing_with_audit(self, ticket):
        """Test AI processing with integrated audit logging"""
        self.stdout.write("\n🤖 Testing AI processing with audit logging...")
        
        try:
            # This should trigger audit logging inside process_ticket_with_ai
            ai_processed = process_ticket_with_ai(ticket.id)
            
            if ai_processed:
                self.stdout.write("  ✅ AI processing completed with audit logging")
            else:
                self.stdout.write("  ⚠️  AI processing completed but may have failed")
                
        except Exception as e:
            self.stdout.write(f"  ❌ AI processing failed: {str(e)}")

    def show_audit_logs_before(self, ticket):
        """Show audit logs before processing"""
        logs = get_audit_logs_for_ticket(ticket.id)
        self.stdout.write(f"\n📊 AUDIT LOGS BEFORE PROCESSING:")
        self.stdout.write(f"  Total logs: {logs.count()}")
        
        if logs.exists():
            for log in logs[:3]:  # Show last 3
                self.stdout.write(f"  - {log.function} at {log.timestamp.strftime('%H:%M:%S')}")

    def show_audit_logs_after(self, ticket):
        """Show comprehensive audit log summary"""
        logs = get_audit_logs_for_ticket(ticket.id)
        
        self.stdout.write(f"\n📈 FINAL AUDIT LOG SUMMARY:")
        self.stdout.write(f"  Ticket ID: {ticket.id}")
        self.stdout.write(f"  Encoded ID: {ticket.encoded_id}")
        self.stdout.write(f"  Total audit logs: {logs.count()}")
        
        # Group by function
        function_counts = {}
        for log in logs:
            function_counts[log.function] = function_counts.get(log.function, 0) + 1
        
        self.stdout.write("\n  📋 Functions logged:")
        for function, count in function_counts.items():
            self.stdout.write(f"    - {function}: {count} logs")
        
        # Show recent logs
        self.stdout.write("\n  🕒 Recent logs:")
        for log in logs[:5]:  # Show last 5
            status = "N/A"
            if isinstance(log.message, dict):
                status = log.message.get('response', {}).get('status', 'N/A')
            
            self.stdout.write(
                f"    - {log.timestamp.strftime('%H:%M:%S')} | "
                f"{log.function} | Status: {status}"
            )
        
        # Test API endpoints
        self.test_api_endpoints(ticket)

    def test_api_endpoints(self, ticket):
        """Test audit log API endpoints"""
        self.stdout.write("\n🌐 Testing API endpoints...")
        
        try:
            from tickets.api_views import TicketAuditLogAPIView, AuditLogSummaryAPIView
            from django.test import RequestFactory
            
            factory = RequestFactory()
            
            # Test ticket audit logs endpoint
            request = factory.get(f'/api/audit-logs/{ticket.id}/')
            view = TicketAuditLogAPIView()
            response = view.get(request, ticket.id)
            
            if response.status_code == 200:
                data = response.data
                self.stdout.write(f"  ✅ Ticket audit logs API: {data['total_audit_logs']} logs found")
            else:
                self.stdout.write(f"  ❌ Ticket audit logs API failed: {response.status_code}")
            
            # Test summary endpoint
            request = factory.get('/api/audit-logs/summary/')
            view = AuditLogSummaryAPIView()
            response = view.get(request)
            
            if response.status_code == 200:
                data = response.data
                self.stdout.write(f"  ✅ Summary API: {data['total_audit_logs']} total logs")
            else:
                self.stdout.write(f"  ❌ Summary API failed: {response.status_code}")
                
        except Exception as e:
            self.stdout.write(f"  ❌ API testing failed: {str(e)}") 