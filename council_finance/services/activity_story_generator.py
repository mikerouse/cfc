"""
Activity Story Generator
Generates human-readable stories for activity log entries using AI factoid patterns
"""
import json
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List
from django.utils import timezone
from django.db.models import Q

from ..models.new_data_model import FinancialFigure, CouncilCharacteristic
from ..models.field import DataField
from ..models.council import Council, FinancialYear
from ..services.factoid_engine import FactoidEngine

logger = logging.getLogger(__name__)


class ActivityStoryGenerator:
    """
    Generates story-style descriptions for activity log entries
    """
    
    def __init__(self):
        self.factoid_engine = FactoidEngine()
    
    def generate_story(self, activity_log) -> Dict[str, Any]:
        """
        Generate a story-style description for an activity log entry
        """
        try:
            # Parse the activity details
            details = self._parse_activity_details(activity_log.details)
            
            if not details:
                return self._fallback_story(activity_log)
            
            # Generate story based on activity type and field
            if activity_log.activity_type in ['create', 'update'] and 'field_name' in details:
                return self._generate_financial_story(activity_log, details)
            else:
                return self._fallback_story(activity_log)
                
        except Exception as e:
            logger.error(f"Error generating story for activity {activity_log.id}: {e}")
            return self._fallback_story(activity_log)
    
    def _parse_activity_details(self, details_str: str) -> Optional[Dict]:
        """Parse JSON details from activity log"""
        try:
            if isinstance(details_str, str):
                return json.loads(details_str)
            elif isinstance(details_str, dict):
                return details_str
            return None
        except (json.JSONDecodeError, TypeError):
            return None
    
    def _generate_financial_story(self, activity_log, details: Dict) -> Dict[str, Any]:
        """Generate story for financial data updates"""
        council = activity_log.related_council
        field_name = details.get('field_name', '')
        new_value = details.get('new_value')
        old_value = details.get('old_value')
        
        try:
            # Get field information
            field = DataField.objects.filter(slug=field_name).first()
            if not field:
                return self._fallback_story(activity_log)
            
            # Get financial year from activity
            year_str = details.get('year')
            financial_year = None
            if year_str:
                financial_year = FinancialYear.objects.filter(label=year_str).first()
            
            if not financial_year:
                financial_year = FinancialYear.objects.filter(is_current=True).first()
            
            # Format the values
            value_text = self._format_financial_value(new_value, field)
            
            # Generate contextual insights
            context = self._generate_context(council, field, new_value, old_value, financial_year)
            
            # Build the story
            story = {
                'title': f"{council.name}'s {field.name} Updated",
                'story': self._build_story_text(council, field, value_text, financial_year, context),
                'summary': f"{field.name} recorded as {value_text}",
                'field_name': field.name,
                'field_slug': field.slug,
                'value': value_text,
                'context': context,
                'year': financial_year.label if financial_year else None,
                'council_name': council.name,
                'council_slug': council.slug,
                'activity_type': activity_log.get_activity_type_display(),
                'timestamp': activity_log.created,
            }
            
            return story
            
        except Exception as e:
            logger.error(f"Error generating financial story: {e}")
            return self._fallback_story(activity_log)
    
    def _format_financial_value(self, value, field: DataField) -> str:
        """Format financial values for display"""
        if value is None:
            return "N/A"
        
        try:
            # Convert to decimal for consistency
            if isinstance(value, str):
                value = Decimal(value.replace(',', '').replace('£', ''))
            elif not isinstance(value, Decimal):
                value = Decimal(str(value))
            
            # Format based on field type and magnitude
            if field.category in ['financial', 'income', 'balance_sheet', 'spending']:
                if value >= 1_000_000:
                    return f"£{value / 1_000_000:.1f}m"
                elif value >= 1_000:
                    return f"£{value / 1_000:.1f}k"
                else:
                    return f"£{value:,.0f}"
            else:
                return f"{value:,.0f}"
                
        except (ValueError, TypeError, AttributeError):
            return str(value)
    
    def _generate_context(self, council: Council, field: DataField, new_value, old_value, financial_year: FinancialYear) -> Dict[str, Any]:
        """Generate contextual information for the story"""
        context = {}
        
        try:
            # Calculate percentage change if we have old value
            if old_value and new_value:
                try:
                    old_val = Decimal(str(old_value).replace(',', '').replace('£', ''))
                    new_val = Decimal(str(new_value).replace(',', '').replace('£', ''))
                    
                    if old_val != 0:
                        change_pct = ((new_val - old_val) / old_val) * 100
                        context['percentage_change'] = f"{change_pct:+.1f}%"
                        context['direction'] = "increased" if change_pct > 0 else "decreased"
                        context['magnitude'] = "significantly" if abs(change_pct) > 20 else "moderately" if abs(change_pct) > 5 else "slightly"
                except (ValueError, TypeError, ZeroDivisionError):
                    pass
            
            # Get ranking among similar councils
            ranking_info = self._get_ranking_context(council, field, new_value, financial_year)
            if ranking_info:
                context.update(ranking_info)
            
            # Get council type for context
            if council.council_type:
                context['council_type'] = council.council_type.name
            
            return context
            
        except Exception as e:
            logger.error(f"Error generating context: {e}")
            return {}
    
    def _get_ranking_context(self, council: Council, field: DataField, value, financial_year: FinancialYear) -> Dict[str, Any]:
        """Get ranking information for context"""
        try:
            if not value or not financial_year:
                return {}
            
            # Get all councils with this field value for comparison
            similar_figures = FinancialFigure.objects.filter(
                field=field,
                year=financial_year,
                value__isnull=False
            ).select_related('council', 'council__council_type')
            
            if council.council_type:
                # Filter to same council type for more relevant comparison
                similar_figures = similar_figures.filter(
                    council__council_type=council.council_type
                )
            
            # Convert value for comparison
            try:
                compare_value = Decimal(str(value).replace(',', '').replace('£', ''))
            except (ValueError, TypeError):
                return {}
            
            # Count councils with higher values
            higher_count = similar_figures.filter(value__gt=compare_value).count()
            total_count = similar_figures.count()
            
            if total_count > 1:
                rank = higher_count + 1
                
                # Generate ranking description
                if rank == 1:
                    return {'ranking': f"highest among {council.council_type.name if council.council_type else 'all'} councils"}
                elif rank <= 3:
                    return {'ranking': f"{self._ordinal(rank)} highest among {council.council_type.name if council.council_type else 'all'} councils"}
                elif rank >= total_count - 2:
                    return {'ranking': f"among the lowest for {council.council_type.name if council.council_type else 'all'} councils"}
                else:
                    percentile = ((total_count - rank + 1) / total_count) * 100
                    return {'ranking': f"{percentile:.0f}th percentile among {council.council_type.name if council.council_type else 'all'} councils"}
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting ranking context: {e}")
            return {}
    
    def _ordinal(self, n: int) -> str:
        """Convert number to ordinal (1st, 2nd, 3rd, etc.)"""
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        return f"{n}{suffix}"
    
    def _build_story_text(self, council: Council, field: DataField, value_text: str, financial_year: FinancialYear, context: Dict) -> str:
        """Build the main story text"""
        # Base story
        year_text = f" for {financial_year.label}" if financial_year else ""
        story = f"{council.name}'s {field.name}{year_text} has been recorded as {value_text}."
        
        # Add change information
        if 'percentage_change' in context and 'direction' in context:
            story += f" This was {context['percentage_change']} {context['direction']} from the previous period"
            if 'magnitude' in context:
                story += f", representing a {context['magnitude']} change"
            story += "."
        
        # Add ranking information
        if 'ranking' in context:
            story += f" This places them as the {context['ranking']}."
        
        return story
    
    def _fallback_story(self, activity_log) -> Dict[str, Any]:
        """Generate a basic fallback story"""
        return {
            'title': f"{activity_log.related_council.name} - {activity_log.get_activity_type_display()}",
            'story': activity_log.description,
            'summary': activity_log.description,
            'field_name': None,
            'field_slug': None,
            'value': None,
            'context': {},
            'year': None,
            'council_name': activity_log.related_council.name,
            'council_slug': activity_log.related_council.slug,
            'activity_type': activity_log.get_activity_type_display(),
            'timestamp': activity_log.created,
        }