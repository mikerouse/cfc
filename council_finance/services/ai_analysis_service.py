"""
AI Analysis Service for Council Finance Analysis
Handles OpenAI API integration and analysis generation
"""
import os
import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.template import Template, Context
from django.core.cache import cache

import openai

from ..models import (
    Council, FinancialYear, AIModel, AIAnalysisTemplate, 
    AIAnalysisConfiguration, CouncilAIAnalysis, FinancialFigure,
    CouncilCharacteristic
)
from ..agents.counter_agent import CounterAgent

logger = logging.getLogger(__name__)


class AIAnalysisService:
    """Service for generating AI-powered council financial analysis"""
    
    def __init__(self):
        self.openai_client = None
        self.counter_agent = CounterAgent()
        self._initialize_openai()
    
    def _initialize_openai(self):
        """Initialize OpenAI client with API key from environment"""
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            logger.warning("OPENAI_API_KEY not found in settings")
            return
        
        try:
            self.openai_client = openai.OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
    
    def get_or_create_analysis(
        self, 
        council: Council, 
        year: FinancialYear, 
        configuration: Optional[AIAnalysisConfiguration] = None,
        force_refresh: bool = False
    ) -> Optional[CouncilAIAnalysis]:
        """
        Get existing analysis or create new one for council/year combination
        """
        if not self.openai_client:
            logger.error("OpenAI client not available")
            return None
        
        # Use default configuration if none provided
        if not configuration:
            configuration = AIAnalysisConfiguration.objects.filter(
                is_active=True, is_default=True
            ).first()
            
            if not configuration:
                logger.error("No active default AI analysis configuration found")
                return None
        
        # Check for existing non-expired analysis
        if not force_refresh:
            existing = CouncilAIAnalysis.objects.filter(
                council=council,
                year=year,
                configuration=configuration,
                status__in=['completed', 'cached']
            ).first()
            
            if existing and not existing.is_expired:
                logger.info(f"Using cached analysis for {council.name} - {year.label}")
                existing.status = 'cached'
                existing.save(update_fields=['status'])
                return existing
        else:
            # For force refresh, delete any existing analysis records
            existing_analyses = CouncilAIAnalysis.objects.filter(
                council=council,
                year=year,
                configuration=configuration
            )
            if existing_analyses.exists():
                logger.info(f"Force refresh: deleting {existing_analyses.count()} existing analysis records for {council.name} - {year.label}")
                existing_analyses.delete()

        # Generate new analysis
        try:
            return self._generate_analysis(council, year, configuration)
        except Exception as e:
            logger.error(f"Failed to generate analysis for {council.name}: {e}")
            return None

    def _generate_analysis(
        self, 
        council: Council, 
        year: FinancialYear, 
        configuration: AIAnalysisConfiguration
    ) -> CouncilAIAnalysis:
        """Generate new AI analysis for council"""
        start_time = time.time()
        
        # Create pending analysis record
        analysis = CouncilAIAnalysis.objects.create(
            council=council,
            year=year,
            configuration=configuration,
            status='processing',
            expires_at=timezone.now() + timedelta(minutes=configuration.cache_duration_minutes),
            input_data={}
        )
        
        try:
            # Gather financial data
            financial_data = self._gather_financial_data(council, year)
            analysis.input_data = financial_data
            analysis.save(update_fields=['input_data'])
            
            # Generate context for AI prompt
            context = self._build_analysis_context(council, year, financial_data, configuration.template)
            
            # Generate AI analysis
            ai_response = self._call_openai_api(context, configuration)
            
            # Process response
            processed_results = self._process_ai_response(ai_response)
            
            # Update analysis record
            processing_time = int((time.time() - start_time) * 1000)
            
            analysis.analysis_text = processed_results['analysis_text']
            analysis.analysis_summary = processed_results['summary']
            analysis.key_insights = processed_results['insights']
            analysis.risk_factors = processed_results['risks']
            analysis.recommendations = processed_results['recommendations']
            analysis.tokens_used = ai_response.get('usage', {}).get('total_tokens')
            analysis.processing_time_ms = processing_time
            analysis.cost_estimate = self._calculate_cost(ai_response, configuration.model)
            analysis.status = 'completed'
            analysis.save()
            
            logger.info(f"Generated analysis for {council.name} - {year.label} in {processing_time}ms")
            return analysis
            
        except Exception as e:
            analysis.status = 'failed'
            analysis.error_message = str(e)
            analysis.save(update_fields=['status', 'error_message'])
            logger.error(f"Analysis generation failed: {e}")
            raise
    
    def _gather_financial_data(self, council: Council, year: FinancialYear) -> Dict[str, Any]:
        """Gather comprehensive financial data for analysis"""
        data = {
            'council_info': {
                'name': council.name,
                'type': council.council_type.name if council.council_type else 'Unknown',
                'nation': council.council_nation.name if council.council_nation else 'Unknown',
                'population': getattr(council, 'latest_population', None),
            },
            'year_info': {
                'current_year': year.label,
                'status': year.status if hasattr(year, 'status') else 'unknown',
            },
            'financial_figures': {},
            'characteristics': {},
            'counters': {},
            'previous_year': {}
        }
        
        try:
            # Get current year financial figures
            current_figures = FinancialFigure.objects.filter(
                council=council, year=year
            ).select_related('field').values(
                'field__slug', 'field__name', 'value', 'field__content_type'
            )
            
            for figure in current_figures:
                slug = figure['field__slug']
                data['financial_figures'][slug] = {
                    'name': figure['field__name'],
                    'value': float(figure['value']) if figure['value'] else 0,
                    'formatted_value': f"£{figure['value']:,.0f}" if figure['value'] else '£0',
                    'unit': figure['field__unit'] or '£'
                }
            
            # Get council characteristics
            characteristics = CouncilCharacteristic.objects.filter(
                council=council
            ).select_related('field').values(
                'field__slug', 'field__name', 'value'
            )
            
            for char in characteristics:
                data['characteristics'][char['field__slug']] = {
                    'name': char['field__name'],
                    'value': char['value']
                }
            
            # Get counter data using CounterAgent
            try:
                counter_results = self.counter_agent.run(
                    council_slug=council.slug, 
                    year_label=year.label
                )
                for slug, result in counter_results.items():
                    if isinstance(result, dict) and 'value' in result:
                        data['counters'][slug] = {
                            'value': result['value'],
                            'formatted': result.get('formatted', str(result['value']))
                        }
                    else:
                        data['counters'][slug] = {
                            'value': result,
                            'formatted': str(result) if result is not None else 'N/A'
                        }
            except Exception as e:
                logger.warning(f"Failed to get counter data: {e}")
            
            # Get previous year data for comparison
            previous_year = self._get_previous_year(year)
            if previous_year:
                data['previous_year'] = self._get_previous_year_data(council, previous_year)
            
        except Exception as e:
            logger.error(f"Error gathering financial data: {e}")
        
        return data
    
    def _get_previous_year(self, current_year: FinancialYear) -> Optional[FinancialYear]:
        """Get the previous financial year"""
        try:
            current_year_num = int(current_year.label.split('/')[0])
            previous_year_label = f"{current_year_num-1}/{str(current_year_num)[-2:]}"
            return FinancialYear.objects.filter(label=previous_year_label).first()
        except (ValueError, AttributeError):
            return None
    
    def _get_previous_year_data(self, council: Council, previous_year: FinancialYear) -> Dict[str, Any]:
        """Get financial data for previous year"""
        data = {
            'year_label': previous_year.label,
            'financial_figures': {},
            'counters': {}
        }
        
        try:
            # Get previous year figures
            prev_figures = FinancialFigure.objects.filter(
                council=council, year=previous_year
            ).select_related('field').values(
                'field__slug', 'field__name', 'value'
            )
            
            for figure in prev_figures:
                slug = figure['field__slug']
                data['financial_figures'][slug] = {
                    'name': figure['field__name'],
                    'value': float(figure['value']) if figure['value'] else 0,
                    'formatted_value': f"£{figure['value']:,.0f}" if figure['value'] else '£0'
                }
            
            # Get previous year counter data
            try:
                prev_counter_results = self.counter_agent.run(
                    council_slug=council.slug,
                    year_label=previous_year.label
                )
                for slug, result in prev_counter_results.items():
                    if isinstance(result, dict) and 'value' in result:
                        data['counters'][slug] = result['value']
                    else:
                        data['counters'][slug] = result
            except Exception as e:
                logger.warning(f"Failed to get previous year counter data: {e}")
                
        except Exception as e:
            logger.error(f"Error gathering previous year data: {e}")
        
        return data
    
    def _build_analysis_context(
        self, 
        council: Council, 
        year: FinancialYear, 
        financial_data: Dict[str, Any],
        template: AIAnalysisTemplate
    ) -> Dict[str, str]:
        """Build context for AI analysis prompt"""
        
        # Create Django template context
        context_data = {
            'council': council,
            'year': year,
            'financial_data': financial_data,
            'council_name': council.name,
            'council_type': council.council_type.name if council.council_type else 'Council',
            'current_year': year.label,
            'population': getattr(council, 'latest_population', None),
        }
        
        # Add percentage changes if previous year data available
        if financial_data.get('previous_year') and financial_data['previous_year'].get('counters'):
            context_data['changes'] = self._calculate_year_over_year_changes(
                financial_data['counters'],
                financial_data['previous_year']['counters']
            )
        
        # Render system prompt using Django template
        django_template = Template(template.system_prompt)
        rendered_prompt = django_template.render(Context(context_data))
        
        return {
            'system_prompt': rendered_prompt,
            'user_message': self._format_financial_data_for_ai(financial_data)
        }
    
    def _calculate_year_over_year_changes(
        self, 
        current_data: Dict[str, Any], 
        previous_data: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate year-over-year percentage changes"""
        changes = {}
        
        for slug, current_value in current_data.items():
            if slug in previous_data:
                try:
                    current_val = float(current_value.get('value', 0))
                    previous_val = float(previous_data[slug])
                    
                    if previous_val != 0:
                        change_pct = ((current_val - previous_val) / previous_val) * 100
                        changes[slug] = {
                            'percentage': round(change_pct, 1),
                            'direction': 'increase' if change_pct > 0 else 'decrease',
                            'current': current_val,
                            'previous': previous_val
                        }
                except (ValueError, TypeError):
                    continue
        
        return changes
    
    def _format_financial_data_for_ai(self, financial_data: Dict[str, Any]) -> str:
        """Format financial data as readable text for AI analysis"""
        formatted_parts = []
        
        # Council info
        council_info = financial_data.get('council_info', {})
        formatted_parts.append(f"Council: {council_info.get('name')} ({council_info.get('type')})")
        
        if council_info.get('population'):
            formatted_parts.append(f"Population: {council_info['population']:,}")
        
        # Current year counters
        formatted_parts.append(f"\n{financial_data['year_info']['current_year']} Financial Data:")
        counters = financial_data.get('counters', {})
        for slug, data in counters.items():
            formatted_parts.append(f"- {slug.replace('_', ' ').title()}: {data.get('formatted', 'N/A')}")
        
        # Previous year comparison
        if financial_data.get('previous_year'):
            prev_data = financial_data['previous_year']
            formatted_parts.append(f"\n{prev_data['year_label']} Comparison:")
            prev_counters = prev_data.get('counters', {})
            for slug, value in prev_counters.items():
                if slug in counters:
                    current_val = counters[slug].get('value', 0)
                    if isinstance(value, (int, float)) and value != 0:
                        change = ((current_val - value) / value) * 100
                        direction = "↑" if change > 0 else "↓"
                        formatted_parts.append(f"- {slug.replace('_', ' ').title()}: {direction} {abs(change):.1f}%")
        
        return '\n'.join(formatted_parts)
    
    def _call_openai_api(
        self, 
        context: Dict[str, str], 
        configuration: AIAnalysisConfiguration
    ) -> Dict[str, Any]:
        """Make API call to OpenAI"""
        try:
            response = self.openai_client.chat.completions.create(
                model=configuration.model.model_id,
                messages=[
                    {"role": "system", "content": context['system_prompt']},
                    {"role": "user", "content": context['user_message']}
                ],
                max_tokens=configuration.model.max_tokens,
                temperature=configuration.model.temperature,
                timeout=configuration.timeout_seconds
            )
            
            return {
                'content': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _process_ai_response(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Process AI response into structured data"""
        content = ai_response.get('content', '')
        
        # Try to extract structured sections
        insights = self._extract_section(content, 'KEY INSIGHTS', 'RISK FACTORS')
        risks = self._extract_section(content, 'RISK FACTORS', 'RECOMMENDATIONS')
        recommendations = self._extract_section(content, 'RECOMMENDATIONS', None)
        
        # Generate summary (first paragraph or first 200 chars)
        lines = content.strip().split('\n')
        summary = ''
        for line in lines:
            if line.strip() and not line.strip().startswith('#'):
                summary = line.strip()[:200] + ('...' if len(line.strip()) > 200 else '')
                break
        
        return {
            'analysis_text': content,
            'summary': summary,
            'insights': self._parse_list_items(insights),
            'risks': self._parse_list_items(risks),
            'recommendations': self._parse_list_items(recommendations)
        }
    
    def _extract_section(self, content: str, start_marker: str, end_marker: Optional[str]) -> str:
        """Extract a section from AI response content"""
        try:
            start_idx = content.upper().find(start_marker)
            if start_idx == -1:
                return ''
            
            start_idx = content.find('\n', start_idx) + 1
            
            if end_marker:
                end_idx = content.upper().find(end_marker, start_idx)
                if end_idx != -1:
                    return content[start_idx:end_idx].strip()
            
            return content[start_idx:].strip()
        except Exception:
            return ''
    
    def _parse_list_items(self, section_text: str) -> List[str]:
        """Parse bullet points or numbered lists from section text"""
        items = []
        lines = section_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove bullet points or numbers
            clean_line = line
            if line.startswith(('•', '-', '*')):
                clean_line = line[1:].strip()
            elif line[0].isdigit() and '.' in line:
                clean_line = line.split('.', 1)[1].strip()
            
            if clean_line:
                items.append(clean_line)
        
        return items[:5]  # Limit to 5 items
    
    def _calculate_cost(self, ai_response: Dict[str, Any], model: AIModel) -> Optional[Decimal]:
        """Calculate estimated cost of API call"""
        if not model.cost_per_token or not ai_response.get('usage'):
            return None
        
        try:
            total_tokens = ai_response['usage']['total_tokens']
            return Decimal(str(model.cost_per_token)) * Decimal(str(total_tokens))
        except Exception:
            return None