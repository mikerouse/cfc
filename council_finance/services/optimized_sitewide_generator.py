"""
Optimized Site-wide AI Factoid Generator Service

Uses pre-aggregated data summaries and intelligent sampling to generate
cross-council insights efficiently at scale.
"""

import json
import logging
import random
from typing import Dict, List, Optional, Any
from django.utils import timezone
from django.core.cache import cache

from council_finance.models import SitewideDataSummary, SitewideFactoidSchedule
from council_finance.services.ai_factoid_generator import AIFactoidGenerator

logger = logging.getLogger(__name__)


class OptimizedSitewideFactoidGenerator(AIFactoidGenerator):
    """
    Optimized generator for site-wide factoids that uses pre-aggregated
    data summaries instead of processing raw council data in real-time.
    """
    
    def __init__(self):
        """Initialize with optimized settings."""
        super().__init__()
        self.max_fields_in_prompt = 8  # Limit fields to control prompt size
        self.max_councils_per_field = 6  # Limit councils mentioned per field
    
    def generate_optimized_factoids(self, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Generate cross-council factoids using pre-aggregated data summaries.
        
        Args:
            limit: Maximum number of factoids to generate
            
        Returns:
            List of factoid dictionaries with text and metadata
        """
        try:
            if not self.client:
                logger.warning("OpenAI client unavailable - using fallback factoids")
                return self._generate_fallback_sitewide_factoids(limit)
            
            # Get optimized data from summaries
            summary_data = self._get_optimized_summary_data()
            
            if not summary_data or len(summary_data) < 2:
                logger.warning("Insufficient summary data available - using fallback")
                return self._generate_fallback_sitewide_factoids(limit)
            
            # Generate AI prompt using compact summaries
            prompt = self._build_optimized_prompt(summary_data, limit)
            
            # Call OpenAI API
            logger.info(f"🤖 Generating {limit} optimized sitewide factoids")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Parse response
            factoids = self._parse_ai_response(response.choices[0].message.content)
            
            if factoids:
                logger.info(f"✅ Generated {len(factoids)} optimized sitewide factoids")
                return factoids[:limit]
            else:
                logger.warning("Failed to parse AI response - using fallback")
                return self._generate_fallback_sitewide_factoids(limit)
                
        except Exception as e:
            logger.error(f"Optimized sitewide factoid generation failed: {e}")
            return self._generate_fallback_sitewide_factoids(limit)
    
    def _get_optimized_summary_data(self) -> List[Dict]:
        """
        Get pre-aggregated summary data for the most recent date.
        
        Returns:
            List of field summaries suitable for compact prompt generation
        """
        try:
            # Get the most recent date with summaries
            latest_date = SitewideDataSummary.objects.values_list(
                'date_calculated', flat=True
            ).order_by('-date_calculated').first()
            
            if not latest_date:
                logger.warning("No sitewide data summaries found")
                return []
            
            # Get summaries for the latest date, ordered by data completeness
            summaries = SitewideDataSummary.objects.filter(
                date_calculated=latest_date
            ).select_related('field', 'year').order_by(
                '-data_completeness', '-total_councils'
            )
            
            # Convert to compact format for AI processing
            summary_data = []
            
            for summary in summaries[:self.max_fields_in_prompt]:
                # Skip fields with poor data quality
                if summary.data_completeness < 30:  # Less than 30% council coverage
                    continue
                
                summary_dict = summary.get_insights_summary()
                
                # Add interesting comparisons if available
                if summary.type_averages:
                    summary_dict['type_insights'] = self._extract_type_insights(summary.type_averages)
                
                if summary.nation_averages:
                    summary_dict['nation_insights'] = self._extract_nation_insights(summary.nation_averages)
                
                # Add outlier information for interesting stories
                if summary.outlier_count > 0:
                    summary_dict['has_outliers'] = True
                    summary_dict['outlier_count'] = summary.outlier_count
                
                summary_data.append(summary_dict)
            
            logger.info(f"Retrieved {len(summary_data)} field summaries for analysis")
            return summary_data
            
        except Exception as e:
            logger.error(f"Failed to get optimized summary data: {e}")
            return []
    
    def _extract_type_insights(self, type_averages: Dict) -> Dict:
        """Extract interesting insights from council type averages."""
        if len(type_averages) < 2:
            return {}
        
        # Find highest and lowest performing types
        sorted_types = sorted(type_averages.items(), key=lambda x: x[1], reverse=True)
        
        highest = sorted_types[0]
        lowest = sorted_types[-1]
        
        # Calculate percentage difference
        if lowest[1] > 0:
            percentage_diff = ((highest[1] - lowest[1]) / lowest[1]) * 100
        else:
            percentage_diff = 0
        
        return {
            'highest_type': highest[0],
            'highest_value': highest[1],
            'lowest_type': lowest[0],
            'lowest_value': lowest[1],
            'percentage_difference': round(percentage_diff, 1)
        }
    
    def _extract_nation_insights(self, nation_averages: Dict) -> Dict:
        """Extract interesting insights from nation averages."""
        if len(nation_averages) < 2:
            return {}
        
        # Find nation differences
        sorted_nations = sorted(nation_averages.items(), key=lambda x: x[1], reverse=True)
        
        if len(sorted_nations) >= 2:
            highest = sorted_nations[0]
            lowest = sorted_nations[-1]
            
            if lowest[1] > 0:
                percentage_diff = ((highest[1] - lowest[1]) / lowest[1]) * 100
            else:
                percentage_diff = 0
            
            return {
                'highest_nation': highest[0],
                'highest_value': highest[1],
                'lowest_nation': lowest[0],
                'lowest_value': lowest[1],
                'percentage_difference': round(percentage_diff, 1)
            }
        
        return {}
    
    def _build_optimized_prompt(self, summary_data: List[Dict], limit: int) -> str:
        """
        Build an optimized AI prompt using pre-aggregated summary data.
        
        This method creates much more compact prompts than the original system
        by using statistical summaries instead of raw council data.
        """
        # Create compact data structure for AI
        analysis_data = {
            'analysis_year': summary_data[0]['year'] if summary_data else 'Latest',
            'total_fields_analyzed': len(summary_data),
            'field_summaries': []
        }
        
        for summary in summary_data:
            field_summary = {
                'field': summary['field_name'],
                'councils_analyzed': summary['total_councils'],
                'average_value_millions': summary['average'],
                'range': f"£{summary['range']['min']:.1f}M to £{summary['range']['max']:.1f}M",
                'top_performers': [
                    f"{council['council_name']} (£{council['value']:.1f}M)"
                    for council in summary['top_performers'][:3]
                ],
                'bottom_performers': [
                    f"{council['council_name']} (£{council['value']:.1f}M)"
                    for council in summary['bottom_performers'][:3]
                ]
            }
            
            # Add type/nation insights if available
            if 'type_insights' in summary and summary['type_insights']:
                ti = summary['type_insights']
                field_summary['type_insight'] = (
                    f"{ti['highest_type']} councils average £{ti['highest_value']:.1f}M, "
                    f"{ti['percentage_difference']:.0f}% higher than {ti['lowest_type']} councils"
                )
            
            if 'nation_insights' in summary and summary['nation_insights']:
                ni = summary['nation_insights']
                field_summary['nation_insight'] = (
                    f"{ni['highest_nation']} averages £{ni['highest_value']:.1f}M, "
                    f"{ni['percentage_difference']:.0f}% higher than {ni['lowest_nation']}"
                )
            
            analysis_data['field_summaries'].append(field_summary)
        
        # Build compact JSON for AI
        json_data = json.dumps(analysis_data, indent=2)
        
        prompt = f"""
You are a financial analyst specializing in UK local government cross-council comparisons. Using the aggregated data below, generate {limit} compelling factoids for a news ticker.

AGGREGATED ANALYSIS DATA:
{json_data}

REQUIREMENTS:
- Generate exactly {limit} factoids
- Maximum 30 words per factoid
- Focus on interesting comparisons, extremes, and patterns
- Use specific council names and precise figures
- Write in engaging news ticker style
- Highlight significant differences between council types, nations, or individual performance
- Use GBP instead of £ symbol to avoid encoding issues

FACTOID TYPES TO PRIORITIZE:
- Cross-council extremes: "Worcestershire paid £91M in interest, 5x more than Rutland's £18M"
- Type comparisons: "County councils average £45M more debt than unitary authorities"
- Nation patterns: "Scottish councils outperform English counterparts by 23% in debt management"
- Efficiency insights: "Top 3 performers manage twice the population with half the debt"

RESPONSE FORMAT:
Return ONLY a valid JSON array. NO markdown, NO explanatory text:

[
    {{
        "text": "Worcestershire's £91M interest payments dwarf Rutland's £18M, highlighting massive scale differences",
        "insight_type": "comparison",
        "confidence": 0.95
    }},
    {{
        "text": "County councils average £45M higher debt than unitary authorities across {analysis_data['total_fields_analyzed']} metrics",
        "insight_type": "type_analysis", 
        "confidence": 0.9
    }}
]

JSON REQUIREMENTS:
- Use double quotes for all strings
- Escape internal quotes with \\"
- Do not include markdown formatting
- Ensure all strings are properly terminated
"""
        
        return prompt.strip()
    
    def _generate_fallback_sitewide_factoids(self, limit: int = 3) -> List[Dict]:
        """
        Generate fallback factoids when optimized generation isn't available.
        
        Uses cached summaries or creates basic comparative statements.
        """
        fallback_factoids = []
        
        try:
            # Try to get some recent summary data for basic factoids
            recent_summaries = SitewideDataSummary.objects.select_related(
                'field'
            ).order_by('-date_calculated', '-total_councils')[:5]
            
            if recent_summaries:
                for summary in recent_summaries[:limit]:
                    if summary.top_5_councils and len(summary.top_5_councils) >= 2:
                        top_council = summary.top_5_councils[0]
                        
                        fallback_factoids.append({
                            'text': f"{top_council['council_name']} leads in {summary.field.name.lower()} with £{top_council['value']:.1f}M",
                            'insight_type': 'basic',
                            'confidence': 0.8
                        })
                    
                    if len(fallback_factoids) >= limit:
                        break
            
            # Fill remaining slots with generic insights
            while len(fallback_factoids) < limit:
                generic_factoids = [
                    "Cross-council financial analysis reveals significant variations in spending patterns",
                    "Regional differences highlight diverse approaches to local government finance",
                    "Council type and size create distinct financial profiles across the UK"
                ]
                
                fallback_factoids.append({
                    'text': generic_factoids[len(fallback_factoids) % len(generic_factoids)],
                    'insight_type': 'system',
                    'confidence': 0.5
                })
        
        except Exception as e:
            logger.error(f"Fallback factoid generation failed: {e}")
            # Ultimate fallback
            for i in range(limit):
                fallback_factoids.append({
                    'text': f"Financial data analysis across {SitewideDataSummary.objects.count()} council metrics available",
                    'insight_type': 'system',
                    'confidence': 0.3
                })
        
        logger.info(f"Generated {len(fallback_factoids)} fallback sitewide factoids")
        return fallback_factoids[:limit]