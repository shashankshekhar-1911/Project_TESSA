from django.contrib import admin
from .models import Ticket, CompletenessChecklist, InputNeededChecklist, InputNeededGlossary, AuditLog

@admin.register(InputNeededChecklist)
class InputNeededChecklistAdmin(admin.ModelAdmin):
    list_display = ['support_theme', 'input_needed_truncated', 'priority', 'created_at']
    list_filter = ['support_theme', 'priority', 'created_at']
    search_fields = ['support_theme', 'input_needed']
    ordering = ['support_theme', '-priority', 'input_needed']
    
    def input_needed_truncated(self, obj):
        return obj.input_needed[:100] + "..." if len(obj.input_needed) > 100 else obj.input_needed
    input_needed_truncated.short_description = 'Input Needed'


@admin.register(InputNeededGlossary)
class InputNeededGlossaryAdmin(admin.ModelAdmin):
    list_display = ['support_theme', 'description_truncated', 'created_at']
    search_fields = ['support_theme', 'description']
    ordering = ['support_theme']
    
    def description_truncated(self, obj):
        return obj.description[:150] + "..." if len(obj.description) > 150 else obj.description
    description_truncated.short_description = 'Description'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['audit_id_short', 'function', 'ticket_id', 'timestamp', 'message_preview']
    list_filter = ['function', 'timestamp']
    search_fields = ['function', 'ticket_id', 'audit_id']
    ordering = ['-timestamp']
    readonly_fields = ['audit_id', 'timestamp', 'function', 'ticket_id', 'message']
    
    def audit_id_short(self, obj):
        return str(obj.audit_id)[:8] + "..."
    audit_id_short.short_description = 'Audit ID'
    
    def message_preview(self, obj):
        if isinstance(obj.message, dict):
            status = obj.message.get('status', 'unknown')
            response_keys = obj.message.get('response', {}).keys() if obj.message.get('response') else []
            return f"Status: {status} | Keys: {', '.join(list(response_keys)[:3])}"
        return str(obj.message)[:100] + "..." if len(str(obj.message)) > 100 else str(obj.message)
    message_preview.short_description = 'Message Preview'
    
    def has_add_permission(self, request):
        # Audit logs should not be manually created
        return False
    
    def has_change_permission(self, request, obj=None):
        # Audit logs should not be edited
        return False 