"""
Integrated TESSA Pipeline for Ticket Processing
Combines completeness checking and draft response creation
Following the workflow diagram provided
"""

import logging
from typing import Dict, Any, Optional
from django.utils import timezone

from .completeness_checker import process_completeness_check
from .draft_response_creator import process_draft_response

logger = logging.getLogger(__name__)


def process_ticket_pipeline(ticket_id: int, trigger_source: str = "webhook") -> Dict[str, Any]:
    """
    Process a ticket through the complete TESSA pipeline
    
    Workflow based on the provided diagram:
    1. Email Received
    2. ZenDesk Ticket Created
    3. Zendesk webhook activated and Tickets table updated
    4. RAG pipeline triggered / vector DB refresh
    5. Request Processor Triggered and tickets table updated
    6. Completeness Checker triggered and some table updated
    7. Draft Response Creator triggered and some table created
    8. Metabase Dashboard Refreshed
    
    Args:
        ticket_id (int): The ticket ID to process
        trigger_source (str): Source that triggered the pipeline (webhook, manual, etc.)
        
    Returns:
        Dict[str, Any]: Complete pipeline results with all processing steps
    """
    
    pipeline_start_time = timezone.now()
    pipeline_results = {
        'ticket_id': ticket_id,
        'trigger_source': trigger_source,
        'pipeline_start_time': pipeline_start_time.isoformat(),
        'steps_completed': [],
        'steps_failed': [],
        'overall_success': False
    }
    
    logger.info(f"Starting integrated pipeline for ticket {ticket_id} (triggered by {trigger_source})")
    
    # Step 1: Completeness Checker
    logger.info(f"Step 1: Running completeness check for ticket {ticket_id}")
    try:
        completeness_result = process_completeness_check(ticket_id)
        pipeline_results['completeness_check'] = completeness_result
        pipeline_results['steps_completed'].append('completeness_check')
        
        logger.info(f"Completeness check completed. Score: {completeness_result.get('completeness_score', 'N/A')}%")
        
        # Check if audit logging was successful
        if completeness_result.get('audit_logged', False):
            logger.info(f"Completeness check audit logged with ID: {completeness_result.get('audit_id', 'N/A')}")
        else:
            logger.warning(f"Completeness check audit logging failed: {completeness_result.get('audit_error', 'Unknown error')}")
            
    except Exception as e:
        error_msg = f"Completeness check failed: {str(e)}"
        logger.error(error_msg)
        pipeline_results['steps_failed'].append('completeness_check')
        pipeline_results['completeness_check'] = {'error': error_msg}
    
    # Step 2: Draft Response Creator (only if completeness check succeeded)
    if 'completeness_check' in pipeline_results['steps_completed']:
        logger.info(f"Step 2: Running draft response creator for ticket {ticket_id}")
        try:
            draft_response_result = process_draft_response(ticket_id)
            pipeline_results['draft_response'] = draft_response_result
            pipeline_results['steps_completed'].append('draft_response')
            
            response_length = len(draft_response_result.get('generated_response', ''))
            logger.info(f"Draft response created. Length: {response_length} characters")
            
            # Check if audit logging was successful
            if draft_response_result.get('audit_logged', False):
                logger.info(f"Draft response audit logged with ID: {draft_response_result.get('audit_id', 'N/A')}")
            else:
                logger.warning(f"Draft response audit logging failed: {draft_response_result.get('audit_error', 'Unknown error')}")
                
        except Exception as e:
            error_msg = f"Draft response creation failed: {str(e)}"
            logger.error(error_msg)
            pipeline_results['steps_failed'].append('draft_response')
            pipeline_results['draft_response'] = {'error': error_msg}
    else:
        logger.warning("Skipping draft response creation due to completeness check failure")
        pipeline_results['draft_response'] = {'skipped': 'Completeness check failed'}
    
    # Step 3: Pipeline Summary and Audit Logging
    pipeline_end_time = timezone.now()
    pipeline_duration = (pipeline_end_time - pipeline_start_time).total_seconds()
    
    pipeline_results['pipeline_end_time'] = pipeline_end_time.isoformat()
    pipeline_results['pipeline_duration_seconds'] = pipeline_duration
    pipeline_results['overall_success'] = len(pipeline_results['steps_failed']) == 0
    
    # Log overall pipeline result
    try:
        from tickets.utils import log_audit_event
        
        pipeline_audit = log_audit_event(
            function_name="integrated_pipeline",
            ticket_id=ticket_id,
            response_data={
                'trigger_source': trigger_source,
                'steps_completed': pipeline_results['steps_completed'],
                'steps_failed': pipeline_results['steps_failed'],
                'overall_success': pipeline_results['overall_success'],
                'pipeline_duration_seconds': pipeline_duration,
                'completeness_score': pipeline_results.get('completeness_check', {}).get('completeness_score'),
                'draft_response_created': 'draft_response' in pipeline_results['steps_completed']
            },
            additional_context={
                'pipeline_start_time': pipeline_start_time.isoformat(),
                'pipeline_end_time': pipeline_end_time.isoformat()
            }
        )
        
        if pipeline_audit:
            pipeline_results['pipeline_audit_id'] = str(pipeline_audit.audit_id)
            logger.info(f"Pipeline audit logged with ID: {pipeline_audit.audit_id}")
        
    except Exception as e:
        logger.error(f"Failed to log pipeline audit: {str(e)}")
        pipeline_results['pipeline_audit_error'] = str(e)
    
    # Final logging
    if pipeline_results['overall_success']:
        logger.info(f"Pipeline completed successfully for ticket {ticket_id} in {pipeline_duration:.2f}s")
    else:
        logger.error(f"Pipeline completed with errors for ticket {ticket_id}. Failed steps: {pipeline_results['steps_failed']}")
    
    return pipeline_results


