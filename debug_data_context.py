#!/usr/bin/env python3
"""
Debug script for data context mapping
"""
import os
import sys
import django

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'council_finance.settings')
django.setup()

def debug_data_context():
    """Debug the data context for Worcestershire"""
    
    from council_finance.calculators import get_data_context_for_council
    from council_finance.models import Council, FinancialYear
    
    print("🔍 Debugging Data Context for Worcestershire")
    print("=" * 50)
    
    try:
        council = Council.objects.get(slug='worcestershire')
        year = FinancialYear.objects.get(label='2024/25')
        
        print(f"Council: {council.name}")
        print(f"Year: {year.label}")
        
        # Get data context
        data_context = get_data_context_for_council(council, year=year)
        
        print("\n📊 Data Context Contents:")
        print("-" * 30)
        
        for category, data in data_context.items():
            if isinstance(data, dict):
                print(f"\n{category.upper()}:")
                for key, value in data.items():
                    print(f"  {key}: {value}")
            else:
                print(f"{category}: {data}")
                
        # Check what would go into figure_map
        print("\n🗺️  Figure Map Simulation:")
        print("-" * 30)
        
        figure_map = {}
        missing = set()
        
        # 1. Financial data
        financial_data = data_context.get('financial', {})
        for field_slug, value in financial_data.items():
            if value is not None:
                try:
                    figure_map[field_slug] = float(value)
                    print(f"  ✅ {field_slug}: {value}")
                except (TypeError, ValueError) as e:
                    print(f"  ❌ {field_slug}: {value} (conversion error: {e})")
                    missing.add(field_slug)
            else:
                print(f"  ❌ {field_slug}: None (missing)")
                missing.add(field_slug)
        
        # 2. Characteristics
        characteristics = data_context.get('characteristics', {})
        for field_slug, value in characteristics.items():
            if value is not None:
                try:
                    if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit()):
                        figure_map[field_slug] = float(value)
                        print(f"  ✅ {field_slug}: {value} (numeric characteristic)")
                    else:
                        figure_map[field_slug] = value
                        print(f"  ℹ️ {field_slug}: {value} (text characteristic)")
                except (TypeError, ValueError):
                    print(f"  ❌ {field_slug}: {value} (non-numeric)")
                    missing.add(field_slug)
            else:
                print(f"  ❌ {field_slug}: None (missing)")
                missing.add(field_slug)
                
        # 3. Calculated fields
        calculated = data_context.get('calculated', {})
        for field_slug, value in calculated.items():
            if value is not None:
                try:
                    figure_map[field_slug] = float(value)
                    print(f"  ✅ {field_slug}: {value} (calculated)")
                except (TypeError, ValueError) as e:
                    print(f"  ❌ {field_slug}: {value} (conversion error: {e})")
                    missing.add(field_slug)
            else:
                print(f"  ❌ {field_slug}: None (missing)")
                missing.add(field_slug)
                
        print(f"\n📈 Summary:")
        print(f"  Total fields in figure_map: {len(figure_map)}")
        print(f"  Missing fields: {len(missing)}")
        
        # Test FormulaEvaluator
        print(f"\n🧮 Testing FormulaEvaluator:")
        print("-" * 30)
        
        from council_finance.calculators import FormulaEvaluator
        evaluator = FormulaEvaluator()
        evaluator.set_variables(figure_map)
        
        test_formulas = [
            'population',
            'non-ring-fenced-government-grants-income',
            'non_ring_fenced_government_grants_income',
            'non-ring-fenced-government-grants-income / population'
        ]
        
        for formula in test_formulas:
            try:
                result = evaluator.evaluate(formula)
                print(f"  ✅ '{formula}' = {result}")
            except Exception as e:
                print(f"  ❌ '{formula}' failed: {e}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_data_context()
