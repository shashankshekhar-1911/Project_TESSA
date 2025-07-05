from django.urls import path
from .views import ticket_detail, input_checklist_viewer
from .webhooks import zendesk_webhook_handler, test_webhook
from .api_views import TicketAuditLogAPIView, AuditLogSummaryAPIView

app_name = 'tickets'

urlpatterns = [
    path('<int:ticket_id>/', ticket_detail, name='ticket-detail'),
    path('input-checklist/', input_checklist_viewer, name='input-checklist'),
    
    # Webhook endpoints (function-based views only)
    path('webhook/zendesk/', zendesk_webhook_handler, name='zendesk-webhook'),
    path('webhook/test/', test_webhook, name='test-webhook'),
    
    # Audit log API endpoints
    path('api/audit-logs/<int:ticket_id>/', TicketAuditLogAPIView.as_view(), name='ticket-audit-logs'),
    path('api/audit-logs/summary/', AuditLogSummaryAPIView.as_view(), name='audit-logs-summary'),
] 