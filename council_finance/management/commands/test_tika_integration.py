"""
Django management command for testing Tika PDF extraction integration.

This command provides a comprehensive test suite for validating the Apache Tika
server deployment and PDF processing capabilities for the AI Financial Statement
Processing feature.

Usage:
    python manage.py test_tika_integration
    python manage.py test_tika_integration --pdf /path/to/test.pdf
    python manage.py test_tika_integration --verbose --test-openai
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Test Tika PDF extraction integration for AI Financial Statement Processing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pdf',
            type=str,
            help='Path to specific PDF file to test (defaults to docs/pdfs/worcestershire2425.pdf)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output with detailed extraction results',
        )
        parser.add_argument(
            '--test-openai',
            action='store_true',
            help='Also test OpenAI analysis of extracted content (requires OPENAI_API_KEY)',
        )
        parser.add_argument(
            '--save-output',
            action='store_true',
            help='Save extraction results to files for review',
        )

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)
        self.verbose = options.get('verbose', False)
        self.test_openai = options.get('test_openai', False)
        self.save_output = options.get('save_output', False)

        # Set default PDF path
        pdf_path = options.get('pdf') or 'docs/pdfs/worcestershire2425.pdf'

        self.stdout.write(
            self.style.SUCCESS('Tika PDF Processing Integration Test Suite')
        )
        self.stdout.write('=' * 60)

        # Run test suite
        try:
            self.test_environment_setup()
            self.test_tika_server_connection()
            self.test_pdf_extraction(pdf_path)
            
            if self.test_openai:
                self.test_openai_integration()
                
            self.stdout.write(
                self.style.SUCCESS('\nAll tests completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\nTest suite failed: {str(e)}')
            )
            sys.exit(1)

    def test_environment_setup(self):
        """Test that required environment variables and configurations are present."""
        self.stdout.write('\nTesting Environment Setup...')
        
        # Check for Tika endpoint
        tika_endpoint = os.getenv('TIKA_ENDPOINT')
        if not tika_endpoint:
            raise CommandError('TIKA_ENDPOINT environment variable not set')
            
        self.stdout.write(f'   [OK] Tika endpoint configured: {tika_endpoint}')
        
        # Check for OpenAI key if OpenAI testing is requested
        if self.test_openai:
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                raise CommandError('OPENAI_API_KEY required for --test-openai option')
            self.stdout.write(f'   [OK] OpenAI API key configured: {openai_key[:12]}...')

    def test_tika_server_connection(self):
        """Test connection to the Tika server."""
        self.stdout.write('\nTesting Tika Server Connection...')
        
        tika_endpoint = os.getenv('TIKA_ENDPOINT')
        
        try:
            # Test basic server health
            response = requests.get(f'{tika_endpoint}', timeout=30)
            
            if response.status_code == 200:
                self.stdout.write('   [OK] Tika server is responding')
                
                # Test version endpoint if available
                try:
                    version_response = requests.get(f'{tika_endpoint}/version', timeout=10)
                    if version_response.status_code == 200:
                        self.stdout.write(f'   [OK] Tika version: {version_response.text.strip()}')
                except:
                    self.stdout.write('   [WARN] Version endpoint not accessible (normal for some setups)')
                    
                # Test parsers endpoint
                try:
                    parsers_response = requests.get(f'{tika_endpoint}/parsers', timeout=10)
                    if parsers_response.status_code == 200:
                        self.stdout.write('   [OK] Parser list accessible')
                        if self.verbose:
                            parsers = parsers_response.json()
                            pdf_parsers = [p for p in parsers if 'pdf' in p.get('name', '').lower()]
                            self.stdout.write(f'      Found {len(pdf_parsers)} PDF parsers')
                except:
                    self.stdout.write('   [WARN] Parsers endpoint not accessible')
                    
            else:
                raise CommandError(f'Tika server returned status {response.status_code}')
                
        except requests.exceptions.RequestException as e:
            raise CommandError(f'Failed to connect to Tika server: {str(e)}')

    def test_pdf_extraction(self, pdf_path):
        """Test PDF text extraction with the specified file."""
        self.stdout.write(f'\nTesting PDF Extraction with {pdf_path}...')
        
        # Check if PDF file exists
        full_pdf_path = os.path.join(os.getcwd(), pdf_path)
        if not os.path.exists(full_pdf_path):
            raise CommandError(f'PDF file not found: {full_pdf_path}')
            
        file_size = os.path.getsize(full_pdf_path) / 1024  # KB
        self.stdout.write(f'   [OK] PDF file found ({file_size:.1f} KB)')
        
        tika_endpoint = os.getenv('TIKA_ENDPOINT')
        
        try:
            # Extract text using Tika
            start_time = time.time()
            
            with open(full_pdf_path, 'rb') as pdf_file:
                # Use Tika's text extraction endpoint
                response = requests.put(
                    f'{tika_endpoint}/text',
                    data=pdf_file.read(),
                    headers={'Content-Type': 'application/pdf'},
                    timeout=120  # 2 minutes timeout for large PDFs
                )
                
            extraction_time = time.time() - start_time
            
            if response.status_code == 200:
                extracted_text = response.text
                text_length = len(extracted_text)
                
                self.stdout.write(f'   [OK] Text extraction successful ({text_length:,} characters)')
                self.stdout.write(f'   [OK] Processing time: {extraction_time:.2f} seconds')
                
                if self.verbose or text_length == 0:
                    # Show sample of extracted text
                    preview = extracted_text[:500].replace('\n', ' ').strip()
                    if preview:
                        self.stdout.write(f'   [INFO] Text preview: "{preview}..."')
                    else:
                        self.stdout.write('   [WARN] No text content extracted (may be image-based PDF)')
                        
                # Basic validation - look for financial terms
                financial_terms = ['£', 'income', 'expenditure', 'assets', 'liabilities', 'debt', 'revenue']
                found_terms = [term for term in financial_terms if term.lower() in extracted_text.lower()]
                
                if found_terms:
                    self.stdout.write(f'   [OK] Found financial terms: {", ".join(found_terms)}')
                else:
                    self.stdout.write('   [WARN] No obvious financial terms detected')
                    
                # Save output if requested
                if self.save_output:
                    output_file = f'tika_extraction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"PDF File: {pdf_path}\n")
                        f.write(f"Extraction Time: {extraction_time:.2f} seconds\n")
                        f.write(f"Text Length: {text_length:,} characters\n")
                        f.write(f"Found Terms: {', '.join(found_terms)}\n")
                        f.write("-" * 50 + "\n")
                        f.write(extracted_text)
                    self.stdout.write(f'   [OK] Extraction saved to: {output_file}')
                    
                return extracted_text
                
            else:
                raise CommandError(f'Tika extraction failed with status {response.status_code}: {response.text}')
                
        except requests.exceptions.RequestException as e:
            raise CommandError(f'PDF extraction request failed: {str(e)}')

    def test_openai_integration(self):
        """Test OpenAI integration for financial data analysis."""
        self.stdout.write('\nTesting OpenAI Integration...')
        
        try:
            from openai import OpenAI
        except ImportError:
            raise CommandError('OpenAI library not installed. Run: pip install openai')
            
        openai_key = os.getenv('OPENAI_API_KEY')
        client = OpenAI(api_key=openai_key)
        
        # Test with sample financial data
        sample_text = """
        STATEMENT OF ACCOUNTS 2024/25
        
        Revenue Income: £145,230,000
        Total Expenditure: £142,890,000
        Current Assets: £23,450,000
        Current Liabilities: £18,920,000
        Long-term Borrowing: £89,340,000
        Interest Payments: £3,240,000
        """
        
        try:
            start_time = time.time()
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analyst. Extract key financial figures from council statements and return them as JSON."
                    },
                    {
                        "role": "user", 
                        "content": f"Extract financial data from this text and return as JSON with fields like revenue_income, total_expenditure, current_assets, etc.:\n\n{sample_text}"
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            ai_time = time.time() - start_time
            
            if response.choices and response.choices[0].message:
                result = response.choices[0].message.content
                self.stdout.write(f'   [OK] OpenAI analysis successful ({ai_time:.2f} seconds)')
                
                if self.verbose:
                    self.stdout.write(f'   [INFO] AI Response:\n{result}')
                    
                # Try to parse as JSON
                try:
                    parsed_result = json.loads(result)
                    self.stdout.write(f'   [OK] Response is valid JSON with {len(parsed_result)} fields')
                except:
                    self.stdout.write('   [WARN] Response is not JSON format (may need prompt refinement)')
                    
            else:
                self.stdout.write('   [WARN] OpenAI returned empty response')
                
        except Exception as e:
            raise CommandError(f'OpenAI integration test failed: {str(e)}')

    def style_test_header(self, text):
        """Helper to format test section headers."""
        return self.style.HTTP_INFO(f'\n{text}')