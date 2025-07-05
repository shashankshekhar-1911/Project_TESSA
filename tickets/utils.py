from django.utils import timezone
from .models import Ticket, AuditLog
import logging
import uuid

logger = logging.getLogger(__name__)


def log_audit_event(function_name, ticket_id, response_data, additional_context=None):
    """
    Log an audit event for TESSA function invocations
    
    Args:
        function_name (str): Name of the function being invoked
        ticket_id (int): ID of the ticket being processed  
        response_data (dict): TESSA response data
        additional_context (dict): Additional context data (optional)
    
    Returns:
        AuditLog: Created audit log instance
    """
    try:
        # Prepare audit message
        audit_message = {
            'response': response_data,
            'function': function_name,
            'ticket_id': ticket_id,
            'timestamp': timezone.now().isoformat()
        }
        
        # Add additional context if provided
        if additional_context:
            audit_message['context'] = additional_context
        
        # Create audit log entry
        audit_log = AuditLog.objects.create(
            function=function_name,
            ticket_id=ticket_id,
            message=response_data
        )
        
        logger.info(f"Audit log created: {audit_log.audit_id} for function {function_name}")
        return audit_log
        
    except Exception as e:
        logger.error(f"Failed to create audit log for {function_name}: {str(e)}")
        return None


def get_audit_logs_for_ticket(ticket_id, function_name=None):
    """
    Retrieve audit logs for a specific ticket
    
    Args:
        ticket_id (int): ID of the ticket
        function_name (str): Optional filter by function name
    
    Returns:
        QuerySet: Filtered audit logs
    """
    logs = AuditLog.objects.filter(ticket_id=ticket_id)
    
    if function_name:
        logs = logs.filter(function=function_name)
    
    return logs.order_by('-timestamp')


