import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views import View
from django.utils import timezone
from .models import Ticket
from .utils import process_ticket_with_ai, extract_ai_reasoning
import pandas as pd

# Try to import celery tasks, but make it optional
try:
    from .tasks import trigger_completeness_pipeline
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    trigger_completeness_pipeline = None

logger = logging.getLogger(__name__)


# Define the mapping between custom field IDs and names (from parse_tickets 1.py)
CUSTOM_FIELD_MAPPING = {
    12713190866711: 'severity',
    12914744896791: 'ticket_type',
    14382186096919: 'summary',
    29660953136279: 'product',
    30235222279191: 'support_theme'
}


def parse_custom_fields(custom_fields_data):
    """
    Parse the custom fields from Zendesk webhook data into a dictionary with named fields.
    
    Args:
        custom_fields_data: Can be a JSON string, list, or already parsed data
        
    Returns:
        dict: Dictionary with named fields mapped from field IDs
    """
    try:
        # Handle different input types
        if isinstance(custom_fields_data, str):
            if pd.isna(custom_fields_data) or not custom_fields_data.strip():
                return {}
            fields_list = json.loads(custom_fields_data)
        elif isinstance(custom_fields_data, list):
            fields_list = custom_fields_data
        elif custom_fields_data is None:
            return {}
        else:
            # Assume it's already a dict or similar structure
            return custom_fields_data
        
        # Create a new dictionary with named fields
        named_fields = {}
        for field in fields_list:
            if isinstance(field, dict):
                field_id = field.get('id')
                field_value = field.get('value')
                
                # Map the numeric ID to the field name if it exists in our mapping
                if field_id in CUSTOM_FIELD_MAPPING:
                    field_name = CUSTOM_FIELD_MAPPING[field_id]
                    named_fields[field_name] = field_value
        
        return named_fields
        
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        logger.warning(f"Error parsing custom fields: {str(e)}")
        return {}


def parse_via(via_data):
    """
    Parse the via field to extract channel information.
    
    Args:
        via_data: Can be a JSON string, dict, or already parsed data
        
    Returns:
        dict: Dictionary with channel information
    """
    try:
        # Handle different input types
        if isinstance(via_data, str):
            if pd.isna(via_data) or not via_data.strip():
                return {'channel': 'unknown'}
            parsed_via = json.loads(via_data)
        elif isinstance(via_data, dict):
            parsed_via = via_data
        elif via_data is None:
            return {'channel': 'unknown'}
        else:
            return {'channel': 'unknown'}
        
        # Extract channel and source information
        return {
            'channel': parsed_via.get('channel', 'unknown'),
            'source': parsed_via.get('source', {})
        }
        
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        logger.warning(f"Error parsing via field: {str(e)}")
        return {'channel': 'unknown'}


