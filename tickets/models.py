from django.db import models
import uuid

class Organization(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=256)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    details = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=128)
    email = models.EmailField(max_length=128, unique=True)
    role = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)
    active = models.BooleanField(default=True)
    suspended = models.BooleanField(default=False)
    timezone = models.CharField(max_length=64, null=True, blank=True)
    phone = models.CharField(max_length=32, null=True, blank=True)

    def __str__(self):
        return self.name

class CompletenessChecklist(models.Model):
    """Model to store support theme checklists for L1 response drafting"""
    support_theme = models.CharField(max_length=128, unique=True, help_text="The support theme/category")
    description = models.TextField(help_text="Description of this support theme")
    priority = models.CharField(max_length=16, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'), 
        ('high', 'High'),
        ('critical', 'Critical')
    ], default='medium')
    
    # Input checklist as JSON array
    input_checklist = models.JSONField(help_text="List of required information/data customer must provide")
    
    # Optional: Common questions to ask
    common_questions = models.JSONField(null=True, blank=True, help_text="Common questions L1 should ask")
    
    # Optional: Expected response template
    response_template = models.TextField(null=True, blank=True, help_text="Template for L1 to draft response")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['support_theme']
    
    def __str__(self):
        return f"{self.support_theme} - {len(self.input_checklist)} items"

