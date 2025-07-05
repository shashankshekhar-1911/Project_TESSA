from django.urls import path
from .api_views import (
    WebhookTicketAPIView, 
    pipeline_metrics, 
    ticket_details, 
    incomplete_tickets, 
    trigger_pipeline_api,
    test_api
)

urlpatterns = [
    path("tickets/webhook/", WebhookTicketAPIView.as_view(), name="ticket-webhook"),
    
    # Test endpoint
    path("test/", test_api, name="test-api"),
    
    # Pipeline and metrics endpoints
    path("metrics/", pipeline_metrics, name="pipeline-metrics"),
    path("tickets/<int:ticket_id>/", ticket_details, name="ticket-details"),
    path("tickets/incomplete/", incomplete_tickets, name="incomplete-tickets"),
    path("pipeline/trigger/", trigger_pipeline_api, name="trigger-pipeline"),
]
