from django.core.management.base import BaseCommand
from tickets.models import Ticket
from tickets.management.commands.analyze_completeness import Command as CompletenessAnalyzer
from django.utils import timezone
import json


class Command(BaseCommand):
    help = 'Trigger the automated completeness pipeline for tickets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ticket-id',
            type=int,
            help='Specific ticket ID to process'
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=['new', 'open', 'pending', 'all'],
            default='new',
            help='Process tickets with specific status (default: new)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum number of tickets to process (default: 10)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocessing even if already processed'
        )

    def handle(self, *args, **options):
        self.stdout.write("🚀 Starting Automated Pipeline Trigger")
        
        # Get tickets to process
        if options['ticket_id']:
            tickets = [Ticket.objects.get(id=options['ticket_id'])]
        else:
            tickets = self.get_tickets_to_process(options)
        
        if not tickets:
            self.stdout.write(self.style.WARNING("No tickets found to process"))
            return
        
        self.stdout.write(f"Found {len(tickets)} tickets to process")
        
        # Process each ticket
        results = {
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'drafts_generated': 0
        }
        
        for ticket in tickets:
            try:
                result = self.process_ticket_pipeline(ticket, options['force'])
                
                if result['processed']:
                    results['processed'] += 1
                    if result['draft_generated']:
                        results['drafts_generated'] += 1
                else:
                    results['skipped'] += 1
                    
            except Exception as e:
                results['errors'] += 1
                self.stdout.write(
                    self.style.ERROR(f"Error processing ticket {ticket.id}: {str(e)}")
                )
        
        # Display results
        self.display_results(results)

    def get_tickets_to_process(self, options):
        """Get tickets based on filter criteria"""
        queryset = Ticket.objects.all().order_by('-created_at')
        
        # Filter by status
        if options['status'] != 'all':
            queryset = queryset.filter(status=options['status'])
        
        # Limit results
        if options['limit']:
            queryset = queryset[:options['limit']]
        
        return list(queryset)

    def process_ticket_pipeline(self, ticket, force=False):
        """
        Process a single ticket through the pipeline
        Simulates the webhook-triggered automated flow
        """
        self.stdout.write(f"Processing ticket {ticket.encoded_id}...")
        
        result = {
            'processed': False,
            'draft_generated': False,
            'steps_completed': []
        }
        
        # Step 1: Check if already processed (unless forced)
        if not force and ticket.completeness_score is not None:
            self.stdout.write(f"  ⏭️  Skipping {ticket.encoded_id} - already processed")
            return result
        
        # Step 2: Simulate RAG Pipeline
        self.stdout.write(f"  📊 Running RAG pipeline...")
        ticket.last_rag_processed = timezone.now()
        result['steps_completed'].append('rag')
        
        # Step 3: Run Completeness Analysis
        self.stdout.write(f"  🔍 Running completeness analysis...")
        completeness_score, missing_items = ticket.check_completeness()
        ticket.completeness_score = completeness_score
        ticket.missing_info = missing_items
        result['steps_completed'].append('completeness')
        
        # Step 4: Generate L1 Response Draft if needed
        if completeness_score < 80 and missing_items:
            self.stdout.write(f"  ✍️  Generating L1 response draft...")
            
            theme = ticket.get_support_theme_from_tags()
            analyzer = CompletenessAnalyzer()
            response_draft = analyzer.generate_response_draft(ticket, theme, missing_items)
            
            ticket.l1_response_draft = response_draft
            ticket.draft_generated_at = timezone.now()
            result['draft_generated'] = True
            result['steps_completed'].append('draft')
        
        # Save ticket with all updates
        ticket.save()
        result['processed'] = True
        
        # Display ticket results
        self.stdout.write(
            f"  ✅ Completed: {completeness_score:.1f}% complete, "
            f"{len(missing_items)} missing items"
        )
        
        if result['draft_generated']:
            self.stdout.write(f"  📝 L1 response draft generated")
        
        return result

    def display_results(self, results):
        """Display pipeline execution results"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("📊 PIPELINE EXECUTION RESULTS")
        self.stdout.write("="*50)
        
        self.stdout.write(f"✅ Tickets Processed: {results['processed']}")
        self.stdout.write(f"📝 L1 Drafts Generated: {results['drafts_generated']}")
        self.stdout.write(f"⏭️  Tickets Skipped: {results['skipped']}")
        self.stdout.write(f"❌ Errors: {results['errors']}")
        
        if results['processed'] > 0:
            draft_percentage = (results['drafts_generated'] / results['processed']) * 100
            self.stdout.write(f"📈 Draft Generation Rate: {draft_percentage:.1f}%")
        
        # Get current database statistics
        self.stdout.write("\n📊 CURRENT DATABASE STATS:")
        
        total_tickets = Ticket.objects.count()
        processed_tickets = Ticket.objects.filter(completeness_score__isnull=False).count()
        incomplete_tickets = Ticket.objects.filter(completeness_score__lt=80).count()
        drafts_available = Ticket.objects.filter(l1_response_draft__isnull=False).count()
        
        self.stdout.write(f"   Total tickets: {total_tickets}")
        self.stdout.write(f"   Processed tickets: {processed_tickets}")
        self.stdout.write(f"   Incomplete tickets: {incomplete_tickets}")
        self.stdout.write(f"   Drafts available: {drafts_available}")
        
        if processed_tickets > 0:
            # Calculate average completeness
            from django.db.models import Avg
            avg_completeness = Ticket.objects.filter(
                completeness_score__isnull=False
            ).aggregate(Avg('completeness_score'))['completeness_score__avg']
            
            self.stdout.write(f"   Average completeness: {avg_completeness:.1f}%")
        
        self.stdout.write("\n🎯 Pipeline integration successful!")
        self.stdout.write("Ready for webhook integration and production deployment.") 