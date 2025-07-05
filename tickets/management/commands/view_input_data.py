from django.core.management.base import BaseCommand
from tickets.models import InputNeededChecklist, InputNeededGlossary


class Command(BaseCommand):
    help = 'View loaded input checklist data'

    def handle(self, *args, **options):
        self.stdout.write("=== INPUT NEEDED CHECKLIST DATA ===")
        
        # Get unique themes properly
        themes = list(InputNeededChecklist.objects.values_list('support_theme', flat=True).distinct())
        unique_themes = sorted(set(themes))
        
        self.stdout.write(f"Total unique themes: {len(unique_themes)}")
        self.stdout.write(f"Total checklist items: {InputNeededChecklist.objects.count()}")
        self.stdout.write(f"Total glossary entries: {InputNeededGlossary.objects.count()}")
        
        self.stdout.write("\n=== THEMES AND ITEM COUNTS ===")
        for theme in unique_themes:
            count = InputNeededChecklist.objects.filter(support_theme=theme).count()
            self.stdout.write(f"• {theme}: {count} items")
        
        self.stdout.write("\n=== SAMPLE CHECKLIST ITEMS ===")
        sample_theme = "Work Status Reversion"
        items = InputNeededChecklist.objects.filter(support_theme=sample_theme)[:3]
        if items:
            self.stdout.write(f"Sample items from '{sample_theme}':")
            for item in items:
                self.stdout.write(f"  - {item.input_needed} (Priority: {item.priority})")
        
        self.stdout.write("\n=== ALL CHECKLIST ITEMS BY THEME ===")
        for theme in unique_themes[:2]:  # Show first 2 themes
            self.stdout.write(f"\n{theme}:")
            items = InputNeededChecklist.objects.filter(support_theme=theme)
            for item in items:
                self.stdout.write(f"  - {item.input_needed} (Priority: {item.priority})")
        
        self.stdout.write("\n=== GLOSSARY ENTRIES ===")
        for glossary in InputNeededGlossary.objects.all():
            self.stdout.write(f"• {glossary.support_theme}:")
            self.stdout.write(f"  {glossary.description[:200]}...")
            self.stdout.write("") 