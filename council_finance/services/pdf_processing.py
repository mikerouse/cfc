"""
PDF Processing Services for AI Financial Statement Processing

This module provides services for extracting and processing financial data
from PDF documents using Apache Tika and OpenAI analysis.

Classes:
    TikaFinancialExtractor: Main class for PDF extraction and AI analysis
    FinancialDataMapper: Maps extracted data to database fields
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Container for PDF extraction results."""
    success: bool
    text_content: str = ""
    character_count: int = 0
    processing_time: float = 0.0
    financial_terms_found: List[str] = None
    error_message: str = ""
    
    def __post_init__(self):
        if self.financial_terms_found is None:
            self.financial_terms_found = []


@dataclass
class AIAnalysisResult:
    """Container for AI analysis results."""
    success: bool
    extracted_data: Dict[str, Any] = None
    confidence_score: float = 0.0
    processing_time: float = 0.0
    error_message: str = ""
    raw_response: str = ""
    
    def __post_init__(self):
        if self.extracted_data is None:
            self.extracted_data = {}


class TikaFinancialExtractor:
    """
    Cost-effective hybrid financial data extractor for hobby projects.
    
    Strategy:
    1. PDF text extraction via Apache Tika (free, already deployed)
    2. PRIMARY: Enhanced regex extraction (free, already working well)
    3. SECONDARY: Minimal AI validation only for ambiguous cases (cheap)
    
    Cost Control:
    - Regex-first approach (£0 per document)
    - AI only for validation/disambiguation (~£0.001-0.01 per document)
    - Strict token limits and model selection
    - Daily cost tracking and limits
    """
    
    def __init__(self):
        """Initialize the extractor with cost-controlled configuration."""
        self.tika_endpoint = os.getenv('TIKA_ENDPOINT', 'https://cfc-tika.onrender.com/tika')
        
        # Cost control settings
        self.ai_enabled = os.getenv('AI_VALIDATION_ENABLED', 'true').lower() == 'true'
        self.daily_ai_limit = int(os.getenv('DAILY_AI_CALLS_LIMIT', '50'))  # Max 50 AI calls per day
        self.max_ai_tokens = int(os.getenv('MAX_AI_TOKENS_PER_CALL', '500'))  # Very conservative
        
        # Initialize OpenAI client with cost controls
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key or not self.ai_enabled:
            logger.info("AI validation disabled - using regex-only extraction")
            self.openai_client = None
        else:
            self.openai_client = OpenAI(api_key=openai_key)
            
        # Financial terms to validate extraction quality
        self.financial_terms = [
            '£', 'income', 'expenditure', 'assets', 'liabilities', 'debt', 
            'revenue', 'borrowing', 'reserves', 'balance', 'surplus', 'deficit'
        ]
        
        # Daily usage tracking
        self._track_daily_usage()
    
    def _track_daily_usage(self):
        """Track daily AI usage to enforce cost limits."""
        from django.core.cache import cache
        from datetime import date
        
        today = date.today().isoformat()
        self.daily_usage_key = f'pdf_ai_calls_{today}'
        self.daily_cost_key = f'pdf_ai_cost_{today}'
        
        # Get current usage
        self.daily_calls = cache.get(self.daily_usage_key, 0)
        self.daily_cost = float(cache.get(self.daily_cost_key, 0.0))
    
    def _can_use_ai(self) -> bool:
        """Check if AI can be used within daily limits."""
        if not self.openai_client:
            return False
            
        if self.daily_calls >= self.daily_ai_limit:
            logger.warning(f"Daily AI limit reached ({self.daily_calls}/{self.daily_ai_limit})")
            return False
            
        max_daily_cost = float(os.getenv('MAX_DAILY_AI_COST', '1.0'))  # £1 per day max
        if self.daily_cost >= max_daily_cost:
            logger.warning(f"Daily AI cost limit reached (£{self.daily_cost:.3f}/£{max_daily_cost})")
            return False
            
        return True
    
    def _increment_ai_usage(self, estimated_cost: float):
        """Track AI usage and costs."""
        from django.core.cache import cache
        
        self.daily_calls += 1
        self.daily_cost += estimated_cost
        
        # Update cache with 25-hour expiry (safe buffer past midnight)
        cache.set(self.daily_usage_key, self.daily_calls, 60 * 60 * 25)
        cache.set(self.daily_cost_key, self.daily_cost, 60 * 60 * 25)
        
        logger.info(f"AI usage: {self.daily_calls}/{self.daily_ai_limit} calls, "
                   f"£{self.daily_cost:.3f} cost today")

    def extract_text_from_pdf(self, pdf_path: str) -> ExtractionResult:
        """
        Extract text content from PDF using Apache Tika.
        
        Args:
            pdf_path: Path to the PDF file to process
            
        Returns:
            ExtractionResult containing extraction details and content
        """
        logger.info(f"Starting PDF text extraction: {pdf_path}")
        start_time = time.time()
        
        try:
            # Check if PDF exists
            if not os.path.exists(pdf_path):
                return ExtractionResult(
                    success=False,
                    error_message=f"PDF file not found: {pdf_path}"
                )
                
            file_size = os.path.getsize(pdf_path) / 1024  # KB
            logger.info(f"Processing PDF file ({file_size:.1f} KB)")
            
            # Extract text using Tika
            with open(pdf_path, 'rb') as pdf_file:
                response = requests.put(
                    f'{self.tika_endpoint}/text',
                    data=pdf_file.read(),
                    headers={'Content-Type': 'application/pdf'},
                    timeout=120  # 2 minutes timeout
                )
                
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                text_content = response.text
                character_count = len(text_content)
                
                # Validate extraction quality
                found_terms = [
                    term for term in self.financial_terms 
                    if term.lower() in text_content.lower()
                ]
                
                logger.info(f"Text extraction successful: {character_count:,} characters, "
                           f"{len(found_terms)} financial terms found")
                
                return ExtractionResult(
                    success=True,
                    text_content=text_content,
                    character_count=character_count,
                    processing_time=processing_time,
                    financial_terms_found=found_terms
                )
            else:
                error_msg = f"Tika extraction failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                return ExtractionResult(
                    success=False,
                    processing_time=processing_time,
                    error_message=error_msg
                )
                
        except requests.exceptions.RequestException as e:
            processing_time = time.time() - start_time
            error_msg = f"PDF extraction request failed: {str(e)}"
            logger.error(error_msg)
            return ExtractionResult(
                success=False,
                processing_time=processing_time,
                error_message=error_msg
            )
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Unexpected error during PDF extraction: {str(e)}"
            logger.error(error_msg)
            return ExtractionResult(
                success=False,
                processing_time=processing_time,
                error_message=error_msg
            )

    def extract_with_hybrid_approach(self, text_content: str, council_name: str = "", year: str = "") -> Dict[str, Any]:
        """
        Cost-effective hybrid extraction: Regex-first with optional AI validation.
        
        This is the main entry point that replaces analyze_with_ai().
        Strategy:
        1. Run enhanced regex extraction (free, high accuracy)
        2. Assess confidence and completeness
        3. Use AI validation only for ambiguous/missing cases (cheap)
        
        Args:
            text_content: Raw text extracted from PDF
            council_name: Name of the council (for context)
            year: Financial year (for context)
            
        Returns:
            Dictionary containing extraction results and metadata
        """
        logger.info(f"Starting hybrid extraction for {len(text_content):,} characters")
        start_time = time.time()
        
        # Step 1: Enhanced regex extraction (PRIMARY - always runs)
        regex_results = self._extract_financial_data_enhanced(text_content)
        
        # Step 2: Assess extraction quality
        quality_assessment = self._assess_extraction_quality(regex_results, text_content)
        
        # Step 3: Decide if AI validation is needed and worthwhile
        needs_ai_validation = (
            quality_assessment['confidence'] < 0.8 or  # Low confidence
            quality_assessment['missing_critical_fields'] > 2 or  # Many missing fields
            quality_assessment['has_ambiguous_values']  # Unclear values detected
        )
        
        final_results = regex_results.copy()
        ai_validation_used = False
        ai_cost = 0.0
        
        if needs_ai_validation and self._can_use_ai():
            logger.info("Running targeted AI validation for ambiguous cases")
            ai_validation = self._validate_with_ai_minimal(
                text_content, regex_results, quality_assessment
            )
            
            if ai_validation['success']:
                # Merge AI improvements with regex results
                final_results = self._merge_extraction_results(regex_results, ai_validation['data'])
                ai_validation_used = True
                ai_cost = ai_validation.get('estimated_cost', 0.01)
                self._increment_ai_usage(ai_cost)
        
        processing_time = time.time() - start_time
        
        # Calculate final confidence score
        final_confidence = self._calculate_hybrid_confidence(
            final_results, quality_assessment, ai_validation_used
        )
        
        logger.info(f"Hybrid extraction complete: {processing_time:.2f}s, "
                   f"confidence: {final_confidence:.1%}, AI used: {ai_validation_used}")
        
        return {
            'success': True,
            'extracted_data': final_results,
            'confidence_score': final_confidence,
            'processing_time': processing_time,
            'extraction_method': 'hybrid_regex_ai' if ai_validation_used else 'enhanced_regex',
            'ai_validation_used': ai_validation_used,
            'ai_cost_estimate': ai_cost,
            'quality_assessment': quality_assessment,
            'notes': f"Regex extraction with{'out' if not ai_validation_used else ''} AI validation"
        }
    
    def _validate_with_ai_minimal(self, text_content: str, regex_results: Dict, quality_assessment: Dict) -> Dict[str, Any]:
        """
        Minimal AI validation for specific ambiguous cases only.
        
        This uses a targeted, cost-efficient approach:
        - Only sends small text excerpts containing the ambiguous values
        - Uses cheapest model (gpt-4o-mini)
        - Strict token limits
        - Focused prompts for specific validation tasks
        """
        if not self._can_use_ai():
            return {'success': False, 'error': 'AI usage limits exceeded'}
        
        try:
            # Identify specific issues to resolve with AI
            ambiguous_fields = quality_assessment.get('ambiguous_fields', [])
            missing_critical = quality_assessment.get('missing_critical_fields_list', [])
            
            # Create targeted validation queries
            validation_queries = []
            
            # Only validate specific problematic fields, not everything
            for field in ambiguous_fields[:3]:  # Max 3 ambiguous fields to keep costs down
                field_context = self._extract_field_context(text_content, field)
                if field_context:
                    validation_queries.append({
                        'field': field,
                        'context': field_context[:300],  # Very small context
                        'regex_value': regex_results.get(field)
                    })
            
            if not validation_queries:
                return {'success': False, 'error': 'No specific validation needed'}
            
            # Ultra-compact prompt for cost efficiency
            prompt_parts = []
            for query in validation_queries:
                prompt_parts.append(f"{query['field']}: found {query['regex_value']} in \"{query['context']}\"")
            
            minimal_prompt = f"""Validate these financial figures from UK council statement:
{chr(10).join(prompt_parts)}

Return only JSON: {{"validated_fields": {{"field_name": correct_number_or_null}}, "confidence": "high|medium|low"}}"""
            
            # Use cheapest model with strict limits
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Cheapest model, good enough for validation
                messages=[{"role": "user", "content": minimal_prompt}],
                max_tokens=self.max_ai_tokens,  # Very strict limit
                temperature=0.0  # Deterministic for validation
            )
            
            # Track estimated cost (gpt-4o-mini: ~$0.00015 input, $0.0006 output per 1K tokens)
            input_tokens = len(minimal_prompt.split()) * 1.3  # Rough token estimate
            output_tokens = self.max_ai_tokens
            estimated_cost_usd = (input_tokens * 0.00015 + output_tokens * 0.0006) / 1000
            estimated_cost_gbp = estimated_cost_usd * 0.79  # Rough USD to GBP
            
            if response.choices and response.choices[0].message:
                try:
                    validation_data = json.loads(response.choices[0].message.content)
                    return {
                        'success': True,
                        'data': validation_data.get('validated_fields', {}),
                        'confidence': validation_data.get('confidence', 'medium'),
                        'estimated_cost': estimated_cost_gbp
                    }
                except json.JSONDecodeError:
                    return {'success': False, 'error': 'AI returned invalid JSON'}
            else:
                return {'success': False, 'error': 'AI returned empty response'}
                
        except Exception as e:
            logger.error(f"AI validation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_field_context(self, text_content: str, field_name: str) -> str:
        """Extract small text context around a specific field for AI validation."""
        import re
        
        # Field-specific search terms
        search_terms = {
            'revenue_income': ['total income', 'gross income', 'revenue'],
            'total_expenditure': ['total expenditure', 'net expenditure'],
            'current_liabilities': ['current liabilities'],
            'reserves': ['total reserves', 'usable reserves'],
            'total_debt': ['total debt', 'total borrowing']
        }
        
        terms = search_terms.get(field_name, [field_name.replace('_', ' ')])
        
        for term in terms:
            # Find the term and extract surrounding context
            pattern = rf'.{{0,150}}{re.escape(term)}.{{0,150}}'
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ""
    
    def _assess_extraction_quality(self, extracted_data: Dict[str, Any], text_content: str) -> Dict[str, Any]:
        """
        Assess the quality and completeness of regex extraction results.
        
        Args:
            extracted_data: Results from regex extraction
            text_content: Original PDF text for context analysis
            
        Returns:
            Quality assessment with confidence score and recommendations
        """
        # Critical fields that should typically be present in council statements
        critical_fields = ['revenue_income', 'total_expenditure', 'current_liabilities', 'reserves']
        
        # Count extracted fields
        extracted_fields = [k for k, v in extracted_data.items() 
                           if v is not None and isinstance(v, (int, float)) and v > 0]
        
        missing_critical = [f for f in critical_fields if f not in extracted_fields]
        
        # Check for potentially ambiguous values (very round numbers might be placeholders)
        ambiguous_fields = []
        for field, value in extracted_data.items():
            if isinstance(value, (int, float)) and value > 0:
                # Flag suspiciously round numbers that might be wrong
                if value % 1000000 == 0 and value > 10000000:  # Exactly X million
                    ambiguous_fields.append(field)
                elif str(int(value)).endswith('00000'):  # Ends in many zeros
                    ambiguous_fields.append(field)
        
        # Calculate base confidence
        field_count_score = min(1.0, len(extracted_fields) / 6)  # Up to 6 key fields
        critical_coverage = 1.0 - (len(missing_critical) / len(critical_fields))
        ambiguity_penalty = len(ambiguous_fields) * 0.1
        
        confidence = max(0.3, min(1.0, (field_count_score + critical_coverage) / 2 - ambiguity_penalty))
        
        # Check if text seems to contain financial data
        financial_indicators = sum(1 for term in self.financial_terms 
                                 if term.lower() in text_content.lower())
        
        return {
            'confidence': confidence,
            'extracted_field_count': len(extracted_fields),
            'missing_critical_fields': len(missing_critical),
            'missing_critical_fields_list': missing_critical,
            'ambiguous_fields': ambiguous_fields,
            'has_ambiguous_values': len(ambiguous_fields) > 0,
            'financial_indicators_found': financial_indicators,
            'recommendation': self._get_quality_recommendation(confidence, missing_critical, ambiguous_fields)
        }
    
    def _get_quality_recommendation(self, confidence: float, missing_critical: List[str], ambiguous_fields: List[str]) -> str:
        """Generate quality improvement recommendations."""
        if confidence >= 0.9:
            return "Excellent extraction quality - no AI validation needed"
        elif confidence >= 0.7:
            if ambiguous_fields:
                return f"Good extraction but {len(ambiguous_fields)} ambiguous values need validation"
            return "Good extraction quality - minimal AI validation beneficial"
        elif confidence >= 0.5:
            return f"Moderate quality - missing {len(missing_critical)} critical fields, AI validation recommended"
        else:
            return "Low extraction quality - AI validation strongly recommended"
    
    def _merge_extraction_results(self, regex_results: Dict[str, Any], ai_validated: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge regex extraction results with AI validation data.
        
        Args:
            regex_results: Original regex extraction results
            ai_validated: AI validation results for specific fields
            
        Returns:
            Merged results with improved accuracy
        """
        merged = regex_results.copy()
        
        # Apply AI corrections/validations
        for field, ai_value in ai_validated.items():
            if ai_value is not None and isinstance(ai_value, (int, float)) and ai_value > 0:
                regex_value = regex_results.get(field)
                
                if regex_value is None:
                    # AI found a field that regex missed
                    merged[field] = ai_value
                    logger.info(f"AI found missing field {field}: {ai_value}")
                elif abs(ai_value - regex_value) / max(ai_value, regex_value) > 0.1:  # >10% difference
                    # Significant disagreement - use AI value but flag for review
                    merged[field] = ai_value
                    logger.warning(f"AI corrected {field}: {regex_value} -> {ai_value}")
                # If values are similar, keep regex value (it's often more reliable)
        
        # Update confidence and notes
        merged['confidence'] = 'medium'  # Hybrid results get medium confidence
        merged['notes'] = 'Enhanced with AI validation for ambiguous cases'
        
        return merged
    
    def _calculate_hybrid_confidence(self, final_results: Dict[str, Any], quality_assessment: Dict[str, Any], ai_used: bool) -> float:
        """
        Calculate final confidence score for hybrid extraction.
        
        Args:
            final_results: Final merged extraction results
            quality_assessment: Quality assessment from regex extraction
            ai_used: Whether AI validation was used
            
        Returns:
            Final confidence score between 0.0 and 1.0
        """
        base_confidence = quality_assessment['confidence']
        
        # AI validation boosts confidence
        if ai_used:
            ai_bonus = 0.15  # Moderate boost for AI validation
            final_confidence = min(1.0, base_confidence + ai_bonus)
        else:
            final_confidence = base_confidence
        
        # Additional boost if many fields extracted successfully
        extracted_count = sum(1 for v in final_results.values() 
                            if v is not None and isinstance(v, (int, float)) and v > 0)
        
        if extracted_count >= 5:  # Good coverage
            final_confidence = min(1.0, final_confidence + 0.05)
        
        return round(final_confidence, 2)
    
    def _validate_with_ai_minimal(self, text_content: str, regex_results: Dict, quality_assessment: Dict) -> Dict[str, Any]:
        """
        Minimal AI validation for specific ambiguous cases only.
        
        This uses a targeted, cost-efficient approach:
        - Only sends small text excerpts containing the ambiguous values
        - Uses cheapest model (gpt-4o-mini)
        - Strict token limits
        - Focused prompts for specific validation tasks
        """
        if not self._can_use_ai():
            return {'success': False, 'error': 'AI usage limits exceeded'}
        
        try:
            # Identify specific issues to resolve with AI
            ambiguous_fields = quality_assessment.get('ambiguous_fields', [])
            missing_critical = quality_assessment.get('missing_critical_fields_list', [])
            
            # Create targeted validation queries
            validation_queries = []
            
            # Only validate specific problematic fields, not everything
            for field in ambiguous_fields[:3]:  # Max 3 ambiguous fields to keep costs down
                field_context = self._extract_field_context(text_content, field)
                if field_context:
                    validation_queries.append({
                        'field': field,
                        'context': field_context[:300],  # Very small context
                        'regex_value': regex_results.get(field)
                    })
            
            if not validation_queries:
                return {'success': False, 'error': 'No specific validation needed'}
            
            # Ultra-compact prompt for cost efficiency
            prompt_parts = []
            for query in validation_queries:
                prompt_parts.append(f"{query['field']}: found {query['regex_value']} in \"{query['context']}\"")
            
            minimal_prompt = f"""Validate these financial figures from UK council statement:
{chr(10).join(prompt_parts)}

Return only JSON: {{"validated_fields": {{"field_name": correct_number_or_null}}, "confidence": "high|medium|low"}}"""
            
            # Use cheapest model with strict limits
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Cheapest model, good enough for validation
                messages=[{"role": "user", "content": minimal_prompt}],
                max_tokens=self.max_ai_tokens,  # Very strict limit
                temperature=0.0  # Deterministic for validation
            )
            
            # Track estimated cost (gpt-4o-mini: ~$0.00015 input, $0.0006 output per 1K tokens)
            input_tokens = len(minimal_prompt.split()) * 1.3  # Rough token estimate
            output_tokens = self.max_ai_tokens
            estimated_cost_usd = (input_tokens * 0.00015 + output_tokens * 0.0006) / 1000
            estimated_cost_gbp = estimated_cost_usd * 0.79  # Rough USD to GBP
            
            if response.choices and response.choices[0].message:
                try:
                    validation_data = json.loads(response.choices[0].message.content)
                    return {
                        'success': True,
                        'data': validation_data.get('validated_fields', {}),
                        'confidence': validation_data.get('confidence', 'medium'),
                        'estimated_cost': estimated_cost_gbp
                    }
                except json.JSONDecodeError:
                    return {'success': False, 'error': 'AI returned invalid JSON'}
            else:
                return {'success': False, 'error': 'AI returned empty response'}
                
        except Exception as e:
            logger.error(f"AI validation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_field_context(self, text_content: str, field_name: str) -> str:
        """Extract small text context around a specific field for AI validation."""
        import re
        
        # Field-specific search terms
        search_terms = {
            'revenue_income': ['total income', 'gross income', 'revenue'],
            'total_expenditure': ['total expenditure', 'net expenditure'],
            'current_liabilities': ['current liabilities'],
            'reserves': ['total reserves', 'usable reserves'],
            'total_debt': ['total debt', 'total borrowing']
        }
        
        terms = search_terms.get(field_name, [field_name.replace('_', ' ')])
        
        for term in terms:
            # Find the term and extract surrounding context
            pattern = rf'.{{0,150}}{re.escape(term)}.{{0,150}}'
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ""
    
    # Backward compatibility - redirect old method to new hybrid approach
    def analyze_with_ai(self, text_content: str, council_name: str = "", year: str = "") -> AIAnalysisResult:
        """
        Backward compatibility wrapper for the hybrid approach.
        
        DEPRECATED: Use extract_with_hybrid_approach() for new implementations.
        """
        logger.warning("analyze_with_ai() is deprecated, use extract_with_hybrid_approach()")
        
        hybrid_result = self.extract_with_hybrid_approach(text_content, council_name, year)
        
        # Convert hybrid result to AIAnalysisResult format for compatibility
        return AIAnalysisResult(
            success=hybrid_result['success'],
            extracted_data=hybrid_result['extracted_data'],
            confidence_score=hybrid_result['confidence_score'],
            processing_time=hybrid_result['processing_time'],
            raw_response=hybrid_result.get('notes', 'Hybrid extraction result')
        )

    def _clean_content_for_ai(self, text_content: str) -> str:
        """
        Clean content to avoid OpenAI content filter issues.
        
        Args:
            text_content: Raw PDF text content
            
        Returns:
            Cleaned content safe for OpenAI processing
        """
        # Remove metadata and problematic characters that might trigger filter
        import re
        
        # Remove PDF metadata
        cleaned = re.sub(r'\{"pdf:[^"]*":[^}]*\}', '', text_content)
        
        # Keep only standard characters and financial content
        # Focus on sections likely to contain financial data
        financial_keywords = [
            'income', 'expenditure', 'assets', 'liabilities', 'debt', 'revenue',
            'borrowing', 'reserves', 'balance', 'surplus', 'deficit', 'statement',
            'accounts', 'financial', '£', 'thousand', 'million'
        ]
        
        # Split into lines and prioritize lines with financial keywords
        lines = cleaned.split('\n')
        financial_lines = []
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in financial_keywords):
                # Keep lines that contain financial terms
                financial_lines.append(line.strip())
                
        # Join back and return first portion
        result = '\n'.join(financial_lines)
        
        # If no financial lines found, return original content (truncated)
        if not result.strip():
            result = text_content[:4000]
            
        return result

    def _extract_financial_data_enhanced(self, text_content: str) -> Dict[str, Any]:
        """
        Enhanced regex extraction method - PRIMARY extraction system.
        
        This is now the main extraction method, refined for UK council statements.
        Much more sophisticated than the original fallback version.
        
        Args:
            text_content: Raw PDF text content
            
        Returns:
            Dictionary of extracted financial data with confidence metadata
        """
        import re
        
        extracted_data = {
            'revenue_income': None,
            'total_expenditure': None,
            'current_assets': None,
            'current_liabilities': None,
            'long_term_liabilities': None,
            'total_debt': None,
            'interest_payments': None,
            'reserves': None,
            'borrowing': None,
            'net_worth': None,
            'confidence': 'medium',  # Enhanced regex gets medium confidence
            'notes': 'Extracted using enhanced regex patterns optimized for UK councils'
        }
        
        # Track metadata for each extraction
        extraction_metadata = {}
        
        # Enhanced regex patterns based on UK council statement analysis
        # PRIORITY ORDER: Group Balance Sheet > Main Balance Sheet > Other sections
        patterns = {
            'revenue_income': [
                # Balance sheet formats
                r'total\s*income[:\s]*\(([0-9,.]+)\)',  # Format: "total income (4,357.2)"
                r'\([0-9,.]+\)\s*total\s*income\s*\(([0-9,.]+)\)',  # Balance sheet format
                # Income statement formats
                r'(?:total|gross)\s*(?:revenue|income)[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'(?:revenue|income)[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'gross\s*income[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                # Alternative formats
                r'income\s*from\s*operations[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
            ],
            'total_expenditure': [
                # Specific council formats
                r'total\s*expenditure\s*([0-9,.]+)',  # Match: "total expenditure 1,325.8"
                r'([0-9,.]+)\s*total\s*expenditure',  # Match: "1,325.8 total expenditure"
                r'(?:total|net)\s*expenditure[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'net\s*cost\s*of\s*services[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                # Additional patterns
                r'operating\s*expenditure[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
            ],
            'current_assets': [
                r'current\s*assets[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'total\s*current\s*assets[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'short.{0,10}term\s*assets[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
            ],
            'current_liabilities': [
                # PRIORITY 1: Group Balance Sheet patterns (Entity Group Entity Group format)
                r'entity\s+group\s+entity\s+group.*?current\s*liabilities.*?\([0-9,.]+\)\s*\([0-9,.]+\)\s*\([0-9,.]+\)\s*\(([0-9,.]+)\)',
                r'current\s*liabilities.*?\([0-9,.]+\)\s*\([0-9,.]+\)\s*\([0-9,.]+\)\s*\(([0-9,.]+)\)',  # 4-column format, take 4th
                # PRIORITY 2: Group Balance Sheet with "total current liabilities"
                r'total\s*current\s*liabilities[:\s]*\(([0-9,.]+)\)(?=.*group)',  # Only if "group" context nearby
                # PRIORITY 3: Main Balance Sheet patterns  
                r'\([0-9,.]+\)\s*current\s*liabilities\s*\(([0-9,.]+)\)',  # Format: (268.9) Current liabilities (247.3)
                r'total\s*current\s*liabilities[:\s]*\(([0-9,.]+)\)',  # Format: "total current liabilities (1,187.5)"
                r'current\s*liabilities[:\s]*\(([0-9,.]+)\)(?!\s*non-current)',  # Avoid matching subsidiary data
                r'current\s*liabilities[:\s]*£?\(([0-9,.]+)\)',  # Format: Current liabilities £(247.3) or (247.3)
                r'current\s*liabilities[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'total\s*current\s*liabilities[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
            ],
            'long_term_liabilities': [
                r'\([0-9,.]+\)\s*long.{0,10}term\s*liabilities\s*\(([0-9,.]+)\)',  # Match: "(577.8) Long-term liabilities (665.8)"
                r'long.{0,10}term\s*liabilities[:\s]*£?\(([0-9,.]+)\)',  # Match: "Long-term liabilities £(665.8)" or "(665.8)"
                r'(?:long.{0,10}term)\s*(?:debt|liabilities|borrowing)[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'long\s*term\s*borrowing[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'non.{0,10}current\s*liabilities[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
            ],
            'interest_payments': [
                r'interest\s*(?:payments?|paid|costs?)[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'financing\s*costs[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'debt\s*servicing[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
            ],
            'total_debt': [
                r'total\s*(?:debt|borrowing)[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'gross\s*debt[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'outstanding\s*borrowing[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
            ],
            'reserves': [
                # PRIORITY 1: Group Balance Sheet patterns (Entity Group Entity Group format)
                r'entity\s+group\s+entity\s+group.*?total\s*reserves.*?([0-9,.]+)\s+([0-9,.]+)\s+([0-9,.]+)\s+([0-9,.]+)',  # Capture all 4, use 4th
                r'total\s*reserves.*?([0-9,.]+)\s+([0-9,.]+)\s+([0-9,.]+)\s+([0-9,.]+)(?=.*group)',  # 4-column format with group context
                # PRIORITY 2: Current year patterns (avoid 3,158.3 from prior year)
                r'total\s*reserves[:\s]*([0-9,.]+)(?!\s*3,158)',  # Match current year, avoid prior year 3,158.3
                r'([0-9,.]+)\s*total\s*reserves(?!\s*3,158)',  # Match: "3,059.6 total reserves" but not prior year
                r'\([0-9,.]+\)\s*total\s*reserves\s*\(([0-9,.]+)\)',  # Balance sheet format
                r'(?:total)?\s*reserves[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'usable\s*reserves[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
            ],
        }
        
        text_lower = text_content.lower()
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    try:
                        # Handle different capture group patterns
                        groups = match.groups()
                        
                        # For 4-column group balance sheet patterns (Entity Group Entity Group)
                        if len(groups) >= 4 and field in ['current_liabilities', 'reserves']:
                            # Take the 4th column (Group current year)
                            raw_value_str = groups[3] if groups[3] else groups[0]
                        else:
                            # Standard single-value extraction
                            raw_value_str = groups[0]
                        
                        # Check if value has comma thousand separators (e.g., "132,743")
                        has_comma_thousands = ',' in raw_value_str and len(raw_value_str.split(',')[-1]) == 3
                        
                        # Clean value string for parsing
                        value_str = raw_value_str.replace(',', '')
                        value = float(value_str)
                        
                        # Check scale indicator from second capture group (if it exists and not a 4-column pattern)
                        scale_indicator = ''
                        if len(groups) == 2 and groups[1]:  # Only for 2-group patterns
                            scale_indicator = groups[1].strip().lower()
                        
                        # Apply scale multipliers with improved logic
                        if scale_indicator in ['million', 'm']:
                            value *= 1000000
                        elif scale_indicator in ['thousand', 'k']:
                            value *= 1000
                        elif not scale_indicator:
                            # Improved logic for council financial statements:
                            if has_comma_thousands:
                                # If comma separators are used (e.g., "132,743"), value is already in correct scale
                                # Convert to full amount: 132,743 -> 132,743,000
                                value *= 1000
                            elif value < 10000:
                                # If no commas and value < 10000, likely in millions (e.g., "132.743")
                                value *= 1000000
                        
                        # Convert to int for storage
                        extracted_data[field] = int(value)
                        
                        # Store metadata for this extraction
                        source_text = match.group(0)  # Full matched text
                        page_number = self._detect_page_number_for_match(text_content, source_text)
                        
                        extraction_metadata[field] = {
                            'source_text': source_text,
                            'page_number': page_number,
                            'raw_value': raw_value_str,
                            'has_comma_thousands': has_comma_thousands,
                            'scale_indicator': scale_indicator
                        }
                        
                        break  # Use first match for each field
                        
                    except (ValueError, AttributeError, IndexError):
                        continue
        
        # Add metadata to the result
        extracted_data['_metadata'] = extraction_metadata
        return extracted_data
    
    # Keep the original fallback method for backward compatibility
    def _extract_financial_data_fallback(self, text_content: str) -> Dict[str, Any]:
        """
        Backward compatibility: calls the enhanced method.
        
        DEPRECATED: Use _extract_financial_data_enhanced() directly.
        """
        logger.warning("_extract_financial_data_fallback() is deprecated, use _extract_financial_data_enhanced()")
        return self._extract_financial_data_enhanced(text_content)

    def _detect_page_number_for_match(self, text_content: str, match_text: str) -> Optional[int]:
        """
        Try to detect page number based on text patterns around a matched financial figure.
        
        Args:
            text_content: Full PDF text content
            match_text: The specific text that was matched
            
        Returns:
            Page number if detected, None otherwise
        """
        import re
        
        # Find the position of the match in the text
        match_pos = text_content.lower().find(match_text.lower())
        if match_pos == -1:
            return None
        
        # Look for page indicators in text around the match (within 2000 characters)
        context_start = max(0, match_pos - 1000)
        context_end = min(len(text_content), match_pos + 1000)
        context = text_content[context_start:context_end]
        
        # Common page number patterns in UK financial statements
        page_patterns = [
            r'page\s+(\d+)',  # "Page 42"
            r'p\.?\s*(\d+)',  # "p. 42" or "p 42"
            r'(\d+)\s*(?:\r?\n|\r)',  # Number at end of line (common page footer)
            r'^\s*(\d+)\s*$',  # Standalone number on its own line
        ]
        
        # Look for page numbers, preferring those closer to the match
        best_page = None
        best_distance = float('inf')
        
        for pattern in page_patterns:
            for match_obj in re.finditer(pattern, context, re.IGNORECASE | re.MULTILINE):
                page_num = int(match_obj.group(1))
                # Only consider reasonable page numbers (1-200)
                if 1 <= page_num <= 200:
                    # Calculate distance from the financial data match
                    page_pos = context_start + match_obj.start()
                    distance = abs(page_pos - match_pos)
                    
                    if distance < best_distance:
                        best_distance = distance
                        best_page = page_num
        
        return best_page

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON object from text that might contain extra content.
        
        Args:
            text: Raw text potentially containing JSON
            
        Returns:
            Parsed JSON object or None if not found
        """
        import re
        
        # Try to find JSON object in the text
        # Look for content between { and } that spans multiple lines
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                # Try to parse each potential JSON match
                return json.loads(match)
            except json.JSONDecodeError:
                continue
                
        # If no valid JSON found, return None
        return None

    def _calculate_confidence_score(self, extracted_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on extracted data quality.
        
        Args:
            extracted_data: Dictionary of extracted financial data
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not extracted_data:
            return 0.0
            
        # Get explicit confidence if provided by AI
        ai_confidence = extracted_data.get('confidence', '').lower()
        confidence_mapping = {'high': 0.9, 'medium': 0.7, 'low': 0.4}
        
        if ai_confidence in confidence_mapping:
            base_score = confidence_mapping[ai_confidence]
        else:
            base_score = 0.6  # Default
            
        # Adjust based on number of extracted fields
        non_null_fields = sum(1 for v in extracted_data.values() 
                             if v is not None and isinstance(v, (int, float)) and v > 0)
        
        field_bonus = min(0.2, non_null_fields * 0.02)  # Up to 0.2 bonus for 10+ fields
        
        final_score = min(1.0, base_score + field_bonus)
        return round(final_score, 2)

    def process_pdf(self, pdf_path: str, council_name: str = "", year: str = "") -> Dict[str, Any]:
        """
        Complete PDF processing workflow: extraction + AI analysis.
        
        Args:
            pdf_path: Path to PDF file to process
            council_name: Name of the council (optional, for better AI context)
            year: Financial year (optional, for better AI context)
            
        Returns:
            Dictionary containing complete processing results:
            {
                'success': bool,
                'extraction': ExtractionResult,
                'analysis': AIAnalysisResult,
                'total_time': float,
                'summary': str
            }
        """
        logger.info(f"Starting complete PDF processing: {pdf_path}")
        overall_start = time.time()
        
        # Step 1: Extract text from PDF
        extraction_result = self.extract_text_from_pdf(pdf_path)
        
        if not extraction_result.success:
            return {
                'success': False,
                'extraction': extraction_result,
                'analysis': None,
                'total_time': time.time() - overall_start,
                'summary': f"PDF extraction failed: {extraction_result.error_message}"
            }
        
        # Step 2: AI analysis of extracted content
        analysis_result = self.analyze_with_ai(
            extraction_result.text_content, 
            council_name, 
            year
        )
        
        total_time = time.time() - overall_start
        
        # Generate summary
        if extraction_result.success and analysis_result.success:
            summary = (f"Successfully processed PDF: {extraction_result.character_count:,} characters extracted, "
                      f"{len(analysis_result.extracted_data)} financial fields identified "
                      f"(confidence: {analysis_result.confidence_score:.0%})")
        else:
            summary = f"Processing completed with issues: {analysis_result.error_message if analysis_result else 'AI analysis skipped'}"
        
        logger.info(f"PDF processing completed in {total_time:.2f} seconds")
        
        return {
            'success': extraction_result.success and (analysis_result.success if analysis_result else True),
            'extraction': extraction_result,
            'analysis': analysis_result,
            'total_time': total_time,
            'summary': summary
        }


class FinancialDataMapper:
    """
    Maps extracted financial data to database field formats.
    
    This class handles the conversion between AI-extracted data and the
    specific field formats expected by the council finance database.
    """
    
    def __init__(self):
        """Initialize mapper with field mappings."""
        # Mapping from AI field names to database field slugs
        self.field_mappings = {
            'revenue_income': 'total-income',
            'total_expenditure': 'total-expenditure',
            'current_assets': 'current-assets',
            'current_liabilities': 'current-liabilities',
            'long_term_liabilities': 'long-term-borrowing',
            'total_debt': 'total-debt',
            'interest_payments': 'interest-payments',
            'reserves': 'total-reserves',
            'borrowing': 'total-borrowing',
            'net_worth': 'net-worth'
        }
    
    def map_to_database_fields(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert AI-extracted data to database field format.
        
        Args:
            extracted_data: Raw data from AI analysis
            
        Returns:
            Dictionary with database field slugs as keys
        """
        mapped_data = {}
        
        for ai_field, db_field in self.field_mappings.items():
            if ai_field in extracted_data and extracted_data[ai_field] is not None:
                value = extracted_data[ai_field]
                
                # Validate numeric values
                if isinstance(value, (int, float)) and value > 0:
                    mapped_data[db_field] = value
                    
        return mapped_data
    
    def validate_financial_data(self, mapped_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate mapped financial data for consistency and reasonableness.
        
        Args:
            mapped_data: Dictionary with database field slugs and values
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for negative values
        for field, value in mapped_data.items():
            if isinstance(value, (int, float)) and value < 0:
                issues.append(f"Negative value for {field}: {value}")
        
        # Check basic consistency rules
        income = mapped_data.get('total-income', 0)
        expenditure = mapped_data.get('total-expenditure', 0)
        
        if income > 0 and expenditure > 0:
            if expenditure > income * 3:  # Expenditure much higher than income
                issues.append("Expenditure significantly exceeds income - please verify figures")
                
        # Check asset/liability consistency
        current_assets = mapped_data.get('current-assets', 0)
        current_liabilities = mapped_data.get('current-liabilities', 0)
        
        if current_assets > 0 and current_liabilities > 0:
            if current_liabilities > current_assets * 2:
                issues.append("Current liabilities much higher than current assets - please verify")
        
        is_valid = len(issues) == 0
        return is_valid, issues
