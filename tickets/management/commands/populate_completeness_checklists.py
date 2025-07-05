from django.core.management.base import BaseCommand
from tickets.models import CompletenessChecklist


class Command(BaseCommand):
    help = 'Populate CompletenessChecklist with support themes and required information checklists'

    def handle(self, *args, **options):
        self.stdout.write("Populating completeness checklists...")
        
        checklists = [
            {
                'support_theme': 'IVMS',
                'description': 'Issues related to IVMS (Intelligent Vegetation Management System)',
                'priority': 'high',
                'input_checklist': [
                    'Specific IVMS module affected (Work Management, Property Layer, etc.)',
                    'User account/email experiencing the issue',
                    'Browser type and version',
                    'Steps to reproduce the issue',
                    'Error message or unexpected behavior description',
                    'Screenshots or screen recordings',
                    'Date and time when issue occurred',
                    'Environment (Production/UAT/Test)',
                    'Work order ID or property ID (if applicable)',
                    'Geographic region/utility company'
                ],
                'common_questions': [
                    'Which specific IVMS feature were you using?',
                    'Can you provide the exact error message?',
                    'Does this happen consistently or intermittently?',
                    'Are other team members experiencing the same issue?',
                    'What browser are you using?',
                    'Can you share a screenshot of the problem?'
                ],
                'response_template': '''Thank you for contacting AiDASH support regarding the IVMS issue.

To help us resolve this quickly, could you please provide:

{missing_items}

This information will allow our technical team to investigate and provide a targeted solution.

Best regards,
AiDASH Support Team'''
            },
            {
                'support_theme': 'User Management',
                'description': 'User account creation, permissions, access issues',
                'priority': 'medium',
                'input_checklist': [
                    'User email address',
                    'Full name of user',
                    'Role/permissions required',
                    'Organization/utility company',
                    'Manager or approver contact',
                    'Specific access requirements',
                    'Urgency level and business justification',
                    'Existing user account (if modification)',
                    'Geographic region or territory'
                ],
                'common_questions': [
                    'What level of access does this user need?',
                    'Which utility company/organization do they belong to?',
                    'Who is their manager or can approve this request?',
                    'Is this a new user or modification of existing account?',
                    'What specific features do they need access to?'
                ],
                'response_template': '''Thank you for your user management request.

To process this request, we need the following information:

{missing_items}

Once we have this information, we can typically process user access requests within 1-2 business days.

Best regards,
AiDASH Support Team'''
            },
            {
                'support_theme': 'Login Issues',
                'description': 'Authentication problems, password resets, account lockouts',
                'priority': 'high',
                'input_checklist': [
                    'User email address',
                    'Error message received',
                    'Browser type and version',
                    'Time of login attempt',
                    'Whether password was recently changed',
                    'Multi-factor authentication status',
                    'Network/VPN information',
                    'Previous successful login date',
                    'Device type (desktop/mobile/tablet)'
                ],
                'common_questions': [
                    'What error message do you see when trying to log in?',
                    'When was the last time you successfully logged in?',
                    'Are you using a VPN or corporate network?',
                    'Have you recently changed your password?',
                    'Are you receiving any authentication codes?'
                ],
                'response_template': '''Thank you for reporting the login issue.

To help resolve your access problem, please provide:

{missing_items}

We understand login issues are urgent and will prioritize your request.

Best regards,
AiDASH Support Team'''
            },
            {
                'support_theme': 'Work Status Issues',
                'description': 'Problems with work order status, retention, updates',
                'priority': 'high',
                'input_checklist': [
                    'Work order ID(s) affected',
                    'Expected vs actual work status',
                    'Date/time when status issue occurred',
                    'User account who performed the work',
                    'Geographic location/region',
                    'Screenshots of status discrepancy',
                    'Business impact description',
                    'Utility company/organization',
                    'Any recent system changes or updates'
                ],
                'common_questions': [
                    'What specific work order IDs are affected?',
                    'What status should the work be showing?',
                    'When did you first notice this status issue?',
                    'How many work orders are impacted?',
                    'Is this affecting reporting or billing?'
                ],
                'response_template': '''Thank you for reporting the work status issue.

To investigate this problem thoroughly, we need:

{missing_items}

Work status issues can impact operations, so we'll treat this as a priority.

Best regards,
AiDASH Support Team'''
            },
            {
                'support_theme': 'Bug Report',
                'description': 'Software bugs, system errors, unexpected behavior',
                'priority': 'medium',
                'input_checklist': [
                    'Detailed description of the bug',
                    'Steps to reproduce consistently',
                    'Expected behavior vs actual behavior',
                    'Screenshots or video recording',
                    'Browser/device information',
                    'User account experiencing the issue',
                    'Frequency of occurrence',
                    'Workaround (if any found)',
                    'Environment where bug occurs',
                    'Related error logs or messages'
                ],
                'common_questions': [
                    'Can you consistently reproduce this bug?',
                    'What should happen instead of what you\'re seeing?',
                    'Does this happen for other users too?',
                    'Have you found any workaround?',
                    'When did this bug first appear?'
                ],
                'response_template': '''Thank you for the detailed bug report.

To help our development team investigate and fix this issue, please provide:

{missing_items}

We will log this in our development queue and provide updates on the fix timeline.

Best regards,
AiDASH Support Team'''
            },
            {
                'support_theme': 'System Blocker',
                'description': 'Critical issues blocking normal system operation',
                'priority': 'critical',
                'input_checklist': [
                    'Detailed description of the blocking issue',
                    'Number of users affected',
                    'Business impact assessment',
                    'Error messages or system responses',
                    'Time when blocking started',
                    'Critical deadlines being affected',
                    'Workaround attempts made',
                    'Contact information for urgent updates',
                    'System/module that is blocked',
                    'Geographic scope of impact'
                ],
                'common_questions': [
                    'How many users are unable to work due to this issue?',
                    'What critical business processes are impacted?',
                    'Is this a complete system outage or partial functionality?',
                    'What is your immediate business deadline?',
                    'Who should we contact for urgent updates?'
                ],
                'response_template': '''Thank you for reporting this critical system blocker.

This has been escalated to our highest priority. To ensure rapid resolution, please confirm:

{missing_items}

Our technical team is immediately investigating. We will provide updates every hour until resolved.

Emergency Contact: [Support Manager Contact]

Best regards,
AiDASH Critical Support Team'''
            },
            {
                'support_theme': 'Email Notifications',
                'description': 'Issues with system email notifications and alerts',
                'priority': 'medium',
                'input_checklist': [
                    'Type of email notification missing',
                    'Expected recipients email addresses',
                    'Date/time when notification should have been sent',
                    'Trigger event for the notification',
                    'Email server/domain information',
                    'Spam/junk folder check confirmation',
                    'Other users experiencing same issue',
                    'Recent email system changes',
                    'Business process dependent on notifications'
                ],
                'common_questions': [
                    'What type of notifications are you not receiving?',
                    'Have you checked your spam/junk folders?',
                    'Are other team members receiving these notifications?',
                    'When did you last receive this type of notification?',
                    'Is your email address current in the system?'
                ],
                'response_template': '''Thank you for reporting the email notification issue.

To diagnose the notification delivery problem, we need:

{missing_items}

We will check our email logs and notification queue to identify the issue.

Best regards,
AiDASH Support Team'''
            },
            {
                'support_theme': 'Data Entry',
                'description': 'Help with data entry procedures and requirements',
                'priority': 'low',
                'input_checklist': [
                    'Specific data entry form or module',
                    'Type of data being entered',
                    'Required data format or structure',
                    'Source of data (spreadsheet, manual, etc.)',
                    'Volume of data to be entered',
                    'Data validation requirements',
                    'Deadline for data entry completion',
                    'User role and permissions',
                    'Training documentation already reviewed'
                ],
                'common_questions': [
                    'What specific data are you trying to enter?',
                    'Do you have the data in a spreadsheet format?',
                    'Are there validation errors you\'re encountering?',
                    'Have you reviewed the data entry guidelines?',
                    'Would bulk import be more suitable?'
                ],
                'response_template': '''Thank you for your data entry assistance request.

To provide the most helpful guidance, please share:

{missing_items}

We can provide step-by-step instructions or training materials once we understand your specific needs.

Best regards,
AiDASH Support Team'''
            },
            {
                'support_theme': 'Permissions',
                'description': 'Access permissions and authorization issues',
                'priority': 'medium',
                'input_checklist': [
                    'User account requesting access',
                    'Specific feature or module needing access',
                    'Current permission level',
                    'Required permission level',
                    'Business justification for access',
                    'Manager approval or authorization',
                    'Role-based access requirements',
                    'Temporary or permanent access needed',
                    'Similar users with correct access (for reference)'
                ],
                'common_questions': [
                    'What specific feature can\'t you access?',
                    'What error message do you see when trying to access it?',
                    'Who has approved this access request?',
                    'Do other users in your role have this access?',
                    'Is this for temporary or ongoing access?'
                ],
                'response_template': '''Thank you for your permissions request.

To process your access requirements, we need:

{missing_items}

Permission changes require proper authorization and typically take 1-2 business days to implement.

Best regards,
AiDASH Support Team'''
            },
            {
                'support_theme': 'General Support',
                'description': 'General inquiries and support requests',
                'priority': 'low',
                'input_checklist': [
                    'Detailed description of question or request',
                    'Relevant system or module',
                    'User account or contact information',
                    'Urgency level and deadline',
                    'Previous research or documentation reviewed',
                    'Specific outcome desired',
                    'Business context or use case'
                ],
                'common_questions': [
                    'Can you provide more details about your request?',
                    'What specific outcome are you looking for?',
                    'Have you checked our documentation or FAQ?',
                    'Is this time-sensitive?',
                    'Would a phone call be helpful to discuss this?'
                ],
                'response_template': '''Thank you for contacting AiDASH support.

To provide you with the best assistance, please provide:

{missing_items}

We appreciate your patience and will respond with helpful information soon.

Best regards,
AiDASH Support Team'''
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for checklist_data in checklists:
            checklist, created = CompletenessChecklist.objects.get_or_create(
                support_theme=checklist_data['support_theme'],
                defaults=checklist_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created checklist for: {checklist_data['support_theme']}")
                )
            else:
                # Update existing checklist
                for key, value in checklist_data.items():
                    if key != 'support_theme':
                        setattr(checklist, key, value)
                checklist.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f"Updated checklist for: {checklist_data['support_theme']}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Completeness checklists populated: {created_count} created, {updated_count} updated"
            )
        ) 