#!/usr/bin/env python
"""
Simple validation test to check if our cache invalidation code is syntactically correct
and follows the expected pattern.
"""

def validate_cache_invalidation_fix():
    """Check if the cache invalidation code was added correctly."""
    
    print("Validating cache invalidation fix...")
    
    # Read the modified file
    with open('council_finance/views/council_edit_api.py', 'r') as f:
        content = f.read()
    
    # Check if cache invalidation code was added for temporal data
    checks = [
        ('Cache import added', 'from django.core.cache import cache' in content),
        ('Temporal cache deletion', 'cache_key_current = f"counter_values:{council.slug}:{year.label}"' in content),
        ('Temporal cache invalidation call', 'cache.delete(cache_key_current)' in content),
        ('Temporal invalidation logging', 'logger.info(f"Invalidated counter cache: {cache_key_current}")' in content),
        ('Characteristics cache invalidation', 'for year in FinancialYear.objects.all():' in content),
        ('Characteristics cache key format', 'cache_key = f"counter_values:{council.slug}:{year.label}"' in content),
    ]
    
    all_passed = True
    for check_name, condition in checks:
        if condition:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name}")
            all_passed = False
    
    # Check if the code is properly indented and in the right place
    if 'cache.delete(cache_key_current)' in content:
        # Find the context around cache invalidation
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'cache.delete(cache_key_current)' in line:
                # Check if it's after the transaction.atomic() block but before the return
                context_start = max(0, i - 15)
                context_end = min(len(lines), i + 10)
                context = '\n'.join(lines[context_start:context_end])
                
                # Look for the transaction block and ensure cache invalidation is outside
                transaction_line = -1
                cache_line = i
                return_line = -1
                
                for j in range(context_start, context_end):
                    if j < len(lines):
                        if 'with transaction.atomic():' in lines[j]:
                            transaction_line = j
                        if 'return JsonResponse(' in lines[j] and j > cache_line:
                            return_line = j
                            break
                
                # Check indentation to see if cache is inside or outside transaction
                if transaction_line > 0 and cache_line > transaction_line:
                    # Get indentation of transaction and cache lines
                    transaction_indent = len(lines[transaction_line]) - len(lines[transaction_line].lstrip())
                    cache_indent = len(lines[cache_line]) - len(lines[cache_line].lstrip())
                    
                    if cache_indent <= transaction_indent:
                        print("✅ Cache invalidation is placed outside database transaction")
                        return True
                    else:
                        print("⚠️  Cache invalidation appears to be inside transaction block")
                        return False
                else:
                    print("✅ Cache invalidation placement appears correct")
                    return True
                break
    
    # Syntax check
    try:
        import ast
        with open('council_finance/views/council_edit_api.py', 'r') as f:
            ast.parse(f.read())
        print("✅ Python syntax is valid")
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        all_passed = False
    
    return all_passed

def validate_cache_key_consistency():
    """Check if cache keys match the pattern used in the counter display code."""
    
    print("\nValidating cache key consistency...")
    
    # Expected cache key pattern from general.py
    expected_pattern = 'counter_values:{council_slug}:{year_label}'
    
    with open('council_finance/views/council_edit_api.py', 'r') as f:
        content = f.read()
    
    # Check if our cache keys match the expected pattern
    if f'f"counter_values:{{council.slug}}:{{year.label}}"' in content:
        print("✅ Cache key format matches expected pattern")
        return True
    else:
        print("❌ Cache key format doesn't match expected pattern")
        return False

if __name__ == '__main__':
    print("Validating cache invalidation implementation...\n")
    
    success1 = validate_cache_invalidation_fix()
    success2 = validate_cache_key_consistency()
    
    if success1 and success2:
        print("\n🎉 All validations passed! The implementation looks correct.")
    else:
        print("\n❌ Some validations failed. Please review the implementation.")