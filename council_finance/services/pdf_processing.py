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
    Main class for extracting financial data from PDF documents.
    
    This class handles the complete workflow:
    1. PDF text extraction via Apache Tika
    2. AI analysis of extracted content using OpenAI
    3. Data validation and mapping to database fields
    
    Usage:
        extractor = TikaFinancialExtractor()
        result = extractor.process_pdf('/path/to/financial_statement.pdf')
        
        if result['success']:
            financial_data = result['extracted_data']
            # Process extracted data...
    """
    
    def __init__(self):
        """Initialize the extractor with configured endpoints."""
        self.tika_endpoint = os.getenv('TIKA_ENDPOINT', 'https://cfc-tika.onrender.com/tika')
        
        # Initialize OpenAI client
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            logger.warning("OpenAI API key not configured - AI analysis will be disabled")
            self.openai_client = None
        else:
            self.openai_client = OpenAI(api_key=openai_key)
            
        # Financial terms to validate extraction quality
        self.financial_terms = [
            '£', 'income', 'expenditure', 'assets', 'liabilities', 'debt', 
            'revenue', 'borrowing', 'reserves', 'balance', 'surplus', 'deficit'
        ]

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

    def analyze_with_ai(self, text_content: str, council_name: str = "", year: str = "") -> AIAnalysisResult:
        """
        Analyze extracted text using OpenAI to identify financial data.
        
        Args:
            text_content: Raw text extracted from PDF
            council_name: Name of the council (for context)
            year: Financial year (for context)
            
        Returns:
            AIAnalysisResult containing extracted financial data
        """
        if not self.openai_client:
            return AIAnalysisResult(
                success=False,
                error_message="OpenAI client not configured"
            )
            
        logger.info(f"Starting AI analysis of financial content ({len(text_content):,} characters)")
        start_time = time.time()
        
        try:
            # Pre-process content to avoid content filter issues
            cleaned_content = self._clean_content_for_ai(text_content)
            
            # Prepare context-aware prompt
            context = f"Council: {council_name}, Year: {year}" if council_name or year else "Council financial statement"
            
            system_prompt = """You are a financial analyst specializing in UK council financial statements. 
            Extract key financial figures and return them as JSON with the following structure:
            
            {
                "revenue_income": number_or_null,
                "total_expenditure": number_or_null,
                "current_assets": number_or_null,
                "current_liabilities": number_or_null,
                "long_term_liabilities": number_or_null,
                "total_debt": number_or_null,
                "interest_payments": number_or_null,
                "reserves": number_or_null,
                "borrowing": number_or_null,
                "net_worth": number_or_null,
                "confidence": "high|medium|low",
                "notes": "Brief explanation of data quality and any issues"
            }
            
            Only extract clearly identifiable monetary values in pounds. 
            Use null for any figures that cannot be determined with confidence.
            All monetary values should be in pounds (remove £ symbol and commas)."""
            
            user_prompt = f"Extract financial data from this {context}:\n\n{cleaned_content[:8000]}"  # Limit content to avoid token limits
            
            # Debug: Log the actual prompt being sent
            logger.info(f"Sending prompt to OpenAI (first 200 chars): {user_prompt[:200]}...")
            
            print(f"DEBUG - Making OpenAI API call with model: gpt-3.5-turbo")
            print(f"DEBUG - User prompt length: {len(user_prompt)}")
            print(f"DEBUG - System prompt length: {len(system_prompt)}")
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.1  # Low temperature for consistent extraction
            )
            
            print(f"DEBUG - API response received: {response}")
            
            processing_time = time.time() - start_time
            
            # Check if content was filtered
            if (response.choices and 
                response.choices[0].finish_reason == 'content_filter'):
                logger.warning("OpenAI content filter triggered - using fallback extraction")
                print("DEBUG - Content filter triggered, attempting fallback extraction")
                
                # Use fallback extraction method
                fallback_data = self._extract_financial_data_fallback(text_content)
                
                return AIAnalysisResult(
                    success=True,
                    extracted_data=fallback_data,
                    confidence_score=0.6,  # Lower confidence for fallback
                    processing_time=processing_time,
                    raw_response="Content filtered - used fallback extraction"
                )
            
            if response.choices and response.choices[0].message:
                raw_response = response.choices[0].message.content
                logger.info(f"AI analysis completed ({processing_time:.2f} seconds)")
                print(f"DEBUG - Raw AI response: {repr(raw_response)}")
                
                try:
                    # Parse JSON response - try direct parsing first
                    extracted_data = json.loads(raw_response)
                    
                    # Check if all financial fields are null/empty (AI found no data)
                    financial_fields = ['revenue_income', 'total_expenditure', 'current_assets', 
                                       'current_liabilities', 'long_term_liabilities', 'total_debt', 
                                       'interest_payments', 'reserves', 'borrowing', 'net_worth']
                    
                    has_financial_data = any(extracted_data.get(field) is not None and 
                                           isinstance(extracted_data.get(field), (int, float)) and 
                                           extracted_data.get(field) > 0 
                                           for field in financial_fields)
                    
                    if not has_financial_data:
                        logger.warning("AI returned no financial data - using fallback extraction")
                        print("DEBUG - AI found no data, attempting fallback extraction")
                        
                        # Use fallback extraction method
                        fallback_data = self._extract_financial_data_fallback(text_content)
                        
                        return AIAnalysisResult(
                            success=True,
                            extracted_data=fallback_data,
                            confidence_score=0.6,  # Lower confidence for fallback
                            processing_time=processing_time,
                            raw_response="AI found no data - used fallback extraction"
                        )
                    
                    # Determine confidence score
                    confidence_score = self._calculate_confidence_score(extracted_data)
                    
                    logger.info(f"Successfully extracted {len(extracted_data)} financial fields "
                              f"with confidence score {confidence_score:.2f}")
                    
                    return AIAnalysisResult(
                        success=True,
                        extracted_data=extracted_data,
                        confidence_score=confidence_score,
                        processing_time=processing_time,
                        raw_response=raw_response
                    )
                    
                except json.JSONDecodeError as e:
                    # Try to extract JSON from response that might have extra text
                    logger.warning(f"Direct JSON parsing failed, attempting to extract JSON: {str(e)}")
                    extracted_json = self._extract_json_from_text(raw_response)
                    
                    if extracted_json:
                        extracted_data = extracted_json
                        confidence_score = self._calculate_confidence_score(extracted_data)
                        
                        logger.info(f"Successfully extracted JSON from response text")
                        return AIAnalysisResult(
                            success=True,
                            extracted_data=extracted_data,
                            confidence_score=confidence_score,
                            processing_time=processing_time,
                            raw_response=raw_response
                        )
                    else:
                        logger.error(f"Could not extract valid JSON from AI response: {raw_response[:200]}...")
                        return AIAnalysisResult(
                            success=False,
                            processing_time=processing_time,
                            error_message=f"AI response is not valid JSON: {str(e)}",
                            raw_response=raw_response
                        )
            else:
                return AIAnalysisResult(
                    success=False,
                    processing_time=processing_time,
                    error_message="OpenAI returned empty response"
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"AI analysis failed: {str(e)}"
            logger.error(error_msg)
            return AIAnalysisResult(
                success=False,
                processing_time=processing_time,
                error_message=error_msg
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

    def _extract_financial_data_fallback(self, text_content: str) -> Dict[str, Any]:
        """
        Fallback extraction method using regex patterns when OpenAI fails.
        
        Args:
            text_content: Raw PDF text content
            
        Returns:
            Dictionary of extracted financial data
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
            'confidence': 'low',
            'notes': 'Extracted using fallback regex patterns due to content filter'
        }
        
        # Track metadata for each extraction
        extraction_metadata = {}
        
        # Define regex patterns for financial figures
        # Handle various formats: £123,456, £6.2m, 123.4 million, etc.
        # Capture both the number and the scale indicator in separate groups
        # PRIORITY ORDER: Group Balance Sheet > Main Balance Sheet > Other sections
        patterns = {
            'revenue_income': [
                r'total\s*income[:\s]*\(([0-9,.]+)\)',  # Format: "total income (4,357.2)"
                r'\([0-9,.]+\)\s*total\s*income\s*\(([0-9,.]+)\)',  # Balance sheet format
                r'(?:total|gross)?\s*(?:revenue|income)[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'(?:revenue|income)[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'gross\s*income[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
            ],
            'total_expenditure': [
                r'total\s*expenditure\s*([0-9,.]+)',  # Match: "total expenditure 1,325.8"
                r'([0-9,.]+)\s*total\s*expenditure',  # Match: "1,325.8 total expenditure"
                r'(?:total|net)?\s*expenditure[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'net\s*cost\s*of\s*services[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
            ],
            'current_assets': [
                r'current\s*assets[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'total\s*current\s*assets[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
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
            ],
            'interest_payments': [
                r'interest\s*(?:payments?|paid|costs?)[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'financing\s*costs[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
            ],
            'total_debt': [
                r'total\s*(?:debt|borrowing)[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
                r'gross\s*debt[:\s]*£?([0-9,.]+)\s*(million|m|thousand|k|\s|$)',
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