@csrf_exempt
@require_http_methods(["POST"])
def zendesk_webhook_handler(request):
    """
    Handle ZenDesk webhook notifications
    Processes ticket creation/updates and triggers AI analysis
    """
    try:
        # Parse webhook data
        webhook_data = json.loads(request.body.decode('utf-8'))
        logger.info(f"Received ZenDesk webhook: {webhook_data.get('type', 'unknown')}")
        
        # Extract ticket data
        ticket_data = webhook_data.get('ticket', {})
        if not ticket_data:
            logger.warning("No ticket data in webhook")
            return JsonResponse({'error': 'No ticket data provided'}, status=400)
        
        # Create or update ticket
        ticket = update_ticket_from_webhook(ticket_data)
        
        # Trigger AI processing in background
        try:
            # Process immediately (for testing) or queue for background processing
            ai_processed = process_ticket_with_ai(ticket.id)
            
            # NEW: Also trigger TESSA pipeline with audit logging
            tessa_results = {}
            try:
                # Import TESSA functions
                import sys
                sys.path.append('agents')
                from agents.completeness_checker import process_completeness_check
                from agents.draft_response_creator import process_draft_response_creator
                
                # Run completeness check with audit logging
                logger.info(f"Running TESSA completeness check for ticket {ticket.ticket_id}")
                completeness_result = process_completeness_check(ticket.ticket_id)
                tessa_results['completeness'] = completeness_result.get('audit_logged', False)
                
                # Run draft response creator with audit logging  
                logger.info(f"Running TESSA draft response creator for ticket {ticket.ticket_id}")
                response_result = process_draft_response_creator(ticket.ticket_id, post_to_zendesk=False)
                tessa_results['draft_response'] = response_result.get('audit_logged', False)
                
                logger.info(f"TESSA pipeline completed for ticket {ticket.encoded_id}: {tessa_results}")
                
            except Exception as tessa_error:
                logger.error(f"Error in TESSA pipeline for ticket {ticket.id}: {str(tessa_error)}")
                tessa_results['error'] = str(tessa_error)
            
            if ai_processed:
                logger.info(f"AI processing completed for ticket {ticket.encoded_id}")
                # Log successful webhook processing
                from .utils import log_audit_event
                log_audit_event(
                    function_name="zendesk_webhook_handler",
                    ticket_id=ticket.ticket_id,
                    response_data={
                        "status": "success",
                        "ticket_created": ticket.pk,
                        "ai_processed": True,
                        "tessa_pipeline": tessa_results,
                        "webhook_type": webhook_data.get('type', 'unknown'),
                        "parsed_via": ticket.via,
                        "custom_fields_parsed": bool(ticket_data.get('custom_fields'))
                    },
                    additional_context={
                        "encoded_id": ticket.encoded_id,
                        "zendesk_id": ticket.ticket_id,
                        "via_channel": ticket.via.get('channel', 'unknown') if ticket.via else 'unknown',
                        "tessa_completeness_logged": tessa_results.get('completeness', False),
                        "tessa_response_logged": tessa_results.get('draft_response', False)
                    }
                )
            else:
                logger.warning(f"AI processing failed/skipped for ticket {ticket.encoded_id}")
                
        except Exception as e:
            logger.error(f"Error in AI processing for ticket {ticket.id}: {str(e)}")
            # Continue - don't fail webhook due to AI processing errors
        
        # Trigger completeness pipeline if available
        try:
            from .tasks import trigger_completeness_pipeline
            trigger_completeness_pipeline.delay(ticket.id)
            logger.info(f"Queued completeness pipeline for ticket {ticket.encoded_id}")
        except ImportError:
            logger.info("Celery not available, skipping background pipeline")
        except Exception as e:
            logger.error(f"Error queuing pipeline for ticket {ticket.id}: {str(e)}")
        
        return JsonResponse({
            'status': 'success',
            'ticket_id': ticket.id,
            'encoded_id': ticket.encoded_id,
            'ai_processed': ai_processed if 'ai_processed' in locals() else False,
            'message': 'Ticket processed successfully'
        })
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook request")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def update_ticket_from_webhook(ticket_data):
    """
    Create or update ticket from ZenDesk webhook data
    Returns the ticket instance
    """
    # Extract key identifiers
    zendesk_id = ticket_data.get('id')
    external_id = ticket_data.get('external_id')
    
    # Find existing ticket or create new one
    ticket = None
    if zendesk_id:
        try:
            ticket = Ticket.objects.get(ticket_id=zendesk_id)
            logger.info(f"Updating existing ticket {ticket.encoded_id}")
        except Ticket.DoesNotExist:
            pass
    
    if not ticket and external_id:
        try:
            ticket = Ticket.objects.get(external_id=external_id)
            logger.info(f"Found ticket by external_id: {ticket.encoded_id}")
        except Ticket.DoesNotExist:
            pass
    
    # Create new ticket if not found
    if not ticket:
        ticket = Ticket()
        logger.info(f"Creating new ticket for ZenDesk ID {zendesk_id}")
    
    # Parse via and custom fields using the parsing functions
    via_data = parse_via(ticket_data.get('via'))
    custom_fields_data = parse_custom_fields(ticket_data.get('custom_fields', []))
    
    # Map webhook data to ticket fields
    ticket.ticket_id = zendesk_id
    ticket.external_id = external_id
    ticket.subject = ticket_data.get('subject', '')
    ticket.description = ticket_data.get('description', '')
    ticket.raw_subject = ticket_data.get('raw_subject', ticket_data.get('subject', ''))
    ticket.status = ticket_data.get('status', 'new')
    ticket.priority = ticket_data.get('priority', 'normal')
    ticket.type = ticket_data.get('type', '')
    ticket.recipient = ticket_data.get('recipient', '')
    
    # Store via data as JSON
    ticket.via = via_data
    
    # Map custom fields to TESSA-specific fields (overriding basic priority if provided)
    if custom_fields_data.get('severity'):
        ticket.severity = custom_fields_data['severity']
    if custom_fields_data.get('ticket_type'):
        ticket.ticket_type = custom_fields_data['ticket_type']  
    if custom_fields_data.get('summary'):
        ticket.summary = custom_fields_data['summary']
    if custom_fields_data.get('product'):
        ticket.product = custom_fields_data['product']
    if custom_fields_data.get('support_theme'):
        ticket.support_theme = custom_fields_data['support_theme']

    # Parse timestamps
    if ticket_data.get('created_at'):
        try:
            ticket.created_at = timezone.datetime.fromisoformat(
                ticket_data['created_at'].replace('Z', '+00:00')
            )
        except:
            pass
    
    if ticket_data.get('updated_at'):
        try:
            ticket.updated_at = timezone.datetime.fromisoformat(
                ticket_data['updated_at'].replace('Z', '+00:00')
            )
        except:
            pass
    
    # User relationships
    ticket.requester_id = ticket_data.get('requester_id')
    ticket.submitter_id = ticket_data.get('submitter_id')
    ticket.assignee_id = ticket_data.get('assignee_id')
    ticket.organization_id = ticket_data.get('organization_id')
    ticket.group_id = ticket_data.get('group_id')
    
    # Array fields
    ticket.tags = ticket_data.get('tags', [])
    ticket.collaborator_ids = ticket_data.get('collaborator_ids', [])
    ticket.follower_ids = ticket_data.get('follower_ids', [])
    ticket.email_cc_ids = ticket_data.get('email_cc_ids', [])
    
    # Additional ZenDesk fields
    ticket.forum_topic_id = ticket_data.get('forum_topic_id')
    ticket.problem_id = ticket_data.get('problem_id')
    ticket.has_incidents = ticket_data.get('has_incidents', False)
    ticket.is_public = ticket_data.get('is_public', True)
    ticket.custom_status_id = ticket_data.get('custom_status_id')
    ticket.ticket_form_id = ticket_data.get('ticket_form_id')
    ticket.brand_id = ticket_data.get('brand_id')
    ticket.allow_channelback = ticket_data.get('allow_channelback', True)
    ticket.allow_attachments = ticket_data.get('allow_attachments', True)
    
    # Generate encoded ID if not present
    if not ticket.encoded_id:
        import random
        import string
        ticket.encoded_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=13))
    
    # Save ticket
    ticket.save()
    
    logger.info(f"Ticket {ticket.encoded_id} saved successfully")
    return ticket


