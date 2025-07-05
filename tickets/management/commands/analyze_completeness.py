from django.core.management.base import BaseCommand
from tickets.models import Ticket, CompletenessChecklist
from django.db import transaction
import json


class Command(BaseCommand):
    help = 'Analyze ticket completeness and generate L1 response drafts'

    def add_arguments(self, parser):
        parser.add_argument('--ticket-id', type=int, help='Analyze specific ticket by ID')
        parser.add_argument('--all', action='store_true', help='Analyze all tickets')
        parser.add_argument('--update', action='store_true', help='Update tickets with completeness scores')
        parser.add_argument('--generate-responses', action='store_true', help='Generate L1 response drafts')

    def handle(self, *args, **options):
        if options['ticket_id']:
            tickets = Ticket.objects.filter(id=options['ticket_id'])
        elif options['all']:
            tickets = Ticket.objects.all()
        else:
            # Default: analyze recent tickets
            tickets = Ticket.objects.filter(status__in=['new', 'open', 'pending'])[:20]
        
        self.stdout.write(f"Analyzing {tickets.count()} tickets...")
        
        completeness_stats = {
            'high_completeness': 0,
            'medium_completeness': 0, 
            'low_completeness': 0,
            'total_analyzed': 0
        }
        
        response_drafts = []
        
        with transaction.atomic():
            for ticket in tickets:
                self.analyze_ticket(ticket, options, completeness_stats, response_drafts)
        
        self.print_summary(completeness_stats, response_drafts, options)

    def analyze_ticket(self, ticket, options, stats, response_drafts):
        """Analyze individual ticket completeness"""
        try:
            theme = ticket.get_support_theme_from_tags()
            completeness, missing_items = ticket.check_completeness()
            
            stats['total_analyzed'] += 1
            
            if completeness >= 80:
                stats['high_completeness'] += 1
                completeness_level = 'High'
            elif completeness >= 50:
                stats['medium_completeness'] += 1
                completeness_level = 'Medium'
            else:
                stats['low_completeness'] += 1
                completeness_level = 'Low'
            
            self.stdout.write(
                f"Ticket {ticket.id}: {theme} - {completeness:.1f}% complete ({completeness_level})"
            )
            
            if missing_items:
                self.stdout.write(f"  Missing: {', '.join(missing_items[:3])}{'...' if len(missing_items) > 3 else ''}")
            
            # Update ticket if requested
            if options['update']:
                ticket.completeness_score = completeness
                ticket.missing_info = missing_items
                ticket.save(update_fields=['completeness_score', 'missing_info'])
            
            # Generate response draft if requested and completeness is low
            if options['generate_responses'] and completeness < 70:
                draft = self.generate_response_draft(ticket, theme, missing_items)
                if draft:
                    response_drafts.append({
                        'ticket_id': ticket.id,
                        'ticket_subject': ticket.subject,
                        'theme': theme,
                        'completeness': completeness,
                        'draft_response': draft
                    })
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error analyzing ticket {ticket.id}: {str(e)}")
            )

    def generate_response_draft(self, ticket, theme, missing_items):
        """Generate L1 response draft based on missing information"""
        try:
            checklist = CompletenessChecklist.objects.get(support_theme=theme)
            
            if not missing_items:
                return None
            
            # Format missing items for the template
            missing_items_formatted = []
            for i, item in enumerate(missing_items, 1):
                missing_items_formatted.append(f"{i}. {item}")
            
            missing_items_text = '\n'.join(missing_items_formatted)
            
            # Use the template from the checklist
            response_draft = checklist.response_template.format(
                missing_items=missing_items_text
            )
            
            return response_draft
            
        except CompletenessChecklist.DoesNotExist:
            # Fallback generic response
            missing_items_formatted = []
            for i, item in enumerate(missing_items, 1):
                missing_items_formatted.append(f"{i}. {item}")
            
            missing_items_text = '\n'.join(missing_items_formatted)
            
            return f"""Thank you for contacting AiDASH support.

To help us resolve your issue efficiently, could you please provide the following information:

{missing_items_text}

This will help our technical team provide you with a targeted solution.

Best regards,
AiDASH Support Team"""

    def print_summary(self, stats, response_drafts, options):
        """Print analysis summary and response drafts"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("COMPLETENESS ANALYSIS SUMMARY")
        self.stdout.write("="*60)
        
        self.stdout.write(f"Total tickets analyzed: {stats['total_analyzed']}")
        self.stdout.write(f"High completeness (80%+): {stats['high_completeness']}")
        self.stdout.write(f"Medium completeness (50-79%): {stats['medium_completeness']}")
        self.stdout.write(f"Low completeness (<50%): {stats['low_completeness']}")
        
        if stats['total_analyzed'] > 0:
            avg_completeness = (
                (stats['high_completeness'] * 85) + 
                (stats['medium_completeness'] * 65) + 
                (stats['low_completeness'] * 30)
            ) / stats['total_analyzed']
            self.stdout.write(f"Average estimated completeness: {avg_completeness:.1f}%")
        
        if response_drafts:
            self.stdout.write(f"\n{len(response_drafts)} L1 RESPONSE DRAFTS GENERATED")
            self.stdout.write("="*60)
            
            for draft in response_drafts[:5]:  # Show first 5
                self.stdout.write(f"\nTicket {draft['ticket_id']}: {draft['ticket_subject'][:50]}...")
                self.stdout.write(f"Theme: {draft['theme']} | Completeness: {draft['completeness']:.1f}%")
                self.stdout.write("Response Draft:")
                self.stdout.write("-" * 40)
                self.stdout.write(draft['draft_response'])
                self.stdout.write("-" * 40)
            
            if len(response_drafts) > 5:
                self.stdout.write(f"\n... and {len(response_drafts) - 5} more response drafts")
        
        # Recommendations
        self.stdout.write(f"\nRECOMMENDATIONS")
        self.stdout.write("="*30)
        
        if stats['low_completeness'] > stats['total_analyzed'] * 0.3:
            self.stdout.write("• High number of incomplete tickets - consider proactive information gathering")
        
        if stats['high_completeness'] > stats['total_analyzed'] * 0.5:
            self.stdout.write("• Good information quality - tickets are well-documented")
        else:
            self.stdout.write("• Consider implementing mandatory fields for ticket submission")
        
        self.stdout.write("• Use generated response drafts to standardize L1 communications")
        self.stdout.write("• Monitor completeness trends over time") 