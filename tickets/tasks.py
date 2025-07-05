import logging
from celery import shared_task
from django.utils import timezone
from .models import Ticket, CompletenessChecklist
from .management.commands.analyze_completeness import Command as CompletenessAnalyzer

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def trigger_completeness_pipeline(self, ticket_id):
    """
    Main pipeline task that orchestrates the completeness checking workflow
    This is triggered by the webhook when a ticket is created/updated
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        logger.info(f"Starting completeness pipeline for ticket {ticket.encoded_id}")
        
        # Step 1: Trigger RAG pipeline (placeholder for now)
        rag_result = trigger_rag_pipeline.delay(ticket_id)
        
        # Step 2: Run completeness analysis
        completeness_result = run_completeness_analysis.delay(ticket_id)
        
        # Step 3: Generate L1 response draft if needed
        draft_result = generate_l1_response_draft.delay(ticket_id)
        
        # Step 4: Update dashboard metrics
        update_dashboard_metrics.delay()
        
        logger.info(f"Pipeline tasks queued for ticket {ticket.encoded_id}")
        
        return {
            'status': 'success',
            'ticket_id': ticket_id,
            'tasks_queued': ['rag', 'completeness', 'draft', 'dashboard']
        }
        
    except Ticket.DoesNotExist:
        logger.error(f"Ticket {ticket_id} not found")
        raise Exception(f"Ticket {ticket_id} not found")
    
    except Exception as e:
        logger.error(f"Pipeline error for ticket {ticket_id}: {str(e)}")
        self.retry(countdown=60, exc=e)


@shared_task(bind=True, max_retries=2)
def trigger_rag_pipeline(self, ticket_id):
    """
    Trigger RAG pipeline and vector database refresh
    Step 4 in the flow diagram
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        
        # TODO: Integrate with actual RAG system
        # For now, this is a placeholder that simulates RAG processing
        
        logger.info(f"RAG pipeline triggered for ticket {ticket.encoded_id}")
        
        # Simulate RAG processing time
        import time
        time.sleep(2)
        
        # Update ticket with RAG processing timestamp
        ticket.last_rag_processed = timezone.now()
        ticket.save()
        
        return {
            'status': 'completed',
            'ticket_id': ticket_id,
            'processed_at': ticket.last_rag_processed.isoformat()
        }
        
    except Ticket.DoesNotExist:
        logger.error(f"Ticket {ticket_id} not found for RAG processing")
        raise
    
    except Exception as e:
        logger.error(f"RAG pipeline error for ticket {ticket_id}: {str(e)}")
        self.retry(countdown=30, exc=e)


@shared_task(bind=True, max_retries=2)
def run_completeness_analysis(self, ticket_id):
    """
    Run completeness analysis on the ticket
    Step 6 in the flow diagram
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        
        # Run completeness check using existing logic
        completeness_score, missing_items = ticket.check_completeness()
        
        # Save results
        ticket.completeness_score = completeness_score
        ticket.missing_info = missing_items
        ticket.save()
        
        logger.info(f"Completeness analysis completed for ticket {ticket.encoded_id}: {completeness_score}%")
        
        return {
            'status': 'completed',
            'ticket_id': ticket_id,
            'completeness_score': completeness_score,
            'missing_items_count': len(missing_items)
        }
        
    except Ticket.DoesNotExist:
        logger.error(f"Ticket {ticket_id} not found for completeness analysis")
        raise
    
    except Exception as e:
        logger.error(f"Completeness analysis error for ticket {ticket_id}: {str(e)}")
        self.retry(countdown=30, exc=e)


@shared_task(bind=True, max_retries=2)
def generate_l1_response_draft(self, ticket_id):
    """
    Generate L1 response draft for incomplete tickets
    Step 7 in the flow diagram
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        
        # Only generate draft if completeness is below threshold
        if ticket.completeness_score and ticket.completeness_score < 80:
            
            # Get support theme and missing items
            theme = ticket.get_support_theme_from_tags()
            missing_items = ticket.missing_info or []
            
            if missing_items:
                # Generate response draft using existing logic
                analyzer = CompletenessAnalyzer()
                response_draft = analyzer.generate_response_draft(ticket, theme, missing_items)
                
                # Save the draft (you might want to create a ResponseDraft model)
                # For now, we'll store it in a field on the ticket
                ticket.l1_response_draft = response_draft
                ticket.draft_generated_at = timezone.now()
                ticket.save()
                
                logger.info(f"L1 response draft generated for ticket {ticket.encoded_id}")
                
                return {
                    'status': 'draft_generated',
                    'ticket_id': ticket_id,
                    'theme': theme,
                    'missing_items_count': len(missing_items)
                }
        
        return {
            'status': 'no_draft_needed',
            'ticket_id': ticket_id,
            'completeness_score': ticket.completeness_score
        }
        
    except Ticket.DoesNotExist:
        logger.error(f"Ticket {ticket_id} not found for L1 draft generation")
        raise
    
    except Exception as e:
        logger.error(f"L1 draft generation error for ticket {ticket_id}: {str(e)}")
        self.retry(countdown=30, exc=e)


@shared_task
def update_dashboard_metrics():
    """
    Update dashboard metrics and refresh data
    Step 8 in the flow diagram
    """
    try:
        # Calculate current metrics
        total_tickets = Ticket.objects.count()
        incomplete_tickets = Ticket.objects.filter(completeness_score__lt=80).count()
        drafts_generated = Ticket.objects.filter(l1_response_draft__isnull=False).count()
        
        # Calculate average completeness
        from django.db.models import Avg
        avg_completeness = Ticket.objects.filter(
            completeness_score__isnull=False
        ).aggregate(Avg('completeness_score'))['completeness_score__avg']
        
        metrics = {
            'total_tickets': total_tickets,
            'incomplete_tickets': incomplete_tickets,
            'drafts_generated': drafts_generated,
            'average_completeness': round(avg_completeness or 0, 2),
            'updated_at': timezone.now().isoformat()
        }
        
        logger.info(f"Dashboard metrics updated: {metrics}")
        
        # TODO: Push to Metabase or dashboard system
        # This could involve API calls or database updates
        
        return metrics
        
    except Exception as e:
        logger.error(f"Dashboard metrics update error: {str(e)}")
        raise


@shared_task
def process_ticket_batch(ticket_ids):
    """
    Batch process multiple tickets for efficiency
    Useful for bulk imports or periodic processing
    """
    results = []
    
    for ticket_id in ticket_ids:
        try:
            result = trigger_completeness_pipeline.delay(ticket_id)
            results.append({'ticket_id': ticket_id, 'task_id': result.id})
        except Exception as e:
            results.append({'ticket_id': ticket_id, 'error': str(e)})
    
    return {
        'status': 'batch_processed',
        'total_tickets': len(ticket_ids),
        'results': results
    } 