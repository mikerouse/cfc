"""
Year-specific population utilities for accurate per capita calculations.
"""

from council_finance.models import DataField, FinancialFigure


def get_population_for_year(council, year):
    """
    Get population for a specific financial year.
    
    This function retrieves the population that should be used for per capita
    calculations for a given year. It prioritizes year-specific population data
    and falls back to the council's latest_population if no year-specific data exists.
    
    Args:
        council: Council instance
        year: FinancialYear instance
        
    Returns:
        int: Population for the specified year
        
    Example:
        >>> pop_2023 = get_population_for_year(council, year_2023)
        >>> debt_per_capita = total_debt / pop_2023
    """
    if not council or not year:
        return 0
    
    try:
        # Get the population DataField
        pop_field = DataField.objects.get(slug='population')
        
        # Try to find year-specific population
        fig = FinancialFigure.objects.filter(
            council=council,
            year=year,
            field=pop_field
        ).first()
        
        if fig and fig.value:
            try:
                # Convert to integer, handling comma-separated values
                clean_value = fig.value.replace(',', '').strip()
                return int(float(clean_value))
            except (ValueError, AttributeError):
                # If conversion fails, fall back to latest_population
                pass
    
    except DataField.DoesNotExist:
        # Population field doesn't exist, use fallback
        pass
    
    # Fall back to latest_population
    return council.latest_population or 0


def set_population_for_year(council, year, population):
    """
    Set population for a specific financial year.
    
    This creates or updates the FinancialFigure record for population
    for the given council and year.
    
    Args:
        council: Council instance
        year: FinancialYear instance
        population: Population value (int or str)
        
    Returns:
        FinancialFigure: The created or updated figure
        
    Raises:
        ValueError: If population is not a valid number
    """
    if not council or not year:
        raise ValueError("Council and year are required")
    
    # Validate population
    try:
        if isinstance(population, str):
            population = population.replace(',', '').strip()
        pop_value = int(float(population))
        if pop_value < 0:
            raise ValueError("Population cannot be negative")
    except (ValueError, TypeError):
        raise ValueError(f"Invalid population value: {population}")
    
    # Get or create population field
    pop_field, _ = DataField.objects.get_or_create(
        slug='population',
        defaults={
            'name': 'Population',
            'content_type': 'integer',
            'category': 'characteristic',
            'description': 'Number of residents in the council area'
        }
    )
    
    # Create or update the figure
    fig, created = FinancialFigure.objects.update_or_create(
        council=council,
        year=year,
        field=pop_field,
        defaults={'value': str(pop_value)}
    )
    
    return fig


def copy_latest_to_year(council, year):
    """
    Copy the council's latest_population to a specific year.
    
    This is useful for initializing historical data when no
    year-specific population exists.
    
    Args:
        council: Council instance
        year: FinancialYear instance
        
    Returns:
        FinancialFigure or None: The created figure, or None if no latest_population
    """
    if not council.latest_population:
        return None
    
    return set_population_for_year(council, year, council.latest_population)


def get_population_history(council, limit=5):
    """
    Get population history for a council across multiple years.
    
    Args:
        council: Council instance
        limit: Maximum number of years to return
        
    Returns:
        list: List of dicts with year and population data
        
    Example:
        >>> history = get_population_history(council)
        >>> [{'year': '2024/25', 'population': 105000}, ...]
    """
    try:
        pop_field = DataField.objects.get(slug='population')
        
        figures = FinancialFigure.objects.filter(
            council=council,
            field=pop_field,
            value__isnull=False
        ).select_related('year').order_by('-year__start_date')[:limit]
        
        history = []
        for fig in figures:
            try:
                pop = int(fig.value.replace(',', ''))
                history.append({
                    'year': fig.year.label,
                    'year_id': fig.year.id,
                    'population': pop,
                    'formatted': f"{pop:,}"
                })
            except (ValueError, AttributeError):
                continue
        
        return history
        
    except DataField.DoesNotExist:
        return []


def calculate_population_change(council, from_year, to_year):
    """
    Calculate population change between two years.
    
    Args:
        council: Council instance
        from_year: FinancialYear instance (earlier year)
        to_year: FinancialYear instance (later year)
        
    Returns:
        dict: Population change data
        
    Example:
        >>> change = calculate_population_change(council, year_2023, year_2024)
        >>> {'from': 95000, 'to': 100000, 'change': 5000, 'percent': 5.26}
    """
    pop_from = get_population_for_year(council, from_year)
    pop_to = get_population_for_year(council, to_year)
    
    if not pop_from or not pop_to:
        return None
    
    change = pop_to - pop_from
    percent_change = (change / pop_from) * 100 if pop_from > 0 else 0
    
    return {
        'from': pop_from,
        'to': pop_to,
        'change': change,
        'percent': round(percent_change, 2),
        'from_formatted': f"{pop_from:,}",
        'to_formatted': f"{pop_to:,}",
        'change_formatted': f"{abs(change):,}",
        'direction': 'increase' if change > 0 else 'decrease' if change < 0 else 'unchanged'
    }