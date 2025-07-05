from django.shortcuts import render
from tickets.models import Ticket, CompletenessChecklist, InputNeededChecklist, InputNeededGlossary

def dashboard_home(request):
    tickets = Ticket.objects.all().order_by("-created_at")[:50]
    return render(request, "dashboard/dashboard.html", {"tickets": tickets})

def ticket_detail(request, ticket_id):
    ticket = Ticket.objects.get(id=ticket_id)
    return render(request, "dashboard/ticket_detail.html", {"ticket": ticket})

def welcome_screen(request):
    return render(request, "dashboard/welcome.html", {"message": "Welcome to TESSA"})

def welcome(request):
    return render(request, 'welcome.html')

def upload_dataset(request):
    """View to upload a new dataset"""
    if request.method == "POST":
        # Handle file upload here
        pass
    return render(request, "upload_dataset.html", {})

def completeness_checker(request):
    """View to display support theme checklists for L1 agents"""
    checklists = CompletenessChecklist.objects.all().order_by('priority', 'support_theme')
    
    # Group by priority for better organization
    priority_groups = {}
    for checklist in checklists:
        priority = checklist.get_priority_display()
        if priority not in priority_groups:
            priority_groups[priority] = []
        priority_groups[priority].append(checklist)
    
    context = {
        'checklists': checklists,
        'priority_groups': priority_groups,
        'total_themes': checklists.count()
    }
    
    return render(request, 'completeness_checker.html', context)

def input_checklist_viewer(request):
    """View to display detailed input checklist data from Excel"""
    # Get all themes and their items
    themes = InputNeededChecklist.objects.values_list('support_theme', flat=True).distinct()
    unique_themes = sorted(set(themes))
    
    # Organize data by theme
    theme_data = []
    for theme in unique_themes:
        items = InputNeededChecklist.objects.filter(support_theme=theme).order_by('-priority', 'input_needed')
        
        # Get glossary description
        try:
            glossary = InputNeededGlossary.objects.get(support_theme=theme)
            description = glossary.description
        except InputNeededGlossary.DoesNotExist:
            description = "No description available"
        
        # Group items by priority
        priority_groups = {}
        for item in items:
            priority = item.get_priority_display()
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(item)
        
        theme_data.append({
            'theme': theme,
            'description': description,
            'items': items,
            'priority_groups': priority_groups,
            'total_items': items.count()
        })
    
    context = {
        'theme_data': theme_data,
        'total_themes': len(unique_themes),
        'total_items': InputNeededChecklist.objects.count(),
        'total_glossary': InputNeededGlossary.objects.count()
    }
    
    return render(request, 'input_checklist_viewer.html', context)
