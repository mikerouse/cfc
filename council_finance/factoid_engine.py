"""
Enhanced Factoid Engine for generating dynamic factoids with rich content
"""
import re
from typing import List, Dict, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime, timezone
from django.db.models import Q, Avg, Count
from django.template import Template, Context
from django.utils.safestring import mark_safe

from .models import (
    FactoidTemplate, FactoidPlaylist, PlaylistItem, 
    CounterDefinition, Council, FinancialYear,
    FinancialFigure, CouncilCharacteristic
)
from .agents.counter_agent import CounterAgent


class FactoidEngine:
    """Advanced factoid generation with multiple data sources and intelligent content"""
    
    def __init__(self):
        self.counter_agent = CounterAgent()
    
    def generate_factoid_playlist(self, counter_slug: str, council_slug: Optional[str], year_label: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Generate comprehensive factoid playlist for a specific context"""
        try:
            counter = CounterDefinition.objects.get(slug=counter_slug)
            council = None
            if council_slug and council_slug != 'all-councils':
                council = Council.objects.get(slug=council_slug)
            year = FinancialYear.objects.get(label=year_label)
        except (CounterDefinition.DoesNotExist, Council.DoesNotExist, FinancialYear.DoesNotExist):
            return []
        
        # Get or create playlist
        playlist, created = FactoidPlaylist.objects.get_or_create(
            counter=counter,
            council=council,
            year=year,
            defaults={'auto_generate': True}
        )
        
        # Check if we need to regenerate
        if created or not playlist.computed_factoids or self._should_regenerate(playlist, force_refresh):
            factoids = self._generate_all_factoids(counter, council, year)
            playlist.computed_factoids = factoids
            playlist.last_computed = datetime.now(timezone.utc)
            playlist.save()
        
        return playlist.computed_factoids
    
    def _should_regenerate(self, playlist: FactoidPlaylist, force_refresh: bool = False) -> bool:
        """Determine if playlist should be regenerated"""
        if not playlist.last_computed or force_refresh:
            return True
        
        # Regenerate if older than 1 hour
        age = datetime.now(timezone.utc) - playlist.last_computed
        return age.total_seconds() > 3600
    
    def _generate_all_factoids(self, counter: CounterDefinition, council: Council, year: FinancialYear) -> List[Dict[str, Any]]:
        """Generate all types of factoids for the given context"""
        factoids = []
        
        # Handle site-wide counters (no specific council)
        if not council:
            return self._generate_site_wide_factoids(counter, year)
        
        # Get counter data
        counter_data = self._get_counter_data(counter, council, year)
        if not counter_data or not counter_data.get('value'):
            return []
        
        # Get previous year data for comparisons
        previous_data = self._get_previous_year_data(counter, council, year)
        
        # Get templates that apply to this counter
        templates = self._get_applicable_templates(counter, council)
        
        # Generate factoids from templates
        for template in templates:
            factoid = self._generate_factoid_from_template(template, counter_data, previous_data, council)
            if factoid and factoid.get('is_relevant', True):
                factoids.append(factoid)
        
        # Generate dynamic factoids
        factoids.extend(self._generate_percentage_change(counter_data, previous_data))
        factoids.extend(self._generate_ranking_factoids(counter_data, counter, council))
        factoids.extend(self._generate_per_capita_factoids(counter_data, council))
        factoids.extend(self._generate_trend_factoids(counter, council, year))
        
        # Sort by priority and relevance
        factoids = self._prioritize_factoids(factoids)
        
        return factoids[:6]  # Limit to top 6 factoids
    
    def _generate_site_wide_factoids(self, counter: CounterDefinition, year: FinancialYear) -> List[Dict[str, Any]]:
        """Generate factoids for site-wide counters (aggregated data across all councils)"""
        factoids = []
        
        try:
            # For site-wide counters, create generic factoids about the data
            counter_name = counter.name.lower()
            
            # Get total councils count for context
            total_councils = Council.objects.filter(status='active').count()
            
            # Generate contextual factoids
            if 'debt' in counter_name:
                factoids.extend([
                    {
                        'type': 'context',
                        'emoji': '🏛️',
                        'color': 'blue',
                        'text': f'Aggregated across **{total_councils}** UK councils',
                        'animation_duration': 7000,
                        'flip_animation': True,
                        'priority': 100,
                        'is_relevant': True
                    },
                    {
                        'type': 'context',
                        'emoji': '📊',
                        'color': 'purple',
                        'text': 'Updated as councils publish annual financial statements',
                        'animation_duration': 8000,
                        'flip_animation': True,
                        'priority': 90,
                        'is_relevant': True
                    },
                    {
                        'type': 'sustainability',
                        'emoji': '⚖️',
                        'color': 'orange',
                        'text': 'Financial sustainability varies significantly between councils',
                        'animation_duration': 9000,
                        'flip_animation': True,
                        'priority': 80,
                        'is_relevant': True
                    }
                ])
            elif 'revenue' in counter_name or 'income' in counter_name:
                factoids.extend([
                    {
                        'type': 'context',
                        'emoji': '💰',
                        'color': 'green',
                        'text': f'Combined revenue from **{total_councils}** councils',
                        'animation_duration': 7000,
                        'flip_animation': True,
                        'priority': 100,
                        'is_relevant': True
                    },
                    {
                        'type': 'context',
                        'emoji': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
                        'color': 'blue',
                        'text': 'Includes England, Scotland, Wales and Northern Ireland',
                        'animation_duration': 8000,
                        'flip_animation': True,
                        'priority': 90,
                        'is_relevant': True
                    }
                ])
            else:
                # Generic factoids
                factoids.extend([
                    {
                        'type': 'context',
                        'emoji': '📈',
                        'color': 'blue',
                        'text': f'UK-wide data from **{total_councils}** local councils',
                        'animation_duration': 7000,
                        'flip_animation': True,
                        'priority': 100,
                        'is_relevant': True
                    },
                    {
                        'type': 'context',
                        'emoji': '🔍',
                        'color': 'purple',
                        'text': 'Browse individual councils for detailed breakdowns',
                        'animation_duration': 8000,
                        'flip_animation': True,
                        'priority': 90,
                        'is_relevant': True
                    }
                ])
            
            # Add year context
            factoids.append({
                'type': 'context',
                'emoji': '📅',
                'color': 'gray',
                'text': f'Financial year **{year.label}** data',
                'animation_duration': 6000,
                'flip_animation': True,
                'priority': 70,
                'is_relevant': True
            })
            
        except Exception as e:
            # Fallback factoid
            factoids = [{
                'type': 'context',
                'emoji': '📊',
                'color': 'blue',
                'text': 'UK council financial transparency data',
                'animation_duration': 6000,
                'flip_animation': True,
                'priority': 50,
                'is_relevant': True
            }]
        
        return factoids[:4]  # Limit site-wide factoids
    
    def _get_counter_data(self, counter: CounterDefinition, council: Council, year: FinancialYear) -> Dict[str, Any]:
        """Get counter data for the specified context"""
        try:
            results = self.counter_agent.run(council_slug=council.slug, year_label=year.label)
            counter_result = results.get(counter.slug, {})
            
            if isinstance(counter_result, dict):
                return {
                    'value': counter_result.get('value'),
                    'formatted': counter_result.get('formatted', 'No data'),
                    'counter_slug': counter.slug,
                    'counter_name': counter.name,
                    'council_name': council.name,
                    'council_population': getattr(council, 'latest_population', None),
                    'year_label': year.label
                }
            else:
                return {
                    'value': counter_result,
                    'formatted': str(counter_result) if counter_result is not None else 'No data',
                    'counter_slug': counter.slug,
                    'counter_name': counter.name,
                    'council_name': council.name,
                    'council_population': getattr(council, 'latest_population', None),
                    'year_label': year.label
                }
        except Exception as e:
            return {}
    
    def _get_previous_year_data(self, counter: CounterDefinition, council: Council, year: FinancialYear) -> Optional[Dict[str, Any]]:
        """Get counter data for the previous year"""
        try:
            # Simple year calculation - this could be enhanced
            current_year_num = int(year.label.split('/')[0])
            previous_year_label = f"{current_year_num-1}/{str(current_year_num)[-2:]}"
            
            previous_year = FinancialYear.objects.filter(label=previous_year_label).first()
            if not previous_year:
                return None
            
            return self._get_counter_data(counter, council, previous_year)
        except (ValueError, AttributeError):
            return None
    
    def _get_applicable_templates(self, counter: CounterDefinition, council: Council) -> List[FactoidTemplate]:
        """Get factoid templates that apply to this counter/council combination"""
        templates = FactoidTemplate.objects.filter(
            is_active=True,
            counters=counter
        ).prefetch_related('council_types')
        
        # Filter by council type if specified
        if council.council_type:
            templates = templates.filter(
                Q(council_types__isnull=True) | Q(council_types=council.council_type)
            )
        
        return templates.order_by('-priority', 'name')
    
    def _generate_factoid_from_template(self, template: FactoidTemplate, counter_data: Dict, previous_data: Optional[Dict], council: Council) -> Optional[Dict[str, Any]]:
        """Generate a factoid from a template with dynamic data"""
        try:
            # Prepare template context
            context_data = counter_data.copy()
            if previous_data:
                context_data['previous_value'] = previous_data.get('value')
                context_data['previous_formatted'] = previous_data.get('formatted')
            
            # Add calculated fields
            if previous_data and counter_data.get('value') and previous_data.get('value'):
                try:
                    current = float(counter_data['value'])
                    previous = float(previous_data['value'])
                    if previous != 0:
                        change = ((current - previous) / previous) * 100
                        context_data['change'] = f"{change:+.1f}"
                        context_data['change_abs'] = f"{abs(change):.1f}"
                        context_data['change_direction'] = "increase" if change > 0 else "decrease"
                except (ValueError, TypeError):
                    pass
            
            # Check template conditions
            if not self._meets_template_conditions(template, counter_data):
                return None
            
            # Render template text
            django_template = Template(template.template_text)
            rendered_text = django_template.render(Context(context_data))
            
            return {
                'type': template.factoid_type,
                'text': rendered_text,
                'emoji': template.emoji or self._get_default_emoji(template.factoid_type),
                'color': template.color_scheme,
                'animation_duration': template.animation_duration,
                'flip_animation': template.flip_animation,
                'priority': template.priority,
                'template_id': template.id,
                'is_relevant': True
            }
        except Exception as e:
            return None
    
    def _meets_template_conditions(self, template: FactoidTemplate, counter_data: Dict) -> bool:
        """Check if counter data meets template display conditions"""
        value = counter_data.get('value')
        if value is None:
            return False
        
        try:
            value = float(value)
            
            if template.min_value is not None and value < float(template.min_value):
                return False
            
            if template.max_value is not None and value > float(template.max_value):
                return False
            
            return True
        except (ValueError, TypeError):
            return False
    
    def _generate_percentage_change(self, current: Dict, previous: Optional[Dict]) -> List[Dict[str, Any]]:
        """Generate percentage change factoids"""
        if not previous or not current.get('value') or not previous.get('value'):
            return []
        
        try:
            current_val = float(current['value'])
            previous_val = float(previous['value'])
            
            if previous_val == 0:
                return []
            
            change = ((current_val - previous_val) / previous_val) * 100
            
            
            if abs(change) < 1:  # Skip insignificant changes
                return []
            
            emoji = "📈" if change > 0 else "📉"
            color = "green" if change > 0 else "red"
            direction = "increase" if change > 0 else "decrease"
            
            return [{
                'type': 'percent_change',
                'emoji': emoji,
                'color': color,
                'text': f"**{abs(change):.1f}%** {direction} vs last year",
                'animation_duration': 6000,
                'flip_animation': True,
                'priority': 100,
                'is_relevant': True
            }]
        except (ValueError, TypeError):
            return []
    
    def _generate_ranking_factoids(self, counter_data: Dict, counter: CounterDefinition, council: Council) -> List[Dict[str, Any]]:
        """Generate ranking-based factoids"""
        try:
            # Get all councils with data for this counter
            year_label = counter_data.get('year_label')
            if not year_label:
                return []
            
            # This is a simplified version - in production you'd want to run the counter agent
            # for all councils and rank them properly
            ranking_data = self._calculate_simple_ranking(counter, council, year_label)
            
            if not ranking_data:
                return []
            
            position = ranking_data['position']
            total = ranking_data['total']
            
            if position <= 3:
                emojis = ["🥇", "🥈", "🥉"]
                emoji = emojis[position - 1]
                color = "green"
            elif position >= total - 2:
                emoji = "🔻"
                color = "red"
            else:
                emoji = "📊"
                color = "blue"
            
            ordinal = self._get_ordinal_number(position)
            
            return [{
                'type': 'ranking',
                'emoji': emoji,
                'color': color,
                'text': f"Ranks **{ordinal}** out of {total} councils",
                'animation_duration': 5000,
                'flip_animation': True,
                'priority': 90,
                'is_relevant': True
            }]
        except Exception:
            return []
    
    def _generate_per_capita_factoids(self, counter_data: Dict, council: Council) -> List[Dict[str, Any]]:
        """Generate per-capita insights"""
        if not counter_data.get('value') or not council.latest_population:
            return []
        
        try:
            value = float(counter_data['value'])
            population = council.latest_population
            per_capita = value / population
            
            # Format appropriately based on magnitude
            if per_capita >= 1000:
                formatted = f"£{per_capita:,.0f}"
            elif per_capita >= 100:
                formatted = f"£{per_capita:.0f}"
            else:
                formatted = f"£{per_capita:.2f}"
            
            return [{
                'type': 'per_capita',
                'emoji': '👤',
                'color': 'purple',
                'text': f"**{formatted}** per resident",
                'animation_duration': 7000,
                'flip_animation': True,
                'priority': 80,
                'is_relevant': True
            }]
        except (ValueError, TypeError):
            return []
    
    def _generate_trend_factoids(self, counter: CounterDefinition, council: Council, year: FinancialYear) -> List[Dict[str, Any]]:
        """Generate multi-year trend factoids"""
        # This is a placeholder for trend analysis
        # In a full implementation, you'd analyze multiple years of data
        return []
    
    def _calculate_simple_ranking(self, counter: CounterDefinition, council: Council, year_label: str) -> Optional[Dict[str, Any]]:
        """Calculate a simple ranking (placeholder implementation)"""
        # This is a simplified version for demonstration
        # In production, you'd run the counter agent for all councils and rank them
        return {
            'position': 5,  # Placeholder
            'total': 20     # Placeholder
        }
    
    def _get_ordinal_number(self, n: int) -> str:
        """Convert number to ordinal (1st, 2nd, 3rd, etc.)"""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"
    
    def _get_default_emoji(self, factoid_type: str) -> str:
        """Get default emoji for factoid type"""
        default_emojis = {
            'percent_change': '📊',
            'ranking': '🏆',
            'comparison': '⚖️',
            'trend': '📈',
            'ratio': '🔢',
            'per_capita': '👤',
            'sustainability': '🌱',
            'milestone': '🎯',
            'anomaly': '⚠️',
            'context': '📋',
        }
        return default_emojis.get(factoid_type, '💡')
    
    def _prioritize_factoids(self, factoids: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort factoids by priority and relevance"""
        return sorted(factoids, key=lambda x: (-x.get('priority', 0), -len(x.get('text', ''))))