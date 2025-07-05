from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Ticket, AuditLog
from .serializers import TicketSerializer
from agents.pipeline import agent_pipeline
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Avg, Count
from django.utils import timezone
from .models import CompletenessChecklist, InputNeededChecklist, InputNeededGlossary
from .utils import get_audit_logs_for_ticket
import json

class WebhookTicketAPIView(APIView):
    """
    Receives POSTs from Zendesk/Jira webhooks, runs the agent pipeline, and saves the ticket.
    """
    def post(self, request):
        # Extract the ticket data from the nested structure
        ticket = request.data.get("ticket", {})

        # Map the fields from the incoming data to your model fields
        ticket_data = {
            "subject": ticket.get("subject", ""),
            "description": ticket.get("description", ""),
            "status": ticket.get("status", ""),
            "priority": ticket.get("priority", ""),
            "created_at": ticket.get("created_at", None),  # Adjust if you have a specific format
            "updated_at": ticket.get("updated_at", None),  # Adjust if you have a specific format
            "requester": ticket.get("requester", ""),  # Adjust based on actual data
            "assignee": ticket.get("assignee", ""),  # Adjust based on actual data
            "type": ticket.get("type", ""),  # Adjust based on actual data
            "tags": ",".join(ticket.get("tags", [])) if isinstance(ticket.get("tags"), list) else ticket.get("tags", ""),
        }

        # Run through the AI agent pipeline
        ticket_data = agent_pipeline(ticket_data)
        serializer = TicketSerializer(data=ticket_data)
        
        if not serializer.is_valid():
            print(serializer.errors)  # Log the validation errors
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@require_http_methods(["GET"])
def test_api(request):
    """Simple test endpoint to verify API is working"""
    return JsonResponse({
        'status': 'success',
        'message': 'API is working correctly',
        'timestamp': timezone.now().isoformat()
    })

@require_http_methods(["GET"])
def pipeline_metrics(request):
    """
    API endpoint for dashboard metrics
    Returns current pipeline statistics for Metabase integration
    """
    try:
        # Basic ticket statistics
        total_tickets = Ticket.objects.count()
        processed_tickets = Ticket.objects.filter(completeness_score__isnull=False).count()
        incomplete_tickets = Ticket.objects.filter(completeness_score__lt=80).count()
        drafts_available = Ticket.objects.filter(l1_response_draft__isnull=False).count()
        
        # Calculate average completeness
        avg_completeness = Ticket.objects.filter(
            completeness_score__isnull=False
        ).aggregate(Avg('completeness_score'))['completeness_score__avg']
        
        # Recent activity (last 24 hours)
        yesterday = timezone.now() - timezone.timedelta(hours=24)
        recent_processed = Ticket.objects.filter(
            last_rag_processed__gte=yesterday
        ).count()
        recent_drafts = Ticket.objects.filter(
            draft_generated_at__gte=yesterday
        ).count()
        
        # Support theme breakdown - simplified to avoid JSON query issues
        theme_stats = []
        all_checklists = CompletenessChecklist.objects.all()
        for checklist in all_checklists:
            theme_stats.append({
                'theme': checklist.support_theme,
                'ticket_count': 0,  # Will be updated when JSON queries are fixed
                'priority': checklist.priority
            })
        
        # Completeness distribution
        completeness_ranges = [
            {'range': '0-20%', 'count': Ticket.objects.filter(completeness_score__gte=0, completeness_score__lt=20).count()},
            {'range': '20-40%', 'count': Ticket.objects.filter(completeness_score__gte=20, completeness_score__lt=40).count()},
            {'range': '40-60%', 'count': Ticket.objects.filter(completeness_score__gte=40, completeness_score__lt=60).count()},
            {'range': '60-80%', 'count': Ticket.objects.filter(completeness_score__gte=60, completeness_score__lt=80).count()},
            {'range': '80-100%', 'count': Ticket.objects.filter(completeness_score__gte=80).count()},
        ]
        
        metrics = {
            'summary': {
                'total_tickets': total_tickets,
                'processed_tickets': processed_tickets,
                'incomplete_tickets': incomplete_tickets,
                'drafts_available': drafts_available,
                'average_completeness': round(avg_completeness or 0, 2),
                'processing_rate': round((processed_tickets / total_tickets * 100) if total_tickets > 0 else 0, 2)
            },
            'recent_activity': {
                'tickets_processed_24h': recent_processed,
                'drafts_generated_24h': recent_drafts
            },
            'theme_breakdown': theme_stats,
            'completeness_distribution': completeness_ranges,
            'system_info': {
                'total_support_themes': CompletenessChecklist.objects.count(),
                'total_checklist_items': InputNeededChecklist.objects.count(),
                'glossary_entries': InputNeededGlossary.objects.count()
            },
            'updated_at': timezone.now().isoformat()
        }
        
        return JsonResponse(metrics)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=500)