def process_ticket_with_ai(ticket_id):
    """
    Process a ticket through the AI request processor and update the ticket fields
    """
    try:
        # Import here to handle missing dependencies gracefully
        from agents.request_processor import process_ticket
        
        # Get the ticket
        ticket = Ticket.objects.get(id=ticket_id)
        
        # Prepare ticket metadata for the request processor
        ticket_metadata = {
            "plain_body": ticket.description or "",
            "subject": ticket.subject or "",
            "priority": ticket.priority or "",
            "status": ticket.status or "",
            "tags": ticket.tags or []
        }
        
        # Process through AI pipeline
        logger.info(f"Processing ticket {ticket.encoded_id} through AI pipeline...")
        processed_state = process_ticket(ticket_metadata)
        
        # Log audit event for AI processing
        log_audit_event(
            function_name="process_ticket_with_ai",
            ticket_id=ticket.ticket_id,
            response_data={
                "ai_analysis": processed_state,
                "input_metadata": ticket_metadata,
                "status": "success"
            },
            additional_context={
                "encoded_id": ticket.encoded_id,
                "original_priority": ticket.priority
            }
        )
        
        # Update ticket fields with AI analysis
        updates = update_ticket_from_ai_analysis(ticket, processed_state)
        
        # Mark as processed
        ticket.last_rag_processed = timezone.now()
        ticket.save()
        
        logger.info(f"Successfully processed ticket {ticket.encoded_id}")
        return True
        
    except ImportError as e:
        logger.warning(f"AI processing dependencies not available: {str(e)}")
        # Log audit event for failure
        try:
            # Get the ticket to access ticket_id for consistent logging
            ticket = Ticket.objects.get(id=ticket_id)
            log_audit_event(
                function_name="process_ticket_with_ai",
                ticket_id=ticket.ticket_id,
                response_data={
                    "status": "failed",
                    "error": "ImportError - AI dependencies not available",
                    "error_details": str(e)
                }
            )
        except:
            # Fallback if ticket lookup fails
            log_audit_event(
                function_name="process_ticket_with_ai",
                ticket_id=ticket_id,
                response_data={
                    "status": "failed",
                    "error": "ImportError - AI dependencies not available",
                    "error_details": str(e)
                }
            )
        return False
    except Exception as e:
        logger.error(f"Error processing ticket {ticket_id}: {str(e)}")
        # Log audit event for error
        try:
            # Get the ticket to access ticket_id for consistent logging
            ticket = Ticket.objects.get(id=ticket_id)
            log_audit_event(
                function_name="process_ticket_with_ai", 
                ticket_id=ticket.ticket_id,
                response_data={
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
        except:
            # Fallback if ticket lookup fails
            log_audit_event(
                function_name="process_ticket_with_ai", 
                ticket_id=ticket_id,
                response_data={
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
        return False


def update_ticket_from_ai_analysis(ticket, ai_state):
    """
    Update ticket fields based on AI analysis results
    """
    # Helper function to extract value from AI response
    def get_ai_value(field_data, default=None):
        if isinstance(field_data, dict) and 'value' in field_data:
            return field_data['value']
        return default
    
    # Map AI analysis to ticket fields
    mapping_updates = {}
    
    # Priority
    if ai_state.get('priority'):
        ai_priority = get_ai_value(ai_state['priority'])
        if ai_priority:
            mapping_updates['priority'] = ai_priority.lower()
    
    # Organization (map to organization_id field)
    if ai_state.get('organization_id'):
        org_value = get_ai_value(ai_state['organization_id'])
        if org_value and org_value != 'Unknown':
            # Store as string in existing field or create organization lookup
            mapping_updates['organization_id'] = hash(org_value) % 10000  # Simple hash for ID
    
    # Product
    if ai_state.get('product'):
        product_value = get_ai_value(ai_state['product'])
        if product_value and product_value != 'Unknown':
            mapping_updates['product'] = product_value
    
    # Support Theme
    if ai_state.get('support_theme'):
        theme_value = get_ai_value(ai_state['support_theme'])
        if theme_value:
            mapping_updates['support_theme'] = theme_value
    
    # Summary
    if ai_state.get('summary'):
        summary_value = get_ai_value(ai_state['summary'])
        if summary_value:
            mapping_updates['summary'] = summary_value[:500]  # Limit length
    
    # Severity
    if ai_state.get('severity'):
        severity_value = get_ai_value(ai_state['severity'])
        if severity_value:
            mapping_updates['severity'] = severity_value.lower()
    
    # Ticket Type
    if ai_state.get('ticket_type'):
        type_value = get_ai_value(ai_state['ticket_type'])
        if type_value:
            mapping_updates['ticket_type'] = type_value
    
    # Interface Affected
    if ai_state.get('interface_affected'):
        interface_value = get_ai_value(ai_state['interface_affected'])
        if interface_value:
            mapping_updates['interface_affected'] = interface_value
    
    # Code Change
    if ai_state.get('code_change'):
        code_value = get_ai_value(ai_state['code_change'])
        if code_value:
            mapping_updates['code_change'] = code_value
    
    # Module
    if ai_state.get('module'):
        module_value = get_ai_value(ai_state['module'])
        if module_value:
            mapping_updates['module'] = module_value
    
    # Workaround
    if ai_state.get('workaround'):
        workaround_value = get_ai_value(ai_state['workaround'])
        if workaround_value:
            mapping_updates['workaround'] = workaround_value
    
    # Effort
    if ai_state.get('effort_aidash'):
        effort_value = get_ai_value(ai_state['effort_aidash'])
        if effort_value:
            mapping_updates['effort_aidash'] = effort_value
    
    # Urgency
    if ai_state.get('urgency'):
        urgency_value = get_ai_value(ai_state['urgency'])
        if urgency_value:
            mapping_updates['urgency'] = urgency_value.lower()
    
    # Update ticket with all mapped fields
    for field, value in mapping_updates.items():
        setattr(ticket, field, value)
    
    # Log the updates
    logger.info(f"Updated ticket {ticket.encoded_id} with AI analysis: {list(mapping_updates.keys())}")
    
    return mapping_updates


def extract_ai_reasoning(ai_state):
    """
    Extract reasoning from AI analysis for logging/debugging
    """
    reasoning_summary = {}
    
    for field_name, field_data in ai_state.items():
        if isinstance(field_data, dict) and 'reasoning' in field_data:
            reasoning_summary[field_name] = field_data['reasoning']
    
    return reasoning_summary


def process_ticket_metadata_for_ai(ticket):
    """
    Prepare ticket data in the format expected by the request processor
    """
    return {
        "plain_body": ticket.description or "",
        "subject": ticket.subject or "", 
        "priority": ticket.priority or "",
        "status": ticket.status or "",
        "tags": ticket.tags or [],
        "created_at": ticket.created_at.isoformat() if ticket.created_at else "",
        "ticket_id": ticket.ticket_id or ticket.id,
        "encoded_id": ticket.encoded_id or ""
    } 