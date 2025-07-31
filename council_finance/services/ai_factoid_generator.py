"""
AI-Powered Factoid Generator Service

Generates intelligent insights about council financial data using OpenAI API.
Replaces template-based factoid system with dynamic AI analysis.
"""

import json
import logging
import os
from decimal import Decimal
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Q
import openai

logger = logging.getLogger(__name__)

class AIFactoidGenerator:
    """
    Generates AI-powered factoids for council financial data analysis.
    
    Uses OpenAI API to create intelligent insights based on:
    - Financial time series data
    - Peer council comparisons  
    - Population trends
    - Regional context
    """
    
    def __init__(self):
        """Initialize the AI client and configuration."""
        self.client = None
        self._setup_openai_client()
        self.max_factoids = 3
        self.max_tokens = 500
        self.temperature = 0.7
        
    def _setup_openai_client(self):
        """Set up OpenAI client with API key from environment."""
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
            
        if api_key:
            openai.api_key = api_key
            self.client = openai
            logger.info("✅ OpenAI client initialized successfully")
        else:
            logger.warning("⚠️ OpenAI API key not found - AI factoids will use fallback")
    
    def generate_insights(self, council_data: Dict, limit: int = 3, style: str = 'news_ticker') -> List[Dict]:
        """
        Generate AI factoids for a council using comprehensive data analysis.
        
        Args:
            council_data: Dictionary containing council and financial data
            limit: Maximum number of factoids to generate
            style: Style of factoids ('news_ticker', 'analytical', 'comparison')
            
        Returns:
            List of factoid dictionaries with text and insight_type
        """
        try:
            if not self.client:
                logger.warning("OpenAI client unavailable - using fallback factoids")
                return self._generate_fallback_factoids(council_data, limit)
                
            # Generate AI prompt from council data
            prompt = self._build_analysis_prompt(council_data, limit, style)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Parse and validate response
            factoids = self._parse_ai_response(response.choices[0].message.content)
            
            if factoids:
                logger.info(f"✅ Generated {len(factoids)} AI factoids for {council_data['council'].name}")
                return factoids[:limit]  # Ensure we don't exceed limit
            else:
                logger.warning("AI response parsing failed - using fallback")
                return self._generate_fallback_factoids(council_data, limit)
                
        except Exception as e:
            logger.error(f"❌ AI factoid generation failed: {str(e)}")
            return self._generate_fallback_factoids(council_data, limit)
    
    def _build_analysis_prompt(self, data: Dict, limit: int, style: str) -> str:
        """
        Build comprehensive analysis prompt for OpenAI based on council data.
        
        Includes financial time series, peer comparisons, and contextual information.
        """
        council = data['council']
        
        # Format financial data for AI analysis
        financial_summary = self._format_financial_data(data.get('financial_time_series', {}))
        peer_summary = self._format_peer_data(data.get('peer_comparisons', {}))
        population_info = self._format_population_data(data.get('population_data', {}))
        
        prompt = f"""
        Analyse this UK council's financial data and generate {limit} interesting factoids in news ticker style.
        
        Council: {council.name}
        Type: {getattr(council, 'council_type', 'Council')}
        {population_info}
        
        Financial Data Analysis:
        {financial_summary}
        
        Peer Comparisons:
        {peer_summary}
        
        Requirements:
        - Maximum 25 words per factoid
        - Focus on trends, comparisons, notable patterns, peaks, and changes
        - Use specific figures and years where available
        - Write in engaging news ticker style
        - Highlight significant financial insights
        - Return as valid JSON array only, no other text
        
        Response format (JSON only):
        [
            {{
                "text": "Interest payments peaked in 2023 at £3.8M, up 58% from 2019",
                "insight_type": "trend"
            }},
            {{
                "text": "Spends £205 per resident on interest - 23% above regional average",
                "insight_type": "comparison"
            }}
        ]
        
        Insight types: trend, comparison, peak, change, ranking, efficiency, volatility
        """
        
        return prompt.strip()
    
    def _format_financial_data(self, financial_data: Dict) -> str:
        """Format financial time series data for AI prompt."""
        if not financial_data:
            return "Limited financial data available for analysis."
            
        formatted_lines = []
        
        # Process each metric over time
        for metric, years_data in financial_data.items():
            if years_data and isinstance(years_data, dict):
                # Get latest and earliest values
                years = sorted(years_data.keys())
                if len(years) >= 2:
                    latest_year = years[-1]
                    earliest_year = years[0]
                    latest_value = years_data[latest_year]
                    earliest_value = years_data[earliest_year]
                    
                    # Calculate percentage change
                    if earliest_value and latest_value:
                        try:
                            change_pct = ((float(latest_value) - float(earliest_value)) / float(earliest_value)) * 100
                            formatted_lines.append(
                                f"{metric.replace('_', ' ').title()}: {latest_year} £{latest_value}M "
                                f"({change_pct:+.1f}% from {earliest_year})"
                            )
                        except (ValueError, TypeError, ZeroDivisionError):
                            formatted_lines.append(
                                f"{metric.replace('_', ' ').title()}: {latest_year} £{latest_value}M"
                            )
        
        return "\n".join(formatted_lines) if formatted_lines else "Financial data processing in progress."
    
    def _format_peer_data(self, peer_data: Dict) -> str:
        """Format peer comparison data for AI prompt."""
        if not peer_data:
            return "Peer comparison data being compiled."
            
        formatted_lines = []
        
        for metric, comparison in peer_data.items():
            if isinstance(comparison, dict):
                council_value = comparison.get('council_value')
                peer_average = comparison.get('peer_average')
                percentile = comparison.get('percentile')
                
                if council_value and peer_average:
                    metric_name = metric.replace('_', ' ').title()
                    formatted_lines.append(
                        f"{metric_name}: £{council_value}M vs peer average £{peer_average}M"
                    )
                    
                    if percentile:
                        formatted_lines.append(f"  (Ranks in {percentile}th percentile)")
        
        return "\n".join(formatted_lines) if formatted_lines else "Peer analysis in development."
    
    def _format_population_data(self, population_data: Dict) -> str:
        """Format population data for AI prompt."""
        if not population_data:
            return "Population: Data being updated"
            
        latest_pop = population_data.get('latest')
        if latest_pop:
            return f"Population: {latest_pop:,} residents"
        
        return "Population: Information pending"
    
    def _parse_ai_response(self, response_text: str) -> List[Dict]:
        """
        Parse and validate AI response JSON.
        
        Returns list of factoid dictionaries or empty list if parsing fails.
        """
        try:
            # Clean response text - remove any markdown formatting
            clean_text = response_text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            # Parse JSON
            factoids = json.loads(clean_text)
            
            # Validate structure
            if not isinstance(factoids, list):
                logger.error("AI response is not a list")
                return []
            
            validated_factoids = []
            for factoid in factoids:
                if isinstance(factoid, dict) and 'text' in factoid:
                    # Ensure required fields exist
                    validated_factoid = {
                        'text': str(factoid['text'])[:150],  # Limit length
                        'insight_type': factoid.get('insight_type', 'general'),
                        'confidence': factoid.get('confidence', 0.8)
                    }
                    validated_factoids.append(validated_factoid)
            
            return validated_factoids
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response JSON: {e}")
            logger.debug(f"Raw response: {response_text}")
            return []
        except Exception as e:
            logger.error(f"Error validating AI response: {e}")
            return []
    
    def _generate_fallback_factoids(self, council_data: Dict, limit: int = 3) -> List[Dict]:
        """
        Generate basic fallback factoids when AI service is unavailable.
        
        Uses simple council data to create basic insights.
        """
        council = council_data['council']
        fallback_factoids = []
        
        try:
            # Basic council information
            if hasattr(council, 'latest_population') and council.latest_population:
                fallback_factoids.append({
                    'text': f"Population: {council.latest_population:,} residents",
                    'insight_type': 'basic',
                    'confidence': 1.0
                })
            
            # Latest financial data if available
            financial_data = council_data.get('financial_time_series', {})
            if 'total_debt' in financial_data:
                debt_data = financial_data['total_debt']
                if debt_data:
                    latest_year = max(debt_data.keys())
                    latest_debt = debt_data[latest_year]
                    fallback_factoids.append({
                        'text': f"Latest debt figure: £{latest_debt}M for {latest_year}",
                        'insight_type': 'basic',
                        'confidence': 1.0
                    })
            
            # Council type information
            if hasattr(council, 'council_type'):
                fallback_factoids.append({
                    'text': f"{council.council_type} serving {council.name} area",
                    'insight_type': 'basic',
                    'confidence': 1.0
                })
            
        except Exception as e:
            logger.error(f"Error generating fallback factoids: {e}")
            # Ultimate fallback
            fallback_factoids = [{
                'text': f"Financial data for {council.name} is being processed",
                'insight_type': 'basic',
                'confidence': 1.0
            }]
        
        return fallback_factoids[:limit]


