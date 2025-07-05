import pandas as pd
from django.core.management.base import BaseCommand
from tickets.models import InputNeededChecklist, InputNeededGlossary


class Command(BaseCommand):
    help = 'Load input needed checklist data from Excel file into database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='input_needed_checklist.xlsx',
            help='Path to the Excel file (default: input_needed_checklist.xlsx)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before loading'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        
        try:
            # Read the Excel file
            df = pd.read_excel(file_path)
            self.stdout.write(f"Reading Excel file: {file_path}")
            self.stdout.write(f"Excel shape: {df.shape}")
            
            if options['clear']:
                self.stdout.write("Clearing existing data...")
                InputNeededChecklist.objects.all().delete()
                InputNeededGlossary.objects.all().delete()
                self.stdout.write(self.style.SUCCESS("Existing data cleared"))
            
            # Process the data
            checklist_items = []
            glossary_items = {}
            
            # Parse the Excel data structure
            for i, row in df.iterrows():
                row_values = [str(val) if pd.notna(val) else None for val in row.values]
                
                # Skip header rows and empty rows more carefully
                if i < 8:  # Skip first 8 rows (headers)
                    continue
                
                if all(val is None or val == 'nan' for val in row_values):
                    continue
                
                # Column 1: support_theme, Column 2: input_needed, Column 3: priority (left table)
                support_theme_1 = row_values[1]
                input_needed = row_values[2]
                priority_1 = row_values[3]
                
                # Column 7: support_theme, Column 8: description (right table - glossary)
                support_theme_2 = row_values[7]
                description = row_values[8]
                
                # Process checklist items (left table)
                if (support_theme_1 and support_theme_1 != 'nan' and 
                    support_theme_1 != 'support_theme' and  # Skip header
                    input_needed and input_needed != 'nan' and
                    input_needed != 'input_needed'):  # Skip header
                    
                    # Map priority values
                    priority_mapping = {
                        'high': 'high',
                        'medium': 'medium', 
                        'low': 'low',
                        'critical': 'critical'
                    }
                    
                    mapped_priority = priority_mapping.get(priority_1.lower() if priority_1 else 'medium', 'medium')
                    
                    # Check for duplicates before adding
                    item_key = (support_theme_1, input_needed)
                    if not any(item['support_theme'] == support_theme_1 and item['input_needed'] == input_needed 
                              for item in checklist_items):
                        checklist_items.append({
                            'support_theme': support_theme_1,
                            'input_needed': input_needed,
                            'priority': mapped_priority
                        })
                
                # Process glossary items (right table)
                if (support_theme_2 and support_theme_2 != 'nan' and 
                    support_theme_2 != 'support_theme' and  # Skip header
                    description and description != 'nan' and
                    description != 'description'):  # Skip header
                    
                    # Only add if not already in glossary_items
                    if support_theme_2 not in glossary_items:
                        glossary_items[support_theme_2] = description
            
            # Load checklist items
            self.stdout.write(f"Loading {len(checklist_items)} unique checklist items...")
            checklist_created = 0
            for item in checklist_items:
                checklist_obj, created = InputNeededChecklist.objects.get_or_create(
                    support_theme=item['support_theme'],
                    input_needed=item['input_needed'],
                    defaults={'priority': item['priority']}
                )
                if created:
                    checklist_created += 1
            
            # Load glossary items
            self.stdout.write(f"Loading {len(glossary_items)} unique glossary items...")
            glossary_created = 0
            for theme, description in glossary_items.items():
                glossary_obj, created = InputNeededGlossary.objects.get_or_create(
                    support_theme=theme,
                    defaults={'description': description}
                )
                if created:
                    glossary_created += 1
            
            # Summary
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nData loading completed successfully!"
                )
            )
            self.stdout.write(f"✅ Checklist items created: {checklist_created}")
            self.stdout.write(f"✅ Glossary entries created: {glossary_created}")
            
            # Show summary statistics
            total_checklist = InputNeededChecklist.objects.count()
            total_glossary = InputNeededGlossary.objects.count()
            
            self.stdout.write(f"\n📊 Database Summary:")
            self.stdout.write(f"   Total checklist items: {total_checklist}")
            self.stdout.write(f"   Total glossary entries: {total_glossary}")
            
            # Show theme breakdown (unique themes)
            themes = InputNeededChecklist.objects.values_list('support_theme', flat=True).distinct()
            unique_themes = sorted(set(themes))
            self.stdout.write(f"   Unique support themes: {len(unique_themes)}")
            
            for theme in unique_themes:
                count = InputNeededChecklist.objects.filter(support_theme=theme).count()
                self.stdout.write(f"     • {theme}: {count} items")
                
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f"File not found: {file_path}")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error loading data: {str(e)}")
            )
            import traceback
            self.stdout.write(traceback.format_exc()) 