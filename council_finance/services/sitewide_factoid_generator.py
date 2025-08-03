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
            'population',
            # Use actual existing fields instead of planned ones
            'usable-reserves',
            'unusable-reserves',
            # Note: employee-costs and housing-benefit-payments not yet available
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
            
            # Generate outlier analysis for interesting insights
            outlier_analysis = self._detect_interesting_outliers(aggregated_stats)
            efficiency_analysis = self._analyze_efficiency_patterns(aggregated_stats)
            
            return {
                'year': latest_year.label,
                'fields_data': aggregated_stats,
                'type_comparisons': type_comparisons,
                'nation_comparisons': nation_comparisons,
                'outlier_analysis': outlier_analysis,
                'efficiency_analysis': efficiency_analysis,
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
        # Adjust the minimum council count based on total councils in system
        total_councils = Council.objects.count()
        min_councils = max(2, min(10, int(total_councils * 0.5)))  # At least 2, or 50% of councils, max 10
        
        recent_years = FinancialFigure.objects.values('year').annotate(
            council_count=Count('council', distinct=True)
        ).filter(
            council_count__gte=min_councils
        ).order_by('-year__start_date')[:1]
        
        if recent_years:
            year_id = recent_years[0]['year']
            return FinancialYear.objects.get(id=year_id)
        
        # Fallback: get the year with the most council data
        best_year = FinancialFigure.objects.values('year').annotate(
            council_count=Count('council', distinct=True)
        ).filter(
            council_count__gte=1  # At least 1 council has data
        ).order_by('-council_count', '-year__start_date')[:1]
        
        if best_year:
            year_id = best_year[0]['year']
            return FinancialYear.objects.get(id=year_id)
        
        # Final fallback to most recent financial year
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
    
    def _detect_interesting_outliers(self, fields_data: Dict) -> Dict[str, Any]:
        """
        Detect interesting outliers - councils that punch above/below their weight.
        
        Identifies patterns like:
        - Small councils with surprisingly high reserves
        - Large councils with unusually low costs
        - Councils performing opposite to expectations
        """
        outliers = {
            'size_vs_performance': [],
            'unexpected_efficiency': [],
            'contrarian_patterns': []
        }
        
        try:
            # Get population data for size analysis
            population_data = fields_data.get('population', {})
            if not population_data or not population_data.get('councils'):
                logger.info("No population data available for outlier detection")
                return outliers
                
            population_councils = {c['council_slug']: c['value'] for c in population_data['councils']}
            
            # Analyze each financial field for outliers
            for field_slug, field_data in fields_data.items():
                if field_slug == 'population' or not field_data.get('councils'):
                    continue
                    
                outliers_found = self._find_field_outliers(
                    field_slug, field_data, population_councils
                )
                
                # Categorize outliers
                for outlier in outliers_found:
                    outlier_type = outlier.get('type', 'unknown')
                    if outlier_type == 'size_mismatch':
                        outliers['size_vs_performance'].append(outlier)
                    elif outlier_type == 'efficiency_surprise':
                        outliers['unexpected_efficiency'].append(outlier)
                    elif outlier_type == 'contrarian':
                        outliers['contrarian_patterns'].append(outlier)
                        
        except Exception as e:
            logger.error(f"Error in outlier detection: {e}")
            
        return outliers
    
    def _find_field_outliers(self, field_slug: str, field_data: Dict, population_data: Dict) -> List[Dict]:
        """Find outliers for a specific field."""
        outliers = []
        councils = field_data.get('councils', [])
        
        if len(councils) < 2:
            return outliers
            
        try:
            # Calculate per-capita values where population data exists
            per_capita_data = []
            for council in councils:
                slug = council['council_slug']
                if slug in population_data and population_data[slug] > 0:
                    per_capita = council['value'] / population_data[slug]
                    per_capita_data.append({
                        'council_slug': slug,
                        'council_name': council['council_name'],
                        'absolute_value': council['value'],
                        'population': population_data[slug],
                        'per_capita_value': per_capita,
                        'council_type': council.get('council_type', 'Unknown'),
                        'council_nation': council.get('council_nation', 'Unknown')
                    })
            
            if len(per_capita_data) < 2:
                return outliers
                
            # Sort by population to identify size categories
            per_capita_data.sort(key=lambda x: x['population'])
            
            # Find size vs performance mismatches
            smallest = per_capita_data[0]
            largest = per_capita_data[-1]
            
            # Calculate ratios and differences
            pop_ratio = largest['population'] / smallest['population']
            per_capita_ratio = largest['per_capita_value'] / smallest['per_capita_value'] if smallest['per_capita_value'] > 0 else float('inf')
            
            # Detect interesting patterns
            if pop_ratio > 2:  # Significant size difference
                if field_slug in ['interest-paid', 'employee-costs'] and per_capita_ratio < 0.5:
                    # Large council surprisingly efficient
                    outliers.append({
                        'type': 'efficiency_surprise',
                        'field': field_slug,
                        'pattern': 'large_council_efficient',
                        'large_council': largest,
                        'small_council': smallest,
                        'population_ratio': pop_ratio,
                        'efficiency_ratio': per_capita_ratio,
                        'insight': f"Despite being {pop_ratio:.1f}x larger, {largest['council_name']} spends {(1/per_capita_ratio):.1f}x less per capita on {field_slug.replace('-', ' ')}"
                    })
                elif field_slug in ['reserves-and-balances'] and per_capita_ratio < 0.7:
                    # Small council surprisingly well-reserved
                    outliers.append({
                        'type': 'size_mismatch',
                        'field': field_slug,
                        'pattern': 'small_council_well_reserved',
                        'small_council': smallest,
                        'large_council': largest,
                        'population_ratio': pop_ratio,
                        'reserves_ratio': 1/per_capita_ratio,
                        'insight': f"{smallest['council_name']} maintains {(1/per_capita_ratio):.1f}x higher reserves per capita than {largest['council_name']} despite being {pop_ratio:.1f}x smaller"
                    })
                elif per_capita_ratio > 2:
                    # Small council disproportionately high spending
                    outliers.append({
                        'type': 'contrarian',
                        'field': field_slug,
                        'pattern': 'small_council_high_spending',
                        'small_council': smallest,
                        'large_council': largest,
                        'population_ratio': pop_ratio,
                        'spending_ratio': per_capita_ratio,
                        'insight': f"{smallest['council_name']} spends {per_capita_ratio:.1f}x more per capita on {field_slug.replace('-', ' ')} than {largest['council_name']}"
                    })
                    
        except Exception as e:
            logger.error(f"Error finding outliers for {field_slug}: {e}")
            
        return outliers
    
    def _analyze_efficiency_patterns(self, fields_data: Dict) -> Dict[str, Any]:
        """
        Analyze efficiency patterns across councils.
        
        Looks for councils that consistently outperform or underperform
        across multiple metrics.
        """
        efficiency_patterns = {
            'consistent_performers': [],
            'mixed_performers': [],
            'efficiency_leaders': [],
            'areas_for_improvement': []
        }
        
        try:
            population_data = fields_data.get('population', {})
            if not population_data or not population_data.get('councils'):
                return efficiency_patterns
                
            population_map = {c['council_slug']: c['value'] for c in population_data['councils']}
            
            # Track performance across multiple fields
            council_scores = {}
            
            cost_fields = ['interest-paid', 'employee-costs', 'current-liabilities']
            efficiency_fields = ['reserves-and-balances', 'business-rates-income']
            
            for field_slug in cost_fields + efficiency_fields:
                field_data = fields_data.get(field_slug, {})
                if not field_data or not field_data.get('councils'):
                    continue
                    
                # Calculate efficiency scores (lower is better for costs, higher for reserves/income)
                councils_with_per_capita = []
                for council in field_data['councils']:
                    slug = council['council_slug']
                    if slug in population_map and population_map[slug] > 0:
                        per_capita = council['value'] / population_map[slug]
                        councils_with_per_capita.append({
                            'slug': slug,
                            'name': council['council_name'],
                            'per_capita': per_capita
                        })
                
                if len(councils_with_per_capita) < 2:
                    continue
                    
                # Rank councils (1 = best, higher = worse)
                if field_slug in cost_fields:
                    # For costs, lower per capita is better
                    councils_with_per_capita.sort(key=lambda x: x['per_capita'])
                else:
                    # For reserves/income, higher per capita is better  
                    councils_with_per_capita.sort(key=lambda x: x['per_capita'], reverse=True)
                
                # Record rankings
                for rank, council in enumerate(councils_with_per_capita, 1):
                    slug = council['slug']
                    if slug not in council_scores:
                        council_scores[slug] = {
                            'name': council['name'],
                            'field_scores': {},
                            'total_rank': 0,
                            'fields_analyzed': 0
                        }
                    
                    council_scores[slug]['field_scores'][field_slug] = {
                        'rank': rank,
                        'per_capita': council['per_capita'],
                        'total_councils': len(councils_with_per_capita)
                    }
                    council_scores[slug]['total_rank'] += rank
                    council_scores[slug]['fields_analyzed'] += 1
            
            # Analyze patterns
            for slug, data in council_scores.items():
                if data['fields_analyzed'] >= 2:  # Need at least 2 fields for pattern
                    avg_rank = data['total_rank'] / data['fields_analyzed']
                    
                    if avg_rank <= 1.5:
                        efficiency_patterns['efficiency_leaders'].append({
                            'council_slug': slug,
                            'council_name': data['name'],
                            'average_rank': avg_rank,
                            'fields_analyzed': data['fields_analyzed'],
                            'performance': 'consistently_excellent'
                        })
                    elif avg_rank >= (len(council_scores) - 0.5):
                        efficiency_patterns['areas_for_improvement'].append({
                            'council_slug': slug,
                            'council_name': data['name'],
                            'average_rank': avg_rank,
                            'fields_analyzed': data['fields_analyzed'],
                            'performance': 'needs_attention'
                        })
                    else:
                        efficiency_patterns['mixed_performers'].append({
                            'council_slug': slug,
                            'council_name': data['name'],
                            'average_rank': avg_rank,
                            'fields_analyzed': data['fields_analyzed'],
                            'performance': 'mixed_results'
                        })
                        
        except Exception as e:
            logger.error(f"Error in efficiency pattern analysis: {e}")
            
        return efficiency_patterns
    
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
            'nation_comparisons': data['nation_comparisons'],
            'outlier_analysis': data.get('outlier_analysis', {}),
            'efficiency_patterns': data.get('efficiency_analysis', {})
        }, indent=2)
        
        return f"""
You are analysing UK local government financial data across {data['total_councils']} councils for {data['year']}.

CROSS-COUNCIL DATASET (JSON):
{json_data_str}

ANALYSIS REQUIREMENTS:
1. Generate {limit} engaging factoids that compare councils against each other
2. **PRIORITIZE OUTLIERS & SURPRISES**: Use the outlier_analysis and efficiency_patterns data to find the most interesting insights
3. Always mention specific council names when making comparisons
4. Include both council names as hyperlinks in your response
5. Use formats like: "[Council A] paid 30% more than [Council B] despite having lower population"
6. Make council names clickable links using format: <a href="/councils/SLUG/">COUNCIL NAME</a>
7. Keep each factoid to 1-2 sentences maximum
8. Focus on unexpected patterns that challenge assumptions:
   - Small councils outperforming large ones
   - Efficiency surprises (large councils being surprisingly lean)
   - Contrarian patterns (opposite of what you'd expect)
   - Cross-metric efficiency patterns
9. Use UK English spelling and terminology
10. Prefer insights that reveal genuine surprises over obvious comparisons

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
- "efficiency_surprise": Large council surprisingly efficient or small council surprisingly inefficient
- "size_mismatch": Performance that contradicts council size expectations
- "contrarian_pattern": Council behaving opposite to what size/type would suggest
- "efficiency_leader": Council consistently outperforming across multiple metrics

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