class CouncilDataGatherer:
    """
    Gathers comprehensive council data for AI analysis.
    
    Collects financial time series, peer comparisons, population trends,
    and regional context for intelligent factoid generation.
    """
    
    def __init__(self):
        self.cache_timeout = 3600  # 1 hour cache for data gathering
    
    def gather_council_data(self, council) -> Dict[str, Any]:
        """
        Gather comprehensive data for a council for AI analysis.
        
        Args:
            council: Council model instance
            
        Returns:
            Dictionary with all data needed for AI factoid generation
        """
        cache_key = f"ai_council_data:{council.slug}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.debug(f"Using cached data for {council.name}")
            return cached_data
        
        try:
            data = {
                'council': council,
                'financial_time_series': self._get_financial_time_series(council),
                'peer_comparisons': self._get_peer_council_data(council),
                'population_data': self._get_population_trends(council),
                'context': self._get_regional_context(council)
            }
            
            # Cache the gathered data
            cache.set(cache_key, data, self.cache_timeout)
            logger.info(f"✅ Gathered comprehensive data for {council.name}")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to gather council data: {e}")
            # Return minimal data structure
            return {
                'council': council,
                'financial_time_series': {},
                'peer_comparisons': {},
                'population_data': {},
                'context': {}
            }
    
    def _get_financial_time_series(self, council) -> Dict:
        """Get financial data over time for trend analysis."""
        try:
            from council_finance.models import CouncilCharacteristic, FinancialYear
            
            # Get key financial metrics over time
            financial_metrics = [
                'total-debt', 'current-liabilities', 'long-term-liabilities',
                'interest-payments', 'total-revenue', 'total-expenditure'
            ]
            
            time_series = {}
            
            for metric_slug in financial_metrics:
                metric_data = {}
                
                # Get data for each year
                characteristics = CouncilCharacteristic.objects.filter(
                    council=council,
                    field__slug=metric_slug
                ).select_related('field')
                
                for char in characteristics:
                    if char.year and char.value:
                        try:
                            # Convert to millions for consistency
                            value_millions = float(char.value) / 1_000_000
                            metric_data[char.year.label] = f"{value_millions:.1f}"
                        except (ValueError, TypeError):
                            continue
                
                if metric_data:
                    time_series[metric_slug.replace('-', '_')] = metric_data
            
            return time_series
            
        except Exception as e:
            logger.error(f"Error gathering financial time series: {e}")
            return {}
    
    def _get_peer_council_data(self, council) -> Dict:
        """Get peer council comparison data."""
        try:
            # This would implement peer comparison logic
            # For now, return structure that AI can work with
            return {
                'peer_group': f"Similar {getattr(council, 'council_type', 'councils')}",
                'comparison_note': 'Peer analysis being developed'
            }
        except Exception as e:
            logger.error(f"Error gathering peer data: {e}")
            return {}
    
    def _get_population_trends(self, council) -> Dict:
        """Get population data and trends."""
        try:
            population_data = {}
            
            if hasattr(council, 'latest_population') and council.latest_population:
                population_data['latest'] = council.latest_population
            
            return population_data
            
        except Exception as e:
            logger.error(f"Error gathering population data: {e}")
            return {}
    
    def _get_regional_context(self, council) -> Dict:
        """Get regional and contextual information."""
        try:
            context = {}
            
            if hasattr(council, 'nation'):
                context['nation'] = council.nation
            
            if hasattr(council, 'council_type'):
                context['type'] = str(council.council_type)
            
            return context
            
        except Exception as e:
            logger.error(f"Error gathering regional context: {e}")
            return {}