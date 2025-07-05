from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count, Q
from .models import Ticket, InputNeededChecklist, InputNeededGlossary


def ticket_detail(request, ticket_id):
    """
    Display detailed view of a specific ticket
    """
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Get completeness information if available
    completeness_score = ticket.completeness_score
    missing_items = ticket.missing_info or []
    
    context = {
        'ticket': ticket,
        'completeness_score': completeness_score,
        'missing_items': missing_items,
        'has_l1_draft': bool(ticket.l1_response_draft),
    }
    
    return render(request, 'tickets/ticket_detail.html', context)


def input_checklist_viewer(request):
    """
    Display the input checklist data loaded from Excel
    """
    # Get search query
    search_query = request.GET.get('search', '')
    theme_filter = request.GET.get('theme', '')
    priority_filter = request.GET.get('priority', '')
    
    # Base queryset
    checklists = InputNeededChecklist.objects.all()
    
    # Apply filters
    if search_query:
        checklists = checklists.filter(
            Q(support_theme__icontains=search_query) |
            Q(input_needed__icontains=search_query)
        )
    
    if theme_filter:
        checklists = checklists.filter(support_theme=theme_filter)
    
    if priority_filter:
        checklists = checklists.filter(priority=priority_filter)
    
    # Group by support theme
    themes_data = {}
    for checklist in checklists.order_by('support_theme', '-priority', 'input_needed'):
        theme = checklist.support_theme
        if theme not in themes_data:
            themes_data[theme] = {
                'name': theme,
                'items': [],
                'total_items': 0,
                'priority_counts': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
            }
        
        themes_data[theme]['items'].append(checklist)
        themes_data[theme]['total_items'] += 1
        themes_data[theme]['priority_counts'][checklist.priority] += 1
    
    # Get glossary entries
    glossary = InputNeededGlossary.objects.all().order_by('support_theme')
    
    # Get filter options
    all_themes = InputNeededChecklist.objects.values_list('support_theme', flat=True).distinct()
    all_priorities = ['low', 'medium', 'high', 'critical']
    
    context = {
        'themes_data': themes_data,
        'glossary': glossary,
        'search_query': search_query,
        'theme_filter': theme_filter,
        'priority_filter': priority_filter,
        'all_themes': sorted(all_themes),
        'all_priorities': all_priorities,
        'total_themes': len(themes_data),
        'total_items': sum(theme['total_items'] for theme in themes_data.values())
    }
    
    return render(request, 'tickets/input_checklist.html', context) 