@require_http_methods(["GET"])
def ticket_details(request, ticket_id):
    """
    API endpoint to get detailed ticket information
    Including completeness analysis and L1 draft
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        
        # Get theme information
        theme = ticket.get_support_theme_from_tags()
        
        data = {
            'ticket_info': {
                'id': ticket.id,
                'encoded_id': ticket.encoded_id,
                'subject': ticket.subject,
                'status': ticket.status,
                'priority': ticket.priority,
                'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                'tags': ticket.tags or []
            },
            'completeness_analysis': {
                'score': ticket.completeness_score,
                'missing_items': ticket.missing_info or [],
                'support_theme': theme,
                'last_analyzed': ticket.last_rag_processed.isoformat() if ticket.last_rag_processed else None
            },
            'l1_response': {
                'draft_available': bool(ticket.l1_response_draft),
                'draft_content': ticket.l1_response_draft,
                'generated_at': ticket.draft_generated_at.isoformat() if ticket.draft_generated_at else None
            }
        }
        
        return JsonResponse(data)
        
    except Ticket.DoesNotExist:
        return JsonResponse({
            'error': 'Ticket not found',
            'status': 'not_found'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=500)


@require_http_methods(["GET"])
def incomplete_tickets(request):
    """
    API endpoint to get list of incomplete tickets
    For L1 agents to prioritize follow-up
    """
    try:
        # Get incomplete tickets with drafts available
        incomplete = Ticket.objects.filter(
            completeness_score__lt=80,
            l1_response_draft__isnull=False
        ).order_by('completeness_score', '-created_at')[:20]
        
        tickets_data = []
        for ticket in incomplete:
            tickets_data.append({
                'id': ticket.id,
                'encoded_id': ticket.encoded_id,
                'subject': ticket.subject[:100] + '...' if len(ticket.subject) > 100 else ticket.subject,
                'completeness_score': ticket.completeness_score,
                'missing_items_count': len(ticket.missing_info or []),
                'support_theme': ticket.get_support_theme_from_tags(),
                'priority': ticket.priority,
                'draft_available': True,
                'created_at': ticket.created_at.isoformat() if ticket.created_at else None
            })
        
        return JsonResponse({
            'incomplete_tickets': tickets_data,
            'total_count': len(tickets_data),
            'updated_at': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def trigger_pipeline_api(request):
    """
    API endpoint to manually trigger pipeline for specific tickets
    For dashboard integration and manual processing
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
        ticket_ids = data.get('ticket_ids', [])
        force = data.get('force', False)
        
        if not ticket_ids:
            return JsonResponse({
                'error': 'No ticket IDs provided',
                'status': 'error'
            }, status=400)
        
        results = {
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'task_ids': []
        }
        
        for ticket_id in ticket_ids:
            try:
                ticket = Ticket.objects.get(id=ticket_id)
                
                # Check if already processed
                if not force and ticket.completeness_score is not None:
                    results['skipped'] += 1
                    continue
                
                # Try to use Celery if available, otherwise process synchronously
                try:
                    from .tasks import trigger_completeness_pipeline
                    task_result = trigger_completeness_pipeline.delay(ticket_id)
                    results['task_ids'].append(task_result.id)
                except ImportError:
                    # Fallback to synchronous processing
                    from .management.commands.analyze_completeness import Command
                    analyzer = Command()
                    analyzer.analyze_ticket(ticket, {}, {}, [])
                
                results['processed'] += 1
                
            except Ticket.DoesNotExist:
                results['errors'] += 1
        
        return JsonResponse({
            'status': 'success',
            'results': results,
            'message': f'Triggered pipeline for {results["processed"]} tickets'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON',
            'status': 'error'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=500)


class TicketAuditLogAPIView(APIView):
    """
    API view to retrieve audit logs for a specific ticket
    """
    def get(self, request, ticket_id):
        try:
            # Check if ticket exists
            try:
                ticket = Ticket.objects.get(id=ticket_id)
            except Ticket.DoesNotExist:
                return Response(
                    {'error': f'Ticket with id {ticket_id} not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get function filter if provided
            function_name = request.query_params.get('function')
            
            # Retrieve audit logs
            audit_logs = get_audit_logs_for_ticket(ticket_id, function_name)
            
            # Format response data
            audit_data = []
            for log in audit_logs:
                audit_data.append({
                    'audit_id': str(log.audit_id),
                    'function': log.function,
                    'ticket_id': log.ticket_id,
                    'timestamp': log.timestamp.isoformat(),
                    'message': log.message
                })
            
            return Response({
                'ticket_id': ticket_id,
                'encoded_id': ticket.encoded_id,
                'total_audit_logs': len(audit_data),
                'function_filter': function_name,
                'audit_logs': audit_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Error retrieving audit logs: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditLogSummaryAPIView(APIView):
    """
    API view to get audit log summary statistics
    """
    def get(self, request):
        try:
            # Get summary statistics
            total_logs = AuditLog.objects.count()
            functions = AuditLog.objects.values('function').annotate(
                count=Count('function')
            ).order_by('-count')
            
            # Recent activity (last 24 hours)
            from datetime import datetime, timedelta
            yesterday = timezone.now() - timedelta(days=1)
            recent_logs = AuditLog.objects.filter(
                timestamp__gte=yesterday
            ).count()
            
            return Response({
                'total_audit_logs': total_logs,
                'recent_logs_24h': recent_logs,
                'function_breakdown': list(functions),
                'generated_at': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Error retrieving audit summary: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