@csrf_exempt  
@require_http_methods(["POST"])
def test_webhook(request):
    """
    Test endpoint for webhook integration
    """
    try:
        # Create test ticket data with via and custom_fields
        test_ticket_data = {
            "id": 999999,
            "subject": "Test AI Processing - Login Issue",
            "description": "User cannot login to IVMS system. Getting error message 'Invalid credentials' even with correct username and password. Browser: Chrome. Environment: Production.",
            "status": "new",
            "priority": "high",
            "tags": ["ivms", "login", "urgent"],
            "created_at": timezone.now().isoformat(),
            "requester_id": 12345,
            "organization_id": 67890,
            "via": {
                "channel": "web",
                "source": {
                    "from": {"name": "Test User", "address": "test@example.com"},
                    "to": {"name": "Support Team", "address": "support@example.com"}
                }
            },
            "custom_fields": [
                {"id": 12713190866711, "value": "high"},          # severity
                {"id": 12914744896791, "value": "bug"},           # ticket_type  
                {"id": 14382186096919, "value": "Login failure"}, # summary
                {"id": 29660953136279, "value": "IVMS"},          # product
                {"id": 30235222279191, "value": "Access and Login Issues"}  # support_theme
            ]
        }
        
        # Process through webhook handler
        webhook_payload = {"ticket": test_ticket_data}
        
        # Simulate webhook processing
        ticket = update_ticket_from_webhook(test_ticket_data)
        ai_processed = process_ticket_with_ai(ticket.id)
        
        # Get updated ticket
        ticket.refresh_from_db()
        
        return JsonResponse({
            'status': 'success',
            'test_ticket_id': ticket.id,
            'encoded_id': ticket.encoded_id,
            'ai_processed': ai_processed,
            'ai_analysis': {
                'product': ticket.product,
                'support_theme': ticket.support_theme,
                'severity': ticket.severity,
                'ticket_type': ticket.ticket_type,
                'priority': ticket.priority,
                'summary': ticket.summary
            },
            'message': 'Test webhook processing completed'
        })
        
    except Exception as e:
        logger.error(f"Test webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def zendesk_webhook_handler_old(request):
    """
    Handle webhook notifications from ZenDesk
    Triggered when tickets are created, updated, or have any activity
    """
    try:
        # Parse webhook payload
        payload = json.loads(request.body.decode('utf-8'))
        
        # Extract ticket information
        ticket_data = payload.get('ticket', {})
        ticket_id = ticket_data.get('id')
        
        if not ticket_id:
            logger.warning("Webhook received without ticket ID")
            return JsonResponse({'status': 'error', 'message': 'No ticket ID provided'}, status=400)
        
        # Update or create ticket in our database
        ticket, created = update_ticket_from_webhook(ticket_data)
        
        # Trigger the automated pipeline if Celery is available
        if CELERY_AVAILABLE and trigger_completeness_pipeline:
            trigger_completeness_pipeline.delay(ticket.id)
            pipeline_status = "triggered"
        else:
            # Run synchronously if Celery is not available
            from .management.commands.analyze_completeness import Command
            analyzer = Command()
            analyzer.analyze_ticket(ticket, {}, {}, [])
            pipeline_status = "executed_sync"
        
        action = "created" if created else "updated"
        logger.info(f"Ticket {ticket_id} {action} via webhook")
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Ticket {action} and pipeline {pipeline_status}',
            'ticket_id': ticket.id
        })
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Processing error'}, status=500)


@csrf_exempt 
class ZenDeskWebhookView(View):
    """
    Class-based view for handling ZenDesk webhooks
    Provides more flexibility for different webhook types
    """
    
    def post(self, request):
        return zendesk_webhook_handler(request)
    
    def get(self, request):
        # For webhook verification
        return JsonResponse({'status': 'webhook_endpoint_active'}) 