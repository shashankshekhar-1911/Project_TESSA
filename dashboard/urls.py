from django.urls import path
from .views import dashboard_home, ticket_detail, welcome_screen, completeness_checker, input_checklist_viewer

urlpatterns = [
    path("", welcome_screen, name="welcome"),
    path("ticket/<int:ticket_id>/", ticket_detail, name="ticket-detail"),
    path("completeness-checker/", completeness_checker, name="completeness-checker"),
    path("input-checklist/", input_checklist_viewer, name="input-checklist"),
]