class InputNeededChecklist(models.Model):
    """Model to store detailed input requirements for each support theme"""
    support_theme = models.CharField(max_length=128, help_text="The support theme/category")
    input_needed = models.TextField(help_text="Specific input or information required from customer")
    priority = models.CharField(max_length=16, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'), 
        ('high', 'High'),
        ('critical', 'Critical')
    ], help_text="Priority level of this input requirement")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['support_theme', '-priority', 'input_needed']
        indexes = [
            models.Index(fields=['support_theme']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"{self.support_theme}: {self.input_needed[:50]}..."

class InputNeededGlossary(models.Model):
    """Model to store descriptions and definitions of support themes"""
    support_theme = models.CharField(max_length=128, unique=True, help_text="The support theme/category")
    description = models.TextField(help_text="Detailed description of the support theme")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['support_theme']
        verbose_name_plural = "Input Needed Glossaries"
    
    def __str__(self):
        return f"{self.support_theme}: {self.description[:100]}..."

class Ticket(models.Model):
    # Primary key
    id = models.BigAutoField(primary_key=True)
    
    # Core Zendesk fields
    ticket_id = models.BigIntegerField(unique=True, null=True, blank=True)  # Zendesk ticket ID
    zendesk_url = models.URLField(max_length=500, null=True, blank=True)
    external_id = models.CharField(max_length=128, null=True, blank=True)
    via = models.JSONField(null=True, blank=True)  # Channel information as JSON object
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    generated_timestamp = models.BigIntegerField(null=True, blank=True)
    type = models.CharField(max_length=32, null=True, blank=True)
    subject = models.TextField()
    raw_subject = models.TextField(null=True, blank=True)
    description = models.TextField()
    priority = models.CharField(max_length=16)
    status = models.CharField(max_length=32)
    recipient = models.CharField(max_length=256, null=True, blank=True)
    
    # User relationships (using IDs as per schema)
    requester_id = models.BigIntegerField(null=True, blank=True)
    submitter_id = models.BigIntegerField(null=True, blank=True)
    assignee_id = models.BigIntegerField(null=True, blank=True)
    organization_id = models.BigIntegerField(null=True, blank=True)
    group_id = models.BigIntegerField(null=True, blank=True)
    
    # Array fields for multiple IDs (using JSONField for SQLite compatibility)
    collaborator_ids = models.JSONField(null=True, blank=True, default=list)
    follower_ids = models.JSONField(null=True, blank=True, default=list)
    email_cc_ids = models.JSONField(null=True, blank=True, default=list)
    sharing_agreement_ids = models.JSONField(null=True, blank=True, default=list)
    followup_ids = models.JSONField(null=True, blank=True, default=list)
    
    # Additional Zendesk fields
    forum_topic_id = models.BigIntegerField(null=True, blank=True)
    problem_id = models.BigIntegerField(null=True, blank=True)
    has_incidents = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    due_at = models.DateTimeField(null=True, blank=True)
    tags = models.JSONField(null=True, blank=True, default=list)
    satisfaction_rating = models.JSONField(null=True, blank=True)
    custom_status_id = models.BigIntegerField(null=True, blank=True)
    encoded_id = models.CharField(max_length=128, null=True, blank=True)
    ticket_form_id = models.BigIntegerField(null=True, blank=True)
    brand_id = models.BigIntegerField(null=True, blank=True)
    allow_channelback = models.BooleanField(default=True)
    allow_attachments = models.BooleanField(default=True)
    from_messaging_channel = models.BooleanField(default=False)
    source_channel = models.CharField(max_length=64, null=True, blank=True)
    
    # TESSA specific fields
    product = models.CharField(max_length=128, null=True, blank=True)
    support_theme = models.CharField(max_length=128, null=True, blank=True)
    summary = models.TextField(null=True, blank=True)
    severity = models.CharField(max_length=32, null=True, blank=True)
    ticket_type = models.CharField(max_length=64, null=True, blank=True)
    interface_affected = models.CharField(max_length=128, null=True, blank=True)
    code_change = models.CharField(max_length=256, null=True, blank=True)
    module = models.CharField(max_length=128, null=True, blank=True)
    workaround = models.TextField(null=True, blank=True)
    effort_aidash = models.CharField(max_length=64, null=True, blank=True)
    urgency = models.CharField(max_length=32, null=True, blank=True)

    # AI/Agent fields (keeping existing ones)
    sentiment = models.CharField(max_length=16, blank=True, null=True)
    category = models.CharField(max_length=32, blank=True, null=True)
    impact = models.CharField(max_length=32, blank=True, null=True)
    ai_priority = models.CharField(max_length=8, blank=True, null=True)
    next_action = models.CharField(max_length=128, blank=True, null=True)
    escalation = models.CharField(max_length=8, blank=True, null=True)
    resolution = models.TextField(blank=True, null=True)
    troubleshooting_steps = models.TextField(blank=True, null=True)
    counter_questions = models.TextField(blank=True, null=True)
    feedback = models.CharField(max_length=32, blank=True, null=True)
    
    # Completeness tracking
    completeness_score = models.FloatField(null=True, blank=True, help_text="Percentage of required info provided")
    missing_info = models.JSONField(null=True, blank=True, help_text="List of missing information items")
    
    # Pipeline tracking fields
    last_rag_processed = models.DateTimeField(null=True, blank=True, help_text="When RAG pipeline last processed this ticket")
    l1_response_draft = models.TextField(null=True, blank=True, help_text="Generated L1 response draft")
    draft_generated_at = models.DateTimeField(null=True, blank=True, help_text="When L1 draft was generated")

    def get_support_theme_from_tags(self):
        """Extract support theme from tags using predefined mapping"""
        if not self.tags:
            return "general"
        
        # Mapping based on analysis
        theme_mapping = {
            'ivms': 'IVMS',
            'user_mgmt': 'User Management', 
            'login_issues': 'Login Issues',
            'work_status_retention': 'Work Status Issues',
            'system_email_notification_failure': 'Email Notifications',
            'business/product_knowledge': 'Product Knowledge',
            'help_with_data_entries': 'Data Entry',
            'help_with_permissions': 'Permissions',
            'work_mgmt': 'Work Management',
            'cris': 'CRIS System'
        }
        
        for tag in self.tags:
            if tag in theme_mapping:
                return theme_mapping[tag]
        
        # Fallback based on priority tags
        if 'bug' in self.tags:
            return 'Bug Report'
        elif 'blocker' in self.tags:
            return 'System Blocker'
        elif any(tag in ['critical', 'urgent'] for tag in self.tags):
            return 'Critical Issue'
        
        return 'General Support'

    def check_completeness(self):
        """Check ticket completeness against support theme requirements"""
        try:
            theme = self.get_support_theme_from_tags()
            checklist = CompletenessChecklist.objects.get(support_theme=theme)
            
            required_items = checklist.input_checklist
            missing_items = []
            provided_count = 0
            
            # Basic completeness checks
            ticket_data = {
                'description': self.description,
                'subject': self.subject,
                'priority': self.priority,
                'steps_to_reproduce': 'steps' in self.description.lower() or 'reproduce' in self.description.lower(),
                'error_message': 'error' in self.description.lower() or 'exception' in self.description.lower(),
                'browser_info': 'browser' in self.description.lower() or 'chrome' in self.description.lower() or 'firefox' in self.description.lower(),
                'screenshots': 'screenshot' in self.description.lower() or 'image' in self.description.lower(),
                'user_account': '@' in self.description or 'user' in self.description.lower(),
                'environment': 'prod' in self.description.lower() or 'staging' in self.description.lower() or 'test' in self.description.lower()
            }
            
            for item in required_items:
                item_key = item.lower().replace(' ', '_').replace('/', '_')
                if item_key in ticket_data and ticket_data[item_key]:
                    provided_count += 1
                else:
                    missing_items.append(item)
            
            completeness = (provided_count / len(required_items)) * 100 if required_items else 100
            
            self.completeness_score = completeness
            self.missing_info = missing_items
            return completeness, missing_items
            
        except CompletenessChecklist.DoesNotExist:
            return 50.0, ['Support theme checklist not found']

    def __str__(self):
        return f"{self.subject} (ID: {self.id})"

class Comment(models.Model):
    id = models.BigAutoField(primary_key=True)
    ticket = models.ForeignKey(Ticket, related_name="comments", on_delete=models.CASCADE)
    author = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    body = models.TextField()
    public = models.BooleanField(default=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    attachments = models.TextField(null=True, blank=True)  # or use FileField with a file storage setup

    def __str__(self):
        return f"Comment {self.id} on Ticket {self.ticket_id}"

class AuditLog(models.Model):
    """
    Audit log model to track TESSA function invocations and responses
    Table: tessa_audit_logs
    """
    # Primary audit identifier - using UUID as specified in schema
    audit_id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique audit log identifier"
    )
    
    # Function name that was invoked
    function = models.CharField(
        max_length=256,
        help_text="Name of the function invoked"
    )
    
    # Related ticket ID
    ticket_id = models.BigIntegerField(
        help_text="Ticket ID being processed"
    )
    
    # Timestamp of the audit event
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the audit event occurred"
    )
    
    # TESSA response stored as JSON
    message = models.JSONField(
        help_text="TESSA response data"
    )

    class Meta:
        db_table = 'tessa_audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ticket_id']),
            models.Index(fields=['function']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"Audit {self.audit_id} - {self.function} for ticket {self.ticket_id}"
