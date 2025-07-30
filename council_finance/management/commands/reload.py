"""
Management command to reload the development server with cache clearing.
"""
import os
import subprocess
import sys
import time
import json
from datetime import datetime
from io import StringIO

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Reload development server with cache clearing (cfc-reload equivalent)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            default='8000',
            help='Port to run the development server on (default: 8000)',
        )
        parser.add_argument(
            '--no-checks',
            action='store_true',
            help='Skip Django checks before starting server',
        )
        parser.add_argument(
            '--validate',
            action='store_true',
            help='Run comprehensive validation checks and log errors to syntax_errors.log',
        )
        parser.add_argument(
            '--no-tests',
            action='store_true',
            help='Skip comprehensive test suite (tests run by default)',
        )
        parser.add_argument(
            '--test-only',
            action='store_true',
            help='Only run tests, do not start the server',
        )

    def handle(self, *args, **options):
        # Determine number of steps
        total_steps = 5  # Always include tests by default
        if options['validate']:
            total_steps += 1
        if options['no_tests']:
            total_steps -= 1
        if options['test_only']:
            total_steps -= 1  # Don't start server
        
        self.stdout.write(
            self.style.SUCCESS('Council Finance Counters - Development Reload')
        )
        self.stdout.write('=' * 45)
        self.stdout.write('')

        # Step 1: Stop existing servers (unless test-only)
        step_num = 1
        if not options['test_only']:
            self.stdout.write(f'[{step_num}/{total_steps}] Stopping Django server...')
            self._stop_existing_servers()
            step_num += 1

            # Step 2: Clear caches and rebuild frontend
            self.stdout.write(f'[{step_num}/{total_steps}] Clearing caches and rebuilding frontend...')
            try:
                call_command('clear_dev_cache', verbosity=0)
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Cache clearing failed: {e}')
                )
            
            # Rebuild React components with cache busting
            self._rebuild_frontend_with_cache_busting()
            step_num += 1

        # Step N: Run comprehensive test suite (unless skipped)
        if not options['no_tests']:
            self.stdout.write(f'[{step_num}/{total_steps}] Running comprehensive test suite...')
            test_success = self._run_comprehensive_tests()
            
            if not test_success:
                self.stdout.write(
                    self.style.ERROR('Comprehensive tests failed! Check syntax_errors.log for details.')
                )
                if not options['test_only']:
                    self.stdout.write(
                        self.style.WARNING('Continuing with server start despite test failures...')
                    )
                else:
                    return
            else:
                self.stdout.write(
                    self.style.SUCCESS('All comprehensive tests passed!')
                )
            step_num += 1

        # Step N: Run validation checks (if requested)
        if options['validate']:
            self.stdout.write(f'[{step_num}/{total_steps}] Running comprehensive validation...')
            validation_errors = self._run_comprehensive_validation()
            
            if validation_errors:
                self.stdout.write(
                    self.style.WARNING(f'Found {validation_errors} validation issue(s). Check syntax_errors.log for details.')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('All validation checks passed!')
                )
            step_num += 1

        # Step N: Run Django checks (unless skipped or test-only)
        if not options['no_checks'] and not options['test_only']:
            self.stdout.write(f'[{step_num}/{total_steps}] Running Django checks...')
            try:
                call_command('check', verbosity=1)
            except SystemExit as e:
                if e.code != 0:
                    self.stdout.write('')
                    self.stdout.write(
                        self.style.ERROR('Django checks failed! Please fix the errors above.')
                    )
                    return
            step_num += 1
        elif not options['test_only']:
            self.stdout.write(f'[{step_num}/{total_steps}] Skipping Django checks...')
            step_num += 1

        # Final step: Start server (unless test-only)
        if not options['test_only']:
            self.stdout.write(f'[{total_steps}/{total_steps}] Starting development server...')
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS('>> CFC development server starting...')
            )
            self.stdout.write(f'   Navigate to: http://127.0.0.1:{options["port"]}/')
            self.stdout.write('   Press Ctrl+C to stop')
            self.stdout.write('')

            # Start the development server
            try:
                call_command('runserver', options['port'])
            except KeyboardInterrupt:
                self.stdout.write('')
                self.stdout.write('Development server stopped.')
        else:
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS('Test-only mode complete. Server not started.')
            )

    def _rebuild_frontend_with_cache_busting(self):
        """Rebuild React frontend with cache busting and template updates."""
        try:
            # Step 1: Rebuild React components
            self.stdout.write('   > Rebuilding React components...')
            
            # Check if frontend directory exists
            frontend_dir = os.path.join(os.getcwd(), 'frontend')
            if not os.path.exists(frontend_dir):
                self.stdout.write(
                    self.style.WARNING('Frontend directory not found, skipping React rebuild')
                )
                return
            
            # Run npm build in frontend directory
            build_result = subprocess.run([
                'npm', 'run', 'build'
            ], cwd=frontend_dir, capture_output=True, text=True, timeout=120)
            
            if build_result.returncode != 0:
                self.stdout.write(
                    self.style.WARNING(f'React build failed: {build_result.stderr}')
                )
                return
            
            # Step 2: Extract new build filenames from Vite manifest
            self.stdout.write('   > Updating template references with cache busting...')
            self._update_template_build_references()
            
            self.stdout.write('   > Frontend rebuild completed successfully')
            
        except subprocess.TimeoutExpired:
            self.stdout.write(
                self.style.WARNING('React build timed out after 2 minutes')
            )
        except FileNotFoundError:
            self.stdout.write(
                self.style.WARNING('npm not found, skipping React rebuild')
            )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Frontend rebuild failed: {e}')
            )

    def _update_template_build_references(self):
        """Update template references to use new build files with cache busting."""
        try:
            import glob
            import re
            
            # Find the new build files
            static_frontend_dir = os.path.join(os.getcwd(), 'static', 'frontend')
            if not os.path.exists(static_frontend_dir):
                return
            
            # Get the latest main JS and CSS files
            js_files = glob.glob(os.path.join(static_frontend_dir, 'main-*.js'))
            css_files = glob.glob(os.path.join(static_frontend_dir, 'main-*.css'))
            
            if not js_files or not css_files:
                self.stdout.write('   ! No build files found to update')
                return
            
            # Get the newest files (in case multiple exist)
            latest_js = max(js_files, key=os.path.getctime) if js_files else None
            latest_css = max(css_files, key=os.path.getctime) if css_files else None
            
            if latest_js:
                latest_js_name = os.path.basename(latest_js)
            if latest_css:
                latest_css_name = os.path.basename(latest_css)
            
            # Update my_lists_enhanced.html template
            template_path = os.path.join(
                os.getcwd(), 
                'council_finance', 
                'templates', 
                'council_finance', 
                'my_lists_enhanced.html'
            )
            
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Update JS reference
                if latest_js:
                    js_pattern = r'src="{% static \'frontend/main-[^\']+\.js\' %}"'
                    js_replacement = f'src="{{{{ static \'frontend/{latest_js_name}\' }}}}?v={{{{ \'now\'|date:\'U\' }}}}"'
                    content = re.sub(js_pattern, js_replacement, content)
                
                # Update CSS reference  
                if latest_css:
                    css_pattern = r'href="{% static \'frontend/main-[^\']+\.css\' %}"'
                    css_replacement = f'href="{{{{ static \'frontend/{latest_css_name}\' }}}}?v={{{{ \'now\'|date:\'U\' }}}}"'
                    content = re.sub(css_pattern, css_replacement, content)
                
                # Write back the updated template
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.stdout.write(f'   > Updated template with {latest_js_name} and {latest_css_name}')
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Template update failed: {e}')
            )

    def _stop_existing_servers(self):
        """Stop any existing Django development servers."""
        try:
            if os.name == 'nt':  # Windows
                # Use more targeted approach - look for runserver processes specifically
                result = subprocess.run([
                    'powershell', '-Command', 
                    'Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like "*manage.py*runserver*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }'
                ], capture_output=True, check=False, timeout=5)
                
                # Also try taskkill as backup
                subprocess.run([
                    'taskkill', '/F', '/FI', 'WINDOWTITLE eq *runserver*'
                ], capture_output=True, check=False, timeout=3)
                
            else:  # Unix-like
                subprocess.run([
                    'pkill', '-f', 'python.*manage.py.*runserver'
                ], capture_output=True, check=False, timeout=5)
            
            # Give processes time to stop
            time.sleep(0.5)
            
        except subprocess.TimeoutExpired:
            self.stdout.write(
                self.style.WARNING('Server stop command timed out - continuing anyway')
            )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not stop existing servers: {e}')
            )

    def _run_comprehensive_validation(self):
        """Run comprehensive validation checks and log errors to file."""
        errors = []
        log_entries = []
        
        # Initialize log
        log_entries.append({
            'timestamp': datetime.now().isoformat(),
            'validation_type': 'comprehensive_reload_validation',
            'checks_performed': []
        })
        
        # 1. JavaScript Template Validation
        self.stdout.write('   > Validating JavaScript in templates...')
        js_errors = self._validate_javascript_templates()
        if js_errors:
            errors.extend(js_errors)
            log_entries.append({
                'check': 'javascript_templates',
                'status': 'failed',
                'errors': js_errors,
                'description': 'JavaScript syntax validation in Django templates'
            })
        else:
            log_entries.append({
                'check': 'javascript_templates',
                'status': 'passed',
                'description': 'JavaScript syntax validation in Django templates'
            })

        # 2. Python Syntax Validation
        self.stdout.write('   > Validating Python syntax...')
        python_errors = self._validate_python_syntax()
        if python_errors:
            errors.extend(python_errors)
            log_entries.append({
                'check': 'python_syntax',
                'status': 'failed',
                'errors': python_errors,
                'description': 'Python syntax validation for .py files'
            })
        else:
            log_entries.append({
                'check': 'python_syntax',
                'status': 'passed',
                'description': 'Python syntax validation for .py files'
            })

        # 3. Template Syntax Validation
        self.stdout.write('   > Validating Django template syntax...')
        template_errors = self._validate_template_syntax()
        if template_errors:
            errors.extend(template_errors)
            log_entries.append({
                'check': 'template_syntax',
                'status': 'failed',
                'errors': template_errors,
                'description': 'Django template syntax validation'
            })
        else:
            log_entries.append({
                'check': 'template_syntax',
                'status': 'passed',
                'description': 'Django template syntax validation'
            })

        # 4. CSS/SCSS Validation (if applicable)
        self.stdout.write('   > Validating CSS/SCSS syntax...')
        css_errors = self._validate_css_syntax()
        if css_errors:
            errors.extend(css_errors)
            log_entries.append({
                'check': 'css_syntax',
                'status': 'failed',
                'errors': css_errors,
                'description': 'CSS/SCSS syntax validation'
            })
        else:
            log_entries.append({
                'check': 'css_syntax',
                'status': 'passed',
                'description': 'CSS/SCSS syntax validation'
            })

        # 5. JSON Configuration Validation
        self.stdout.write('   > Validating JSON configuration files...')
        json_errors = self._validate_json_files()
        if json_errors:
            errors.extend(json_errors)
            log_entries.append({
                'check': 'json_files',
                'status': 'failed',
                'errors': json_errors,
                'description': 'JSON configuration file validation'
            })
        else:
            log_entries.append({
                'check': 'json_files',
                'status': 'passed',
                'description': 'JSON configuration file validation'
            })

        # Write log file
        self._write_validation_log(log_entries, errors)
        
        return len(errors)

    def _validate_javascript_templates(self):
        """Validate JavaScript syntax in Django templates."""
        errors = []
        
        try:
            # Capture output from the validate_template_javascript command
            out = StringIO()
            err = StringIO()
            
            # Run the JavaScript validation command
            call_command('validate_template_javascript', stdout=out, stderr=err)
            
            output = out.getvalue()
            error_output = err.getvalue()
            
            # Parse output for errors
            if 'FAIL' in output or error_output:
                lines = output.split('\n') + error_output.split('\n')
                for line in lines:
                    if 'FAIL' in line or 'ERROR' in line or line.strip().startswith('- '):
                        errors.append({
                            'type': 'javascript_template_error',
                            'message': line.strip(),
                            'file': self._extract_filename_from_error(line),
                            'severity': 'error'
                        })
                        
        except Exception as e:
            errors.append({
                'type': 'validation_command_error',
                'message': f'JavaScript template validation failed: {str(e)}',
                'file': 'validation_system',
                'severity': 'warning'
            })
        
        return errors

    def _validate_python_syntax(self):
        """Validate Python syntax in all .py files."""
        errors = []
        
        try:
            import ast
            import glob
            
            # Find all Python files
            python_files = []
            for pattern in ['**/*.py', 'council_finance/**/*.py', 'core/**/*.py']:
                python_files.extend(glob.glob(pattern, recursive=True))
            
            # Remove duplicates and filter out venv/node_modules
            python_files = list(set(python_files))
            python_files = [f for f in python_files if 'venv' not in f and 'node_modules' not in f]
            
            for file_path in python_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse with AST
                    ast.parse(content)
                    
                except SyntaxError as e:
                    errors.append({
                        'type': 'python_syntax_error',
                        'message': f'Line {e.lineno}: {e.msg}',
                        'file': file_path,
                        'line': e.lineno,
                        'severity': 'error'
                    })
                except Exception as e:
                    # Skip files that can't be read or parsed for other reasons
                    if 'codec' not in str(e).lower():
                        errors.append({
                            'type': 'python_file_error',
                            'message': f'Could not validate: {str(e)}',
                            'file': file_path,
                            'severity': 'warning'
                        })
                        
        except Exception as e:
            errors.append({
                'type': 'python_validation_error',
                'message': f'Python syntax validation failed: {str(e)}',
                'file': 'validation_system',
                'severity': 'warning'
            })
        
        return errors

    def _validate_template_syntax(self):
        """Validate Django template syntax."""
        errors = []
        
        try:
            import glob
            from django.template import Template, TemplateSyntaxError, Context
            from django.template.loader import get_template
            
            # Find all template files
            template_files = []
            for pattern in ['**/*.html', 'templates/**/*.html', 'council_finance/templates/**/*.html']:
                template_files.extend(glob.glob(pattern, recursive=True))
            
            template_files = list(set(template_files))
            
            for file_path in template_files:
                try:
                    # Try to load template through Django's loader
                    relative_path = file_path
                    if 'templates/' in file_path:
                        relative_path = file_path.split('templates/', 1)[1]
                    
                    get_template(relative_path)
                    
                except TemplateSyntaxError as e:
                    errors.append({
                        'type': 'template_syntax_error',
                        'message': str(e),
                        'file': file_path,
                        'severity': 'error'
                    })
                except Exception as e:
                    # Template not found or other issues - this is often expected
                    if 'not found' not in str(e).lower():
                        errors.append({
                            'type': 'template_validation_warning',
                            'message': f'Could not validate template: {str(e)}',
                            'file': file_path,
                            'severity': 'warning'
                        })
                        
        except Exception as e:
            errors.append({
                'type': 'template_validation_error',
                'message': f'Template syntax validation failed: {str(e)}',
                'file': 'validation_system',
                'severity': 'warning'
            })
        
        return errors

    def _validate_css_syntax(self):
        """Validate CSS/SCSS syntax (basic validation)."""
        errors = []
        
        try:
            import glob
            
            # Find CSS files
            css_files = []
            for pattern in ['**/*.css', '**/*.scss', 'static/**/*.css', 'static/**/*.scss']:
                css_files.extend(glob.glob(pattern, recursive=True))
            
            css_files = [f for f in list(set(css_files)) if 'node_modules' not in f]
            
            for file_path in css_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Basic CSS validation - check for obvious syntax errors
                    open_braces = content.count('{')
                    close_braces = content.count('}')
                    
                    if open_braces != close_braces:
                        errors.append({
                            'type': 'css_syntax_error',
                            'message': f'Unbalanced braces: {open_braces} opening, {close_braces} closing',
                            'file': file_path,
                            'severity': 'error'
                        })
                        
                except Exception as e:
                    if 'codec' not in str(e).lower():
                        errors.append({
                            'type': 'css_file_error',
                            'message': f'Could not validate: {str(e)}',
                            'file': file_path,
                            'severity': 'warning'
                        })
                        
        except Exception as e:
            errors.append({
                'type': 'css_validation_error',
                'message': f'CSS validation failed: {str(e)}',
                'file': 'validation_system',
                'severity': 'warning'
            })
        
        return errors

    def _validate_json_files(self):
        """Validate JSON configuration files."""
        errors = []
        
        try:
            import glob
            
            # Find JSON files
            json_files = []
            for pattern in ['*.json', '**/*.json']:
                json_files.extend(glob.glob(pattern, recursive=True))
            
            json_files = [f for f in list(set(json_files)) if 'node_modules' not in f]
            
            for file_path in json_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                        
                except json.JSONDecodeError as e:
                    errors.append({
                        'type': 'json_syntax_error',
                        'message': f'Line {e.lineno}: {e.msg}',
                        'file': file_path,
                        'line': e.lineno,
                        'severity': 'error'
                    })
                except Exception as e:
                    if 'codec' not in str(e).lower():
                        errors.append({
                            'type': 'json_file_error',
                            'message': f'Could not validate: {str(e)}',
                            'file': file_path,
                            'severity': 'warning'
                        })
                        
        except Exception as e:
            errors.append({
                'type': 'json_validation_error',
                'message': f'JSON validation failed: {str(e)}',
                'file': 'validation_system',
                'severity': 'warning'
            })
        
        return errors

    def _run_comprehensive_tests(self):
        """Run the comprehensive test suite from run_all_tests.py and log failures to syntax_errors.log."""
        try:
            import sys
            import subprocess
            import os
            import json
            
            # Get the path to run_all_tests.py
            test_script_path = os.path.join(os.getcwd(), 'run_all_tests.py')
            
            if not os.path.exists(test_script_path):
                self.stdout.write(
                    self.style.ERROR('run_all_tests.py not found in project root')
                )
                self._write_test_error_to_log('run_all_tests.py not found in project root')
                return False
            
            # Run the comprehensive test suite
            try:
                result = subprocess.run([
                    sys.executable, test_script_path
                ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
                
                # Print condensed output from the test suite
                if result.stdout:
                    lines = result.stdout.split('\n')
                    # Show key summary lines, not every single test
                    for line in lines:
                        if any(keyword in line for keyword in ['SUMMARY', 'FAILED', 'ERROR', 'SUCCESS', '='*20]):
                            if line.strip():
                                self.stdout.write(f'   {line}')
                
                # Log errors to syntax_errors.log if tests failed
                if result.returncode != 0:
                    self._write_test_failures_to_log(result.stdout, result.stderr)
                
                # Return success based on exit code
                return result.returncode == 0
                
            except subprocess.TimeoutExpired:
                error_msg = 'Comprehensive test suite timed out after 5 minutes'
                self.stdout.write(self.style.ERROR(error_msg))
                self._write_test_error_to_log(error_msg)
                return False
                
        except Exception as e:
            error_msg = f'Failed to run comprehensive test suite: {e}'
            self.stdout.write(self.style.ERROR(error_msg))
            self._write_test_error_to_log(error_msg)
            return False

    def _write_test_failures_to_log(self, stdout_output, stderr_output):
        """Write test failures to syntax_errors.log, overwriting the file."""
        log_file_path = os.path.join(os.getcwd(), 'syntax_errors.log')
        
        try:
            with open(log_file_path, 'w', encoding='utf-8') as f:
                f.write("COUNCIL FINANCE COUNTERS - COMPREHENSIVE TEST FAILURES\n")
                f.write("=" * 65 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("Source: Django reload command comprehensive testing\n\n")
                
                f.write("❌ COMPREHENSIVE TESTS FAILED\n")
                f.write("The following issues were detected during testing:\n\n")
                
                # Write test output
                if stdout_output:
                    f.write("TEST OUTPUT:\n")
                    f.write("-" * 40 + "\n")
                    f.write(stdout_output)
                    f.write("\n\n")
                
                if stderr_output:
                    f.write("ERROR OUTPUT:\n")
                    f.write("-" * 40 + "\n")
                    f.write(stderr_output)
                    f.write("\n\n")
                
                # Also check if test_report.json exists and include key errors
                test_report_path = os.path.join(os.getcwd(), 'test_report.json')
                if os.path.exists(test_report_path):
                    try:
                        with open(test_report_path, 'r') as report_file:
                            report_data = json.load(report_file)
                            
                        if 'errors' in report_data and report_data['errors']:
                            f.write("DETAILED ERROR ANALYSIS:\n")
                            f.write("-" * 40 + "\n")
                            for i, error in enumerate(report_data['errors'][:10], 1):  # Limit to 10 errors
                                f.write(f"{i}. {error}\n")
                            
                            if len(report_data['errors']) > 10:
                                f.write(f"... and {len(report_data['errors']) - 10} more errors\n")
                            f.write("\n")
                        
                        if 'warnings' in report_data and report_data['warnings']:
                            f.write("WARNINGS:\n")
                            f.write("-" * 40 + "\n")
                            for i, warning in enumerate(report_data['warnings'][:5], 1):  # Limit to 5 warnings
                                f.write(f"{i}. {warning}\n")
                            f.write("\n")
                            
                    except Exception:
                        f.write("Could not parse test_report.json for detailed errors\n\n")
                
                f.write("RECOMMENDED ACTIONS:\n")
                f.write("-" * 40 + "\n")
                f.write("1. Run 'python run_all_tests.py -v' for full detailed output\n")
                f.write("2. Fix the errors identified above\n")
                f.write("3. Run 'python manage.py reload --test-only' to verify fixes\n")
                f.write("4. Use 'python manage.py reload --no-tests' to skip tests temporarily\n")
                
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not write test failures to syntax_errors.log: {e}')
            )

    def _write_test_error_to_log(self, error_message):
        """Write a single test error to syntax_errors.log."""
        log_file_path = os.path.join(os.getcwd(), 'syntax_errors.log')
        
        try:
            with open(log_file_path, 'w', encoding='utf-8') as f:
                f.write("COUNCIL FINANCE COUNTERS - TEST EXECUTION ERROR\n")
                f.write("=" * 60 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Error: {error_message}\n\n")
                f.write("The comprehensive test suite could not be executed.\n")
                f.write("Please check the error above and ensure run_all_tests.py is available.\n")
        except Exception:
            pass  # Silent fail if we can't write the log

    def _extract_filename_from_error(self, error_line):
        """Extract filename from error message."""
        if ':' in error_line:
            parts = error_line.split(':')
            for part in parts:
                if '.html' in part or '.py' in part or '.js' in part:
                    return part.strip()
        return 'unknown'

    def _write_validation_log(self, log_entries, errors):
        """Write validation results to log file in AI-friendly format."""
        log_file_path = os.path.join(os.getcwd(), 'syntax_errors.log')
        
        try:
            with open(log_file_path, 'w', encoding='utf-8') as f:
                f.write("COUNCIL FINANCE COUNTERS - SYNTAX VALIDATION LOG\n")
                f.write("=" * 60 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total errors found: {len(errors)}\n\n")
                
                if not errors:
                    f.write("🎉 NO SYNTAX ERRORS FOUND! All validation checks passed.\n\n")
                else:
                    f.write("❌ SYNTAX ERRORS FOUND - Copy and paste the sections below to AI tools for fixing:\n\n")
                
                # Group errors by type and file for easier AI processing
                errors_by_file = {}
                for error in errors:
                    file_key = error.get('file', 'unknown')
                    if file_key not in errors_by_file:
                        errors_by_file[file_key] = []
                    errors_by_file[file_key].append(error)
                
                # Write errors in AI-friendly format
                for file_path, file_errors in errors_by_file.items():
                    f.write(f"\n" + "─" * 60 + "\n")
                    f.write(f"FILE: {file_path}\n")
                    f.write(f"ERROR COUNT: {len(file_errors)}\n")
                    f.write("─" * 60 + "\n")
                    
                    for i, error in enumerate(file_errors, 1):
                        f.write(f"\nERROR #{i}:\n")
                        f.write(f"Type: {error.get('type', 'unknown')}\n")
                        f.write(f"Severity: {error.get('severity', 'unknown')}\n")
                        if 'line' in error:
                            f.write(f"Line: {error['line']}\n")
                        f.write(f"Message: {error.get('message', 'No message')}\n")
                        
                        # Add instructions for AI
                        f.write("\nAI INSTRUCTIONS:\n")
                        f.write(f"Please fix the {error.get('type', 'syntax error')} in file '{file_path}'.\n")
                        if 'line' in error:
                            f.write(f"The error is on line {error['line']}.\n")
                        f.write(f"Error details: {error.get('message', 'No message')}\n")
                        f.write("Please provide the corrected code.\n")
                
                # Summary for AI
                f.write(f"\n" + "=" * 60 + "\n")
                f.write("SUMMARY FOR AI TOOLS:\n")
                f.write("=" * 60 + "\n")
                f.write(f"Total files with errors: {len(errors_by_file)}\n")
                f.write(f"Total errors: {len(errors)}\n")
                f.write("\nError types found:\n")
                
                error_types = {}
                for error in errors:
                    error_type = error.get('type', 'unknown')
                    error_types[error_type] = error_types.get(error_type, 0) + 1
                
                for error_type, count in error_types.items():
                    f.write(f"- {error_type}: {count} error(s)\n")
                
                f.write("\nInstructions:\n")
                f.write("1. Copy each file section above to your AI tool\n")
                f.write("2. Ask the AI to fix the syntax errors\n")
                f.write("3. Apply the fixes to your codebase\n")
                f.write("4. Run 'python manage.py reload --validate' again to verify fixes\n")
                
                # Detailed check results
                f.write(f"\n" + "=" * 60 + "\n")
                f.write("DETAILED CHECK RESULTS:\n")
                f.write("=" * 60 + "\n")
                
                for entry in log_entries:
                    if 'check' in entry:
                        status_icon = "✅" if entry['status'] == 'passed' else "❌"
                        f.write(f"{status_icon} {entry['check'].upper()}: {entry['status'].upper()}\n")
                        f.write(f"   Description: {entry.get('description', 'No description')}\n")
                        if entry['status'] == 'failed' and 'errors' in entry:
                            f.write(f"   Error count: {len(entry['errors'])}\n")
                        f.write("\n")
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Could not write validation log: {e}')
            )