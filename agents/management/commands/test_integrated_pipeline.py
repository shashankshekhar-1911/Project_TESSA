from django.core.management.base import BaseCommand
from agents.integrated_pipeline import (
    test_integrated_pipeline, 
    process_ticket_pipeline,
    get_pipeline_status
)
from tickets.models import Ticket


class Command(BaseCommand):
    help = 'Test the integrated TESSA pipeline (completeness checker + draft response creator)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ticket-id',
            type=int,
            help='Specific ticket ID to test the pipeline with'
        )
        parser.add_argument(
            '--auto-find',
            action='store_true',
            help='Automatically find a suitable ticket for testing'
        )
        parser.add_argument(
            '--status-only',
            action='store_true',
            help='Only check pipeline status for the ticket'
        )

    def handle(self, *args, **options):
        self.stdout.write("🚀 Testing Integrated TESSA Pipeline")
        
        ticket_id = options.get('ticket_id')
        auto_find = options.get('auto_find')
        status_only = options.get('status_only')
        
        # Find a ticket to test with
        if not ticket_id and auto_find:
            self.stdout.write("\n🔍 Auto-finding suitable ticket...")
            try:
                test_ticket = Ticket.objects.filter(
                    description__isnull=False,
                    support_theme__isnull=False
                ).first()
                
                if test_ticket:
                    ticket_id = test_ticket.id
                    self.stdout.write(f"  ✅ Found ticket {ticket_id}: {test_ticket.subject[:50]}...")
                else:
                    self.stdout.write("  ❌ No suitable tickets found")
                    return
                    
            except Exception as e:
                self.stdout.write(f"  ❌ Error finding ticket: {str(e)}")
                return
        
        elif not ticket_id:
            self.stdout.write("❌ Please provide --ticket-id or use --auto-find")
            return
        
        # Status check only
        if status_only:
            self.check_pipeline_status(ticket_id)
            return
        
        # Run the full pipeline test
        self.run_pipeline_test(ticket_id)

    def check_pipeline_status(self, ticket_id):
        """Check and display pipeline status for a ticket"""
        self.stdout.write(f"\n📊 Checking Pipeline Status for Ticket {ticket_id}")
        
        try:
            status = get_pipeline_status(ticket_id)
            
            self.stdout.write(f"\n  📋 Status Summary:")
            self.stdout.write(f"    Ticket ID: {status['ticket_id']}")
            self.stdout.write(f"    Pipeline Run: {'✅' if status['pipeline_run'] else '❌'}")
            self.stdout.write(f"    Completeness Check: {'✅' if status['completeness_check_run'] else '❌'}")
            self.stdout.write(f"    Draft Response: {'✅' if status['draft_response_created'] else '❌'}")
            self.stdout.write(f"    Audit Log Count: {status['audit_log_count']}")
            
            if status.get('last_pipeline_run'):
                self.stdout.write(f"    Last Pipeline Run: {status['last_pipeline_run']}")
                self.stdout.write(f"    Last Pipeline Success: {'✅' if status.get('last_pipeline_success') else '❌'}")
            
            if status.get('completeness_score') is not None:
                self.stdout.write(f"    Completeness Score: {status['completeness_score']}%")
            
            if status.get('draft_response_length'):
                self.stdout.write(f"    Draft Response Length: {status['draft_response_length']} chars")
            
        except Exception as e:
            self.stdout.write(f"  ❌ Error checking status: {str(e)}")

    def run_pipeline_test(self, ticket_id):
        """Run the complete pipeline test"""
        self.stdout.write(f"\n🧪 Running Integrated Pipeline Test for Ticket {ticket_id}")
        
        # Get ticket info
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            self.stdout.write(f"\n  📝 Ticket Info:")
            self.stdout.write(f"    Subject: {ticket.subject}")
            self.stdout.write(f"    Support Theme: {ticket.support_theme}")
            self.stdout.write(f"    Description: {ticket.description[:100] if ticket.description else 'No description'}...")
            
        except Ticket.DoesNotExist:
            self.stdout.write(f"  ❌ Ticket {ticket_id} not found")
            return
        
        # Run the pipeline
        self.stdout.write(f"\n🔄 Starting Pipeline Processing...")
        
        try:
            results = process_ticket_pipeline(ticket_id, trigger_source="management_command_test")
            
            self.stdout.write(f"\n✅ Pipeline Processing Complete!")
            self.display_pipeline_results(results)
            
        except Exception as e:
            self.stdout.write(f"\n❌ Pipeline processing failed: {str(e)}")

    def display_pipeline_results(self, results):
        """Display detailed pipeline results"""
        self.stdout.write(f"\n📊 PIPELINE RESULTS")
        self.stdout.write(f"  🎯 Overall Success: {'✅' if results['overall_success'] else '❌'}")
        self.stdout.write(f"  ⏱️  Duration: {results['pipeline_duration_seconds']:.2f} seconds")
        self.stdout.write(f"  📋 Steps Completed: {', '.join(results['steps_completed']) if results['steps_completed'] else 'None'}")
        self.stdout.write(f"  ❌ Steps Failed: {', '.join(results['steps_failed']) if results['steps_failed'] else 'None'}")
        
        # Completeness Check Results
        if 'completeness_check' in results:
            cc_result = results['completeness_check']
            self.stdout.write(f"\n  🔍 COMPLETENESS CHECK:")
            
            if 'error' in cc_result:
                self.stdout.write(f"    ❌ Error: {cc_result['error']}")
            else:
                self.stdout.write(f"    📊 Score: {cc_result.get('completeness_score', 'N/A')}%")
                self.stdout.write(f"    📝 Support Theme: {cc_result.get('support_theme', 'N/A')}")
                self.stdout.write(f"    ✅ Required Inputs: {len(cc_result.get('required_inputs', []))}")
                self.stdout.write(f"    ❌ Missing Inputs: {len(cc_result.get('missing_inputs', []))}")
                
                if cc_result.get('missing_inputs'):
                    self.stdout.write(f"    📋 Missing Items:")
                    for item in cc_result['missing_inputs'][:5]:  # Show first 5
                        self.stdout.write(f"      - {item}")
                    if len(cc_result['missing_inputs']) > 5:
                        self.stdout.write(f"      ... and {len(cc_result['missing_inputs']) - 5} more")
                
                audit_status = "✅" if cc_result.get('audit_logged') else "❌"
                self.stdout.write(f"    📝 Audit Logged: {audit_status}")
                if cc_result.get('audit_id'):
                    self.stdout.write(f"    🔗 Audit ID: {cc_result['audit_id']}")
        
        # Draft Response Results
        if 'draft_response' in results:
            dr_result = results['draft_response']
            self.stdout.write(f"\n  ✍️  DRAFT RESPONSE:")
            
            if 'error' in dr_result:
                self.stdout.write(f"    ❌ Error: {dr_result['error']}")
            elif 'skipped' in dr_result:
                self.stdout.write(f"    ⏭️  Skipped: {dr_result['skipped']}")
            else:
                response_text = dr_result.get('generated_response', '')
                self.stdout.write(f"    📏 Length: {len(response_text)} characters")
                self.stdout.write(f"    🤖 Model: {dr_result.get('model_used', 'N/A')}")
                
                # Show first few lines of response
                if response_text:
                    lines = response_text.split('\n')[:3]
                    self.stdout.write(f"    📄 Preview:")
                    for line in lines:
                        if line.strip():
                            self.stdout.write(f"      {line[:80]}{'...' if len(line) > 80 else ''}")
                
                audit_status = "✅" if dr_result.get('audit_logged') else "❌"
                self.stdout.write(f"    📝 Audit Logged: {audit_status}")
                if dr_result.get('audit_id'):
                    self.stdout.write(f"    🔗 Audit ID: {dr_result['audit_id']}")
        
        # Pipeline Audit
        if results.get('pipeline_audit_id'):
            self.stdout.write(f"\n  📋 Pipeline Audit ID: {results['pipeline_audit_id']}")
        
        self.stdout.write(f"\n🎉 Pipeline test completed for ticket {results['ticket_id']}!")
        
        # Suggest next steps
        if results['overall_success']:
            self.stdout.write("\n💡 Next steps:")
            self.stdout.write("  - Check audit logs in admin panel")
            self.stdout.write("  - Review generated draft response")
            self.stdout.write("  - Monitor pipeline performance metrics")
        else:
            self.stdout.write("\n🔧 Troubleshooting:")
            self.stdout.write("  - Check system logs for error details")
            self.stdout.write("  - Verify database connections")
            self.stdout.write("  - Ensure all required dependencies are installed") 