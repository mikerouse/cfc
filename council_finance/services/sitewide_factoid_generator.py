"""
Site-wide AI Factoid Generator Service

Generates intelligent cross-council comparisons and insights for the homepage.
Extends the existing AI factoid system to work with data from all councils.
"""

import json
import logging
import random
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Q, Avg, Max, Min, Count
from django.db import models

from council_finance.models import Council, DataField, FinancialFigure, FinancialYear
from council_finance.services.ai_factoid_generator import AIFactoidGenerator

logger = logging.getLogger(__name__)


class SitewideFactoidGenerator(AIFactoidGenerator):
    """
    Generates AI-powered factoids for cross-council comparisons on the homepage.
    
    Creates intelligent insights like:
    - "Worcestershire County Council paid 30% more in interest payments than Aberdeen City Council"
    - "Metropolitan councils average £2.3M more in long-term liabilities than unitary authorities"
    - "Scottish councils consistently outperform English councils in debt management ratios"
    """
    
    def __init__(self):
        """Initialize with site-wide analysis capabilities."""
        super().__init__()
        self.cache_timeout = 1800  # 30 minutes cache for site-wide factoids
        self.comparison_fields = [
            'interest-paid',
            'total-debt', 
            'current-liabilities',
            'long-term-liabilities',
            'business-rates-income',
            'council-tax-income',
            'population'
        ]
        
    def generate_sitewide_factoids(self, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Generate cross-council comparison factoids for homepage display.
        
        Args:
            limit: Maximum number of factoids to generate
            
        Returns:
            List of factoid dictionaries with text, councils, and metadata
        """
        cache_key = f"sitewide_factoids_{limit}"
        cached_factoids = cache.get(cache_key)
        
        if cached_factoids:
            logger.info(f"✅ Returning {len(cached_factoids)} cached site-wide factoids")
            return cached_factoids
            
        try:
            # Gather cross-council data for analysis
            cross_council_data = self._gather_cross_council_data()
            
            if not cross_council_data or cross_council_data.get('total_councils', 0) < 2:
                logger.warning("❌ Insufficient cross-council data available for AI factoids, using fallback")
                return self._generate_fallback_sitewide_factoids()
                
            # Generate AI-powered insights
            factoids = self._generate_ai_sitewide_factoids(cross_council_data, limit)
            
            # Cache results
            cache.set(cache_key, factoids, self.cache_timeout)
            logger.info(f"✅ Generated and cached {len(factoids)} site-wide factoids")
            
            return factoids
            
        except Exception as e:
            logger.error(f"❌ Site-wide factoid generation failed: {e}")
            return self._generate_fallback_sitewide_factoids()
    
    def _gather_cross_council_data(self) -> Dict[str, Any]:
        """
        Gather financial data from all councils for cross-comparison analysis.
        
        Returns:
            Dictionary containing aggregated data from all councils
        """
        try:
            # Get latest year with most data coverage
            latest_year = self._get_latest_analysis_year()
            
            if not latest_year:
                logger.warning("❌ No financial year data available")
                return {}
            
            # Gather council data for comparison fields
            council_data = {}
            aggregated_stats = {}
            
            for field_slug in self.comparison_fields:
                try:
                    field = DataField.objects.get(slug=field_slug)
                    
                    # Get all council data for this field in the latest year
                    financial_figures = FinancialFigure.objects.filter(
                        field=field,
                        year=latest_year
                    ).select_related('council', 'council__council_type', 'council__council_nation').values(
                        'council__name', 
                        'council__slug',
                        'council__council_type__name',
                        'council__council_nation__name',
                        'value'
                    )
                    
                    field_data = []
                    for figure in financial_figures:
                        try:
                            value = float(figure['value'])
                            field_data.append({
                                'council_name': figure['council__name'],
                                'council_slug': figure['council__slug'],
                                'council_type': figure['council__council_type__name'],
                                'council_nation': figure['council__council_nation__name'],
                                'value': value
                            })
                        except (ValueError, TypeError):
                            continue
                    
                    if field_data:
                        # Sort by value to identify extremes
                        field_data.sort(key=lambda x: x['value'], reverse=True)
                        
                        values = [item['value'] for item in field_data]
                        aggregated_stats[field_slug] = {
                            'councils': field_data,
                            'count': len(field_data),
                            'max': max(values),
                            'min': min(values),
                            'avg': sum(values) / len(values),
                            'highest_council': field_data[0],
                            'lowest_council': field_data[-1]
                        }
                        
                except DataField.DoesNotExist:
                    logger.warning(f"Field {field_slug} does not exist")
                    continue
                except Exception as e:
                    logger.error(f"Error gathering data for {field_slug}: {e}")
                    continue
            
            # Generate council type and nation comparisons
            type_comparisons = self._generate_type_comparisons(aggregated_stats)
            nation_comparisons = self._generate_nation_comparisons(aggregated_stats)
            
            return {
                'year': latest_year.label,
                'fields_data': aggregated_stats,
                'type_comparisons': type_comparisons,
                'nation_comparisons': nation_comparisons,
                'total_councils': len(set(
                    council['council_slug'] 
                    for field_data in aggregated_stats.values() 
                    for council in field_data['councils']
                ))
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to gather cross-council data: {e}")
            return {}
    
    def _get_latest_analysis_year(self) -> FinancialYear:
        """Get the latest year with good data coverage across councils."""
        # Get the most recent year that has data for multiple councils
        recent_years = FinancialFigure.objects.values('year').annotate(
            council_count=Count('council', distinct=True)
        ).filter(
            council_count__gte=10  # At least 10 councils have data
        ).order_by('-year__start_date')[:1]
        
        if recent_years:
            year_id = recent_years[0]['year']
            return FinancialYear.objects.get(id=year_id)
        
        # Fallback to most recent financial year
        return FinancialYear.objects.order_by('-start_date').first()
    
    def _generate_type_comparisons(self, fields_data: Dict) -> Dict[str, Any]:
        """Generate comparisons between different council types."""
        type_stats = {}
        
        for field_slug, field_data in fields_data.items():
            type_groups = {}
            
            for council in field_data['councils']:
                council_type = council['council_type'] or 'Unknown'
                if council_type not in type_groups:
                    type_groups[council_type] = []
                type_groups[council_type].append(council['value'])
            
            # Calculate averages for each type
            type_averages = {}
            for council_type, values in type_groups.items():
                if len(values) >= 2:  # Only include types with multiple councils
                    type_averages[council_type] = {
                        'average': sum(values) / len(values),
                        'count': len(values),
                        'max': max(values),
                        'min': min(values)
                    }
            
            if len(type_averages) >= 2:
                type_stats[field_slug] = type_averages
        
        return type_stats
    
    def _generate_nation_comparisons(self, fields_data: Dict) -> Dict[str, Any]:
        """Generate comparisons between different nations."""
        nation_stats = {}
        
        for field_slug, field_data in fields_data.items():
            nation_groups = {}
            
            for council in field_data['councils']:
                nation = council['council_nation'] or 'Unknown'
                if nation not in nation_groups:
                    nation_groups[nation] = []
                nation_groups[nation].append(council['value'])
            
            # Calculate averages for each nation
            nation_averages = {}
            for nation, values in nation_groups.items():
                if len(values) >= 3:  # Only include nations with multiple councils
                    nation_averages[nation] = {
                        'average': sum(values) / len(values),
                        'count': len(values),
                        'max': max(values),
                        'min': min(values)
                    }
            
            if len(nation_averages) >= 2:
                nation_stats[field_slug] = nation_averages
        
        return nation_stats
    
    def _generate_ai_sitewide_factoids(self, data: Dict, limit: int) -> List[Dict[str, Any]]:
        """Generate AI-powered site-wide factoids from cross-council data."""
        if not self.client:
            logger.warning("❌ OpenAI client not available, using fallback factoids")
            return self._generate_fallback_sitewide_factoids()
        
        prompt = self._build_sitewide_analysis_prompt(data, limit)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a financial analyst specializing in UK local government cross-council comparisons."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip()
            factoids = self._parse_ai_sitewide_response(content, data)
            
            logger.info(f"✅ Generated {len(factoids)} AI site-wide factoids")
            return factoids
            
        except Exception as e:
            logger.error(f"❌ AI site-wide factoid generation failed: {e}")
            return self._generate_fallback_sitewide_factoids()
    
    def _build_sitewide_analysis_prompt(self, data: Dict, limit: int) -> str:
        """Build AI prompt for site-wide cross-council analysis."""
        
        # Format data for analysis
        json_data_str = json.dumps({
            'analysis_year': data['year'],
            'total_councils_analysed': data['total_councils'],
            'field_comparisons': data['fields_data'],
            'council_type_comparisons': data['type_comparisons'],
            'nation_comparisons': data['nation_comparisons']
        }, indent=2)
        
        return f"""
You are analysing UK local government financial data across {data['total_councils']} councils for {data['year']}.

CROSS-COUNCIL DATASET (JSON):
{json_data_str}

ANALYSIS REQUIREMENTS:
1. Generate {limit} engaging factoids that compare councils against each other
2. Focus on interesting contrasts, surprises, or patterns across councils
3. Always mention specific council names when making comparisons
4. Include both council names as hyperlinks in your response
5. Use formats like: "[Council A] paid 30% more than [Council B] despite having lower population"
6. Make council names clickable links using format: <a href="/councils/SLUG/">COUNCIL NAME</a>
7. Keep each factoid to 1-2 sentences maximum
8. Focus on financial metrics like interest payments, debt levels, reserves
9. Highlight unexpected patterns (small councils outperforming large ones, etc.)
10. Use UK English spelling and terminology

RESPONSE FORMAT:
Return exactly {limit} factoids as a JSON array:
[
  {{
    "text": "Factoid text with <a href='/councils/council-slug/'>Council Name</a> links",
    "councils_mentioned": ["council-slug-1", "council-slug-2"],
    "field": "interest_payments",
    "insight_type": "direct_comparison"
  }}
]

INSIGHT TYPES:
- "direct_comparison": Two specific councils compared
- "type_comparison": Council types compared (metropolitan vs unitary)
- "nation_comparison": Nations compared (England vs Scotland)
- "outlier_analysis": Unusual patterns or outliers identified

Generate insights that would engage users and encourage them to explore specific councils.
"""
    
    def _parse_ai_sitewide_response(self, content: str, data: Dict) -> List[Dict[str, Any]]:
        """Parse AI response into structured factoid data."""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                factoids_data = json.loads(json_match.group())
                
                # Validate and enhance factoids
                validated_factoids = []
                for factoid in factoids_data:
                    if isinstance(factoid, dict) and 'text' in factoid:
                        validated_factoids.append({
                            'text': factoid.get('text', ''),
                            'councils_mentioned': factoid.get('councils_mentioned', []),
                            'field': factoid.get('field', 'unknown'),
                            'insight_type': factoid.get('insight_type', 'general'),
                            'generated_at': timezone.now().isoformat(),
                            'data_year': data.get('year', 'unknown')
                        })
                
                return validated_factoids
                
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"❌ Failed to parse AI sitewide response: {e}")
        
        # Fallback: treat as simple text and create basic factoids
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        factoids = []
        
        for i, line in enumerate(lines[:3]):  # Max 3 factoids
            factoids.append({
                'text': line,
                'councils_mentioned': [],
                'field': 'general',
                'insight_type': 'general',
                'generated_at': timezone.now().isoformat(),
                'data_year': data.get('year', 'unknown')
            })
        
        return factoids
    
    def _generate_fallback_sitewide_factoids(self) -> List[Dict[str, Any]]:
        """Generate contextual fallback factoids when AI is unavailable or data is limited."""
        
        # Try to get some actual data for context
        try:
            councils_with_data = Council.objects.filter(
                characteristics__isnull=False
            ).distinct()[:2]
            
            if len(councils_with_data) >= 2:
                council1 = councils_with_data[0]
                council2 = councils_with_data[1]
                
                fallback_factoids = [
                    {
                        'text': f'Comparing <a href="/councils/{council1.slug}/">{council1.name}</a> and <a href="/councils/{council2.slug}/">{council2.name}</a> reveals diverse approaches to local government finance.',
                        'councils_mentioned': [council1.slug, council2.slug],
                        'field': 'general',
                        'insight_type': 'direct_comparison',
                        'generated_at': timezone.now().isoformat(),
                        'data_year': 'current'
                    },
                    {
                        'text': f'Financial transparency initiatives help citizens understand how councils like <a href="/councils/{council1.slug}/">{council1.name}</a> manage public resources.',
                        'councils_mentioned': [council1.slug],
                        'field': 'general',
                        'insight_type': 'general',
                        'generated_at': timezone.now().isoformat(),
                        'data_year': 'current'
                    },
                    {
                        'text': 'Cross-council analysis reveals significant variations in financial management approaches across the UK.',
                        'councils_mentioned': [],
                        'field': 'general',
                        'insight_type': 'general',
                        'generated_at': timezone.now().isoformat(),
                        'data_year': 'current'
                    }
                ]
            else:
                # Generic fallbacks when no data is available
                fallback_factoids = [
                    {
                        'text': 'Building comprehensive cross-council financial comparisons to improve transparency.',
                        'councils_mentioned': [],
                        'field': 'general',
                        'insight_type': 'general',
                        'generated_at': timezone.now().isoformat(),
                        'data_year': 'current'
                    },
                    {
                        'text': 'Local government financial data analysis helps citizens make informed decisions.',
                        'councils_mentioned': [],
                        'field': 'general',
                        'insight_type': 'general',
                        'generated_at': timezone.now().isoformat(),
                        'data_year': 'current'
                    },
                    {
                        'text': 'Developing AI-powered insights to reveal patterns in council financial management.',
                        'councils_mentioned': [],
                        'field': 'general',
                        'insight_type': 'general',
                        'generated_at': timezone.now().isoformat(),
                        'data_year': 'current'
                    }
                ]
            
            return random.sample(fallback_factoids, min(3, len(fallback_factoids)))
            
        except Exception as e:
            logger.error(f"❌ Error generating fallback factoids: {e}")
            return [
                {
                    'text': 'Cross-council financial analysis in development.',
                    'councils_mentioned': [],
                    'field': 'general',
                    'insight_type': 'general',
                    'generated_at': timezone.now().isoformat(),
                    'data_year': 'current'
                }
            ]