def trigger_pipeline_from_webhook(ticket_id: int) -> Dict[str, Any]:
    """
    Trigger the integrated pipeline from a webhook event
    This follows the workflow: Zendesk webhook -> Pipeline processing
    
    Args:
        ticket_id (int): The ticket ID to process
        
    Returns:
        Dict[str, Any]: Pipeline processing results
    """
    logger.info(f"Webhook triggered pipeline for ticket {ticket_id}")
    return process_ticket_pipeline(ticket_id, trigger_source="zendesk_webhook")


def trigger_pipeline_manual(ticket_id: int) -> Dict[str, Any]:
    """
    Manually trigger the integrated pipeline (for testing or manual processing)
    
    Args:
        ticket_id (int): The ticket ID to process
        
    Returns:
        Dict[str, Any]: Pipeline processing results
    """
    logger.info(f"Manual triggered pipeline for ticket {ticket_id}")
    return process_ticket_pipeline(ticket_id, trigger_source="manual")


def get_pipeline_status(ticket_id: int) -> Dict[str, Any]:
    """
    Get the current pipeline status for a ticket by checking audit logs
    
    Args:
        ticket_id (int): The ticket ID to check
        
    Returns:
        Dict[str, Any]: Status information about pipeline processing
    """
    try:
        from tickets.models import AuditLog
        
        # Get all audit logs for this ticket
        audit_logs = AuditLog.objects.filter(ticket_id=ticket_id).order_by('-timestamp')
        
        status = {
            'ticket_id': ticket_id,
            'pipeline_run': False,
            'completeness_check_run': False,
            'draft_response_created': False,
            'last_pipeline_run': None,
            'audit_log_count': audit_logs.count()
        }
        
        for log in audit_logs:
            if log.function == 'integrated_pipeline':
                status['pipeline_run'] = True
                status['last_pipeline_run'] = log.timestamp.isoformat()
                if isinstance(log.message, dict):
                    status['last_pipeline_success'] = log.message.get('response', {}).get('overall_success', False)
                break
        
        # Check for individual components
        for log in audit_logs:
            if log.function == 'completeness_checker':
                status['completeness_check_run'] = True
                if isinstance(log.message, dict):
                    status['completeness_score'] = log.message.get('response', {}).get('completeness_score')
            elif log.function == 'draft_response_creator':
                status['draft_response_created'] = True
                if isinstance(log.message, dict):
                    response_data = log.message.get('response', {})
                    status['draft_response_length'] = response_data.get('response_length')
                    status['draft_response_success'] = response_data.get('success')
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting pipeline status for ticket {ticket_id}: {str(e)}")
        return {
            'ticket_id': ticket_id,
            'error': str(e),
            'pipeline_run': False
        }


# Testing and validation functions
def test_integrated_pipeline(ticket_id: int = None) -> Dict[str, Any]:
    """
    Test the integrated pipeline with a specific ticket or create a test scenario
    
    Args:
        ticket_id (int, optional): Specific ticket ID to test with
        
    Returns:
        Dict[str, Any]: Test results
    """
    if not ticket_id:
        # Try to find a ticket to test with
        try:
            from tickets.models import Ticket
            test_ticket = Ticket.objects.filter(
                description__isnull=False,
                support_theme__isnull=False
            ).first()
            
            if test_ticket:
                ticket_id = test_ticket.id
                logger.info(f"Using ticket {ticket_id} for pipeline testing")
            else:
                return {'error': 'No suitable test ticket found'}
                
        except Exception as e:
            return {'error': f'Failed to find test ticket: {str(e)}'}
    
    logger.info(f"Testing integrated pipeline with ticket {ticket_id}")
    
    # Run the pipeline
    test_results = process_ticket_pipeline(ticket_id, trigger_source="pipeline_test")
    
    # Add test metadata
    test_results['test_mode'] = True
    test_results['test_timestamp'] = timezone.now().isoformat()
    
    return test_results 