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
        self.max_factoids = 10
        self.max_tokens = 1500  # Increased for longer responses
        self.temperature = 0.7
        self.model = self._get_configured_model()
        
    def _get_configured_model(self):
        """Get the configured OpenAI model from settings or use default."""
        # Check for configured model in settings
        configured_model = getattr(settings, 'OPENAI_MODEL', None)
        
        if configured_model:
            logger.info(f"🤖 Using configured OpenAI model: {configured_model}")
            return configured_model
        
        # Default to gpt-4o-mini for cost efficiency
        default_model = "gpt-4o-mini"
        logger.info(f"🤖 Using default OpenAI model: {default_model}")
        return default_model
        
    def get_model_info(self):
        """Get detailed information about the current model."""
        model_info = {
            'name': self.model,
            'display_name': self._get_model_display_name(self.model),
            'cost_per_1k_tokens': self._get_model_cost(self.model),
            'max_tokens': self._get_model_max_tokens(self.model),
            'description': self._get_model_description(self.model)
        }
        return model_info
        
    def _get_model_display_name(self, model):
        """Get human-readable display name for model."""
        model_names = {
            'gpt-4o-mini': 'GPT-4o Mini',
            'gpt-4o': 'GPT-4o',
            'gpt-4-turbo': 'GPT-4 Turbo',
            'gpt-4': 'GPT-4',
            'gpt-3.5-turbo': 'GPT-3.5 Turbo'
        }
        return model_names.get(model, model)
        
    def _get_model_cost(self, model):
        """Get estimated cost per 1k tokens for model (in USD)."""
        # Costs as of 2025 - these should be updated periodically
        model_costs = {
            'gpt-4o-mini': 0.000150,  # $0.150 per 1M tokens
            'gpt-4o': 0.0025,         # $2.50 per 1M tokens  
            'gpt-4-turbo': 0.01,      # $10 per 1M tokens
            'gpt-4': 0.03,            # $30 per 1M tokens
            'gpt-3.5-turbo': 0.0015   # $1.50 per 1M tokens
        }
        return model_costs.get(model, 0.01)  # Default to moderate cost
        
    def _get_model_max_tokens(self, model):
        """Get maximum tokens for model."""
        model_max_tokens = {
            'gpt-4o-mini': 128000,
            'gpt-4o': 128000,
            'gpt-4-turbo': 128000,
            'gpt-4': 8192,
            'gpt-3.5-turbo': 4096
        }
        return model_max_tokens.get(model, 8192)
        
    def _get_model_description(self, model):
        """Get description of model capabilities."""
        model_descriptions = {
            'gpt-4o-mini': 'Cost-effective model with good performance for factoid generation',
            'gpt-4o': 'Latest high-performance model with excellent reasoning',
            'gpt-4-turbo': 'Fast, high-capability model with large context window',
            'gpt-4': 'Original GPT-4 model with strong reasoning capabilities',
            'gpt-3.5-turbo': 'Fast and economical model for simpler tasks'
        }
        return model_descriptions.get(model, 'AI model for text generation')
        
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
                logger.error("OpenAI client unavailable - cannot generate AI factoids")
                raise Exception("OpenAI API not configured")
                
            # Generate AI prompt from council data
            prompt = self._build_analysis_prompt(council_data, limit, style)
            
            # Call OpenAI API
            print(f"[AI-API] Calling OpenAI {self.model} - Requesting {limit} AI insights for {council_data['council'].name}")
            logger.info(f"🤖 Calling OpenAI {self.model} for {council_data['council'].name}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Parse and validate response
            factoids = self._parse_ai_response(response.choices[0].message.content)
            
            if factoids:
                logger.info(f"🤖 Generated {len(factoids)} LIVE AI factoids for {council_data['council'].name}")
                print(f"[AI-SUCCESS] Generated {len(factoids)} LIVE AI insights using OpenAI {self.model} for {council_data['council'].name}")
                return factoids[:limit]  # Ensure we don't exceed limit
            else:
                logger.error("🔄 AI response parsing failed")
                raise Exception("Failed to parse AI response - invalid format")
                
        except Exception as e:
            logger.error(f"❌ AI factoid generation failed: {str(e)}")
            # Re-raise the exception instead of generating fallback factoids
            raise
    
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
        
        # Build comprehensive JSON data structure for AI
        import json
        
        financial_data = data.get('financial_time_series', {})
        
        council_json_data = {
            "council": {
                "name": council.name,
                "slug": council.slug,
                "type": str(getattr(council, 'council_type', 'Council')),
                "nation": data.get('context', {}).get('nation', 'Unknown')
            },
            "population": population_info,
            "financial_data": financial_data,
            "data_summary": {
                "total_fields": len(financial_data),
                "fields_with_data": list(financial_data.keys()),
                "available_years": sorted(list(set(
                    year for field_data in financial_data.values() 
                    for year in field_data.get('years', {}).keys()
                    if year != 'latest'
                )))
            }
        }
        
        # Convert to formatted JSON string
        json_data_str = json.dumps(council_json_data, indent=2)
        
        prompt = f"""
You are a financial analyst specializing in UK local government finances. Analyze the complete financial dataset below and generate {limit} engaging factoids in news ticker style.

COMPLETE FINANCIAL DATASET (JSON):
{json_data_str}

ANALYSIS REQUIREMENTS:
- Generate exactly {limit} factoids
- Maximum 25 words per factoid  
- Focus on trends, comparisons, notable patterns, peaks, and significant changes
- Use specific figures and years from the data
- Write in engaging news ticker style (like BBC/Sky News tickers)
- Look for year-over-year changes, multi-year trends, and notable figures
- Prioritize the most significant financial insights
- Use UK currency formatting (GBP X.XM for millions to avoid encoding issues)

INSIGHT TYPES TO CONSIDER:
- "trend": Multi-year increases/decreases
- "peak": Highest/lowest values in dataset  
- "change": Year-over-year percentage changes
- "comparison": Relative scale between different metrics
- "efficiency": Per-capita or ratio-based insights
- "volatility": Fluctuations over time

RESPONSE FORMAT:
Return ONLY a valid JSON array with proper escaping. NO markdown, NO explanatory text, ONLY the JSON array:

[
    {{
        "text": "Interest paid jumped 15% to GBP 91.5M in 2024/25, highest in dataset",
        "insight_type": "peak",
        "confidence": 0.95
    }},
    {{
        "text": "Long-term liabilities surged GBP 88M to GBP 665.8M year-on-year", 
        "insight_type": "trend",
        "confidence": 0.9
    }}
]

CRITICAL JSON RULES:
- Use double quotes for all strings
- Escape any quotes within text with \"
- Do not include any text before or after the JSON array
- Do not use markdown formatting like ```json
- Ensure all strings are properly terminated
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
        Parse and validate AI response JSON with enhanced error handling.
        
        Returns list of factoid dictionaries or empty list if parsing fails.
        """
        try:
            # Clean response text more aggressively
            clean_text = response_text.strip()
            
            # Remove markdown formatting
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            elif clean_text.startswith('```'):
                clean_text = clean_text[3:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            
            # Remove any leading/trailing whitespace and newlines
            clean_text = clean_text.strip()
            
            # Log the cleaned text for debugging
            logger.debug(f"Cleaned AI response (first 200 chars): {clean_text[:200]}...")
            
            # Try to find JSON array if there's extra text
            import re
            json_match = re.search(r'\[.*\]', clean_text, re.DOTALL)
            if json_match:
                clean_text = json_match.group(0)
                logger.debug(f"Extracted JSON from response: {clean_text[:100]}...")
            
            # Parse JSON
            factoids = json.loads(clean_text)
            
            # Validate structure
            if not isinstance(factoids, list):
                logger.error(f"AI response is not a list, got: {type(factoids)}")
                return []
            
            validated_factoids = []
            for i, factoid in enumerate(factoids):
                if isinstance(factoid, dict) and 'text' in factoid:
                    # Clean the text to ensure no problematic characters
                    text = str(factoid['text']).strip()
                    text = text.replace('\n', ' ').replace('\r', ' ')
                    # Convert GBP back to £ symbol for display
                    text = text.replace('GBP ', '£')
                    text = text[:150]  # Limit length
                    
                    # Ensure required fields exist
                    validated_factoid = {
                        'text': text,
                        'insight_type': factoid.get('insight_type', 'general'),
                        'confidence': float(factoid.get('confidence', 0.8))
                    }
                    validated_factoids.append(validated_factoid)
                    logger.debug(f"Validated factoid {i+1}: {text[:50]}...")
                else:
                    logger.warning(f"Skipping invalid factoid {i+1}: {factoid}")
            
            logger.info(f"Successfully parsed {len(validated_factoids)} factoids from AI response")
            return validated_factoids
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response JSON: {e}")
            logger.error(f"Error at line {e.lineno}, column {e.colno}")
            logger.error(f"Raw response (first 500 chars): {response_text[:500]}")
            return []
        except Exception as e:
            logger.error(f"Error validating AI response: {e}")
            logger.error(f"Response type: {type(response_text)}")
            logger.error(f"Response length: {len(response_text)}")
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
            
            # Add debt information
            if 'total_debt' in financial_data:
                debt_data = financial_data['total_debt']
                if debt_data:
                    latest_year = max(debt_data.keys())
                    latest_debt = debt_data[latest_year]
                    fallback_factoids.append({
                        'text': f"Total debt: £{latest_debt}M for {latest_year}",
                        'insight_type': 'basic',
                        'confidence': 1.0
                    })
            
            # Add interest payments information
            if 'interest_payments' in financial_data:
                interest_data = financial_data['interest_payments']
                if interest_data:
                    latest_year = max(interest_data.keys())
                    latest_interest = interest_data[latest_year]
                    fallback_factoids.append({
                        'text': f"Interest payments: £{latest_interest}M in {latest_year}",
                        'insight_type': 'basic',
                        'confidence': 1.0
                    })
            
            # Add revenue information
            if 'total_revenue' in financial_data:
                revenue_data = financial_data['total_revenue']
                if revenue_data:
                    latest_year = max(revenue_data.keys())
                    latest_revenue = revenue_data[latest_year]
                    fallback_factoids.append({
                        'text': f"Total revenue: £{latest_revenue}M in {latest_year}",
                        'insight_type': 'basic',
                        'confidence': 1.0
                    })
            
            # Add per capita calculations if we have both debt and population
            if (hasattr(council, 'latest_population') and council.latest_population and 
                'total_debt' in financial_data and financial_data['total_debt']):
                debt_data = financial_data['total_debt']
                if debt_data:
                    latest_year = max(debt_data.keys())
                    latest_debt_millions = float(debt_data[latest_year])
                    debt_per_capita = (latest_debt_millions * 1_000_000) / council.latest_population
                    fallback_factoids.append({
                        'text': f"Debt per resident: £{debt_per_capita:,.0f} in {latest_year}",
                        'insight_type': 'comparison',
                        'confidence': 1.0
                    })
            
            # Council type information
            if hasattr(council, 'council_type'):
                fallback_factoids.append({
                    'text': f"{council.council_type} serving {council.name} area",
                    'insight_type': 'basic',
                    'confidence': 1.0
                })
            
            # Add current liabilities if available
            if 'current_liabilities' in financial_data:
                current_data = financial_data['current_liabilities']
                if current_data:
                    latest_year = max(current_data.keys())
                    latest_current = current_data[latest_year]
                    fallback_factoids.append({
                        'text': f"Current liabilities: £{latest_current}M in {latest_year}",
                        'insight_type': 'basic',
                        'confidence': 1.0
                    })
            
            # Ensure we have enough factoids
            while len(fallback_factoids) < limit:
                fallback_factoids.append({
                    'text': f"Financial analysis for {council.name} includes data from multiple years",
                    'insight_type': 'system',
                    'confidence': 1.0
                })
                break  # Don't loop infinitely
            
        except Exception as e:
            logger.error(f"Error generating fallback factoids: {e}")
            # Ultimate fallback - generate the requested number
            fallback_factoids = []
            for i in range(limit):
                if i == 0:
                    fallback_factoids.append({
                        'text': f"Financial data for {council.name} is being analysed",
                        'insight_type': 'system',
                        'confidence': 1.0
                    })
                elif i == 1:
                    fallback_factoids.append({
                        'text': f"AI insights are being generated for {council.name}",
                        'insight_type': 'system',
                        'confidence': 1.0
                    })
                else:
                    fallback_factoids.append({
                        'text': f"Comprehensive financial analysis available for {council.name}",
                        'insight_type': 'system',
                        'confidence': 1.0
                    })
        
        # Log the final result
        final_factoids = fallback_factoids[:limit]
        print(f"[FALLBACK-SUMMARY] Generated {len(final_factoids)} fallback factoids for {council.name}")
        for i, factoid in enumerate(final_factoids):
            print(f"  [FALLBACK-{i+1}] {factoid['text']}")
        
        return final_factoids


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
            logger.error(f"❌ Failed to gather council data for {council.slug}: {e}")
            logger.error(f"❌ Exception details: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            
            # Don't cache failed data - let it retry next time
            # Return minimal data structure
            return {
                'council': council,
                'financial_time_series': {},
                'peer_comparisons': {},
                'population_data': {},
                'context': {}
            }
    
    def _get_financial_time_series(self, council) -> Dict:
        """Get ALL available financial data over time for comprehensive AI analysis."""
        try:
            from council_finance.models import FinancialFigure, CouncilCharacteristic
            
            all_financial_data = {}
            
            # Get ALL FinancialFigure data (temporal financial data)
            financial_figures = FinancialFigure.objects.filter(
                council=council
            ).select_related('field', 'year').order_by('field__slug', 'year__label')
            
            for ff in financial_figures:
                field_slug = ff.field.slug
                field_name = ff.field.name
                year_label = ff.year.label
                
                if field_slug not in all_financial_data:
                    all_financial_data[field_slug] = {
                        'field_name': field_name,
                        'field_slug': field_slug,
                        'data_type': 'financial_figure',
                        'years': {}
                    }
                
                # Store raw value (let AI decide how to interpret)
                # Handle both numeric and text values
                if ff.value is not None:
                    # Numeric value
                    all_financial_data[field_slug]['years'][year_label] = {
                        'value': float(ff.value),
                        'value_millions': round(float(ff.value) / 1_000_000, 2),
                        'formatted': f"£{float(ff.value) / 1_000_000:.1f}M"
                    }
                elif ff.text_value is not None:
                    # Text value (URLs, etc.)
                    all_financial_data[field_slug]['years'][year_label] = {
                        'value': ff.text_value,
                        'formatted': ff.text_value
                    }
            
            # Get ALL CouncilCharacteristic data (non-temporal data like population)
            characteristics = CouncilCharacteristic.objects.filter(
                council=council
            ).select_related('field')
            
            for char in characteristics:
                field_slug = char.field.slug
                field_name = char.field.name
                
                if field_slug not in all_financial_data:
                    all_financial_data[field_slug] = {
                        'field_name': field_name,
                        'field_slug': field_slug,
                        'data_type': 'characteristic',
                        'years': {}
                    }
                
                # CouncilCharacteristic is non-temporal, use 'current' as key
                try:
                    # Try to convert to number
                    numeric_value = float(char.value)
                    all_financial_data[field_slug]['years']['current'] = {
                        'value': numeric_value,
                        'formatted': f"{numeric_value:,.0f}" if numeric_value >= 1000 else str(numeric_value)
                    }
                except (ValueError, TypeError):
                    # Keep as string if not numeric
                    all_financial_data[field_slug]['years']['current'] = {
                        'value': char.value,
                        'formatted': str(char.value)
                    }
            
            logger.info(f"✅ Gathered {len(all_financial_data)} fields with complete time series for {council.name}")
            return all_financial_data
            
        except Exception as e:
            logger.error(f"❌ Error gathering comprehensive financial data: {e}")
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