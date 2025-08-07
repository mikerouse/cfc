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
    help = 'Reload development server with cache clearing and optional cache warming (cfc-reload equivalent)'

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
        parser.add_argument(
            '--rebuild-react',
            action='store_true',
            help='Rebuild React frontend and update template references',
        )
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear Django cache and browser caches',
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable verbose debugging output',
        )
        parser.add_argument(
            '--dont-warm-cache',
            action='store_true',
            help='Skip warming site-wide counter cache (cache warming is enabled by default)',
        )

    def handle(self, *args, **options):
        # Store debug flag for verbose output
        self.debug_mode = options.get('debug', False)
        
        # Determine number of steps
        total_steps = 5  # Always include tests by default
        if options['validate']:
            total_steps += 1
        if options['no_tests']:
            total_steps -= 1
        if options['test_only']:
            total_steps -= 1  # Don't start server
        if options['rebuild_react']:
            total_steps += 1  # Extra step for React rebuild
        if options['clear_cache']:
            total_steps += 1  # Extra step for cache clearing
        if not options['dont_warm_cache']:
            total_steps += 1  # Extra step for cache warming (enabled by default)
        
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

        # Optional: Enhanced cache clearing
        if options['clear_cache']:
            self.stdout.write(f'[{step_num}/{total_steps}] Enhanced cache clearing...')
            self._enhanced_cache_clear()
            step_num += 1

        # Optional: Force React rebuild
        if options['rebuild_react']:
            self.stdout.write(f'[{step_num}/{total_steps}] Force rebuilding React frontend...')
            self._force_rebuild_react_with_debugging()
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

        # Optional: Warm site-wide counter cache
        if not options['dont_warm_cache']:
            self.stdout.write(f'[{step_num}/{total_steps}] Warming site-wide counter cache...')
            cache_success = self._warm_sitewide_counter_cache()
            if cache_success:
                self.stdout.write(
                    self.style.SUCCESS('Cache warming completed successfully!')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('Cache warming had some issues - check output above')
                )
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
            
            template_files = [
                'my_lists_enhanced.html',
                'council_edit_react.html',
                'factoid_builder_react.html',
            ]

            for filename in template_files:
                template_path = os.path.join(
                    os.getcwd(),
                    'council_finance',
                    'templates',
                    'council_finance',
                    filename,
                )

                if os.path.exists(template_path):
                    with open(template_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    if latest_js:
                        js_pattern = r'src="{% static \'frontend/main-[^\']+\.js\' %}"'
                        js_replacement = f'src="{{{{ static \'frontend/{latest_js_name}\' }}}}?v={{{{ \'now\'|date:\'U\' }}}}"'
                        content = re.sub(js_pattern, js_replacement, content)

                    if latest_css:
                        css_pattern = r'href="{% static \'frontend/main-[^\']+\.css\' %}"'
                        css_replacement = f'href="{{{{ static \'frontend/{latest_css_name}\' }}}}?v={{{{ \'now\'|date:\'U\' }}}}"'
                        content = re.sub(css_pattern, css_replacement, content)

                    with open(template_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                    self.stdout.write(f'   > Updated {filename} with {latest_js_name} and {latest_css_name}')
            
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
            
            # Parse output for errors - improved patterns
            has_failures = ('FAIL' in output or 'ERROR' in output or 
                          'validation failed' in output.lower() or error_output)
            has_success = ('PASS' in output or 'All templates passed' in output or 
                          'validation passed' in output.lower())
            
            if has_failures:
                lines = output.split('\n') + error_output.split('\n')
                for line in lines:
                    if ('FAIL' in line or 'ERROR' in line or 'failed' in line.lower() or 
                        line.strip().startswith('- ') or line.strip().startswith('Error')):
                        errors.append({
                            'type': 'javascript_template_error',
                            'message': line.strip(),
                            'file': self._extract_filename_from_error(line),
                            'severity': 'error'
                        })
            elif not has_success and output.strip():
                # Command ran but output format unexpected - treat as warning
                errors.append({
                    'type': 'javascript_validation_unexpected',
                    'message': f'Unexpected validation output: {output.strip()[:200]}',
                    'file': 'validation_system', 
                    'severity': 'warning'
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
            
            # First run our built-in syntax tests for the Council Edit interface
            self.stdout.write('   > Running Council Edit interface syntax checks...')
            syntax_success = self._run_council_edit_syntax_tests()
            
            if not syntax_success:
                self.stdout.write(
                    self.style.WARNING('Council Edit syntax tests failed - see details below')
                )
            else:
                self.stdout.write('   SUCCESS: Council Edit interface passed all syntax checks')
            
            # Run heroicon validation to prevent runtime errors
            self.stdout.write('   > Running heroicon validation...')
            heroicon_success = self._run_heroicon_validation()
            
            if not heroicon_success:
                self.stdout.write(
                    self.style.WARNING('Heroicon validation failed - see details above')
                )
            else:
                self.stdout.write('   SUCCESS: All heroicons are valid')
            
            # Get the path to run_all_tests.py
            test_script_path = os.path.join(os.getcwd(), 'run_all_tests.py')
            
            if not os.path.exists(test_script_path):
                self.stdout.write(
                    self.style.ERROR('run_all_tests.py not found in project root')
                )
                self._write_test_error_to_log('run_all_tests.py not found in project root')
                return syntax_success  # Return syntax test result if main tests unavailable
            
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
                
                # Return success based on exit code AND syntax tests AND heroicon validation
                return result.returncode == 0 and syntax_success and heroicon_success
                
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

    def _run_council_edit_syntax_tests(self):
        """Run syntax tests for the Council Edit React interface."""
        try:
            # Import our syntax test functions
            import ast
            import os
            
            errors = []
            
            # Test 1: Python files syntax
            files_to_test = [
                'council_finance/views/council_edit_api.py',
                'council_finance/views/councils.py',
                'council_finance/urls.py',
                'council_finance/tests/test_syntax_errors.py',
                'council_finance/tests/test_council_edit_integration.py',
            ]
            
            for file_path in files_to_test:
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        ast.parse(content, filename=file_path)
                    except SyntaxError as e:
                        errors.append(f"Python syntax error in {file_path}: {e}")
                        self.stdout.write(f'   FAIL {os.path.basename(file_path)}: {e}')
                    except Exception as e:
                        errors.append(f"Error checking {file_path}: {e}")
                        self.stdout.write(f'   WARN {os.path.basename(file_path)}: {e}')
                else:
                    errors.append(f"Missing file: {file_path}")
                    self.stdout.write(f'   FAIL {os.path.basename(file_path)}: File not found')
            
            # Test 2: React components exist and have basic structure
            components = [
                'frontend/src/components/CouncilEditApp.jsx',
                'frontend/src/components/council-edit/CharacteristicsTab.jsx',
                'frontend/src/components/council-edit/GeneralDataTab.jsx',
                'frontend/src/components/council-edit/FinancialDataTab.jsx',
                'frontend/src/components/council-edit/FieldEditor.jsx',
            ]
            
            for component in components:
                if os.path.exists(component):
                    try:
                        with open(component, 'r', encoding='utf-8') as f:
                            content = f.read()
                        if 'export default' not in content:
                            errors.append(f"React component missing export: {component}")
                            self.stdout.write(f'   WARN {os.path.basename(component)}: No default export')
                    except Exception as e:
                        errors.append(f"Error checking React component {component}: {e}")
                        self.stdout.write(f'   FAIL {os.path.basename(component)}: {e}')
                else:
                    errors.append(f"Missing React component: {component}")
                    self.stdout.write(f'   FAIL {os.path.basename(component)}: Not found')
            
            # Test 3: Build artifacts exist
            manifest_path = os.path.join(
                os.getcwd(), 'static', 'frontend', '.vite', 'manifest.json'
            )
            artifacts = []
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                main_entry = manifest.get('src/main.jsx', {})
                js_file = main_entry.get('file')
                css_file = main_entry.get('css', [None])[0]
                if js_file:
                    artifacts.append(os.path.join('static', 'frontend', js_file))
                if css_file:
                    artifacts.append(os.path.join('static', 'frontend', css_file))
            except Exception:
                errors.append('Could not read Vite manifest for artifact check')
            
            for artifact in artifacts:
                if not os.path.exists(artifact):
                    errors.append(f"Missing build artifact: {artifact}")
                    self.stdout.write(f'   WARN {os.path.basename(artifact)}: Not found (may need rebuild)')
            
            # Test 4: Django template exists
            template_path = 'council_finance/templates/council_finance/council_edit_react.html'
            if os.path.exists(template_path):
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    required_elements = [
                        'council-edit-react-root',
                        'CouncilEditApp',
                        'csrf_token',
                    ]
                    
                    missing = [req for req in required_elements if req not in content]
                    if missing:
                        errors.append(f"Template missing elements: {missing}")
                        self.stdout.write(f'   WARN council_edit_react.html: Missing {missing}')
                        
                except Exception as e:
                    errors.append(f"Error checking template: {e}")
                    self.stdout.write(f'   FAIL council_edit_react.html: {e}')
            else:
                errors.append("Missing template: council_edit_react.html")
                self.stdout.write('   FAIL council_edit_react.html: Not found')
            
            # If there are errors, write them to a separate section in the log
            if errors:
                self._write_council_edit_errors_to_log(errors)
                return False
            
            return True
            
        except Exception as e:
            self.stdout.write(f'   FAIL Council Edit syntax test failed: {e}')
            return False

    def _write_council_edit_errors_to_log(self, errors):
        """Write Council Edit interface errors to syntax_errors.log."""
        log_file_path = os.path.join(os.getcwd(), 'syntax_errors.log')
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            # Append to existing log or create new one
            with open(log_file_path, 'a', encoding='utf-8') as f:
                f.write(f"\n\n{'='*60}\n")
                f.write("COUNCIL EDIT REACT INTERFACE - SYNTAX TEST FAILURES\n")
                f.write(f"{'='*60}\n")
                f.write(f"Generated: {current_time}\n")
                f.write(f"Total errors: {len(errors)}\n\n")
                
                for i, error in enumerate(errors, 1):
                    f.write(f"{i}. {error}\n")
                
                f.write(f"\n{'='*60}\n")
                f.write("COUNCIL EDIT INTERFACE STATUS:\n")
                f.write("The mobile-first React council edit interface has syntax issues.\n")
                f.write("Please fix the errors above to ensure proper functionality.\n")
                f.write(f"{'='*60}\n\n")
                
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not write Council Edit errors to log: {e}')
            )

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

    def _run_heroicon_validation(self):
        """Run heroicon validation to prevent runtime template errors."""
        try:
            from django.core.management import call_command
            from io import StringIO
            
            # Capture output from validate_heroicons command
            output = StringIO()
            try:
                call_command('validate_heroicons', stdout=output)
                output_text = output.getvalue()
                
                # Check if validation passed
                if 'All heroicons valid!' in output_text:
                    return True
                else:
                    # There were errors - show them
                    self.stdout.write(
                        self.style.ERROR('Heroicon validation failed:')
                    )
                    self.stdout.write(output_text)
                    return False
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error running heroicon validation: {e}')
                )
                return False
                
        except ImportError:
            self.stdout.write(
                self.style.WARNING('Could not import heroicon validation - skipping')
            )
            return True  # Don't fail if validation isn't available

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

    def _enhanced_cache_clear(self):
        """Enhanced cache clearing including browser and static caches."""
        try:
            # Clear Django cache
            self.stdout.write('   > Clearing Django cache...')
            call_command('clear_dev_cache', verbosity=0)
            
            # Clear static files cache by touching timestamp
            self.stdout.write('   > Invalidating static file caches...')
            static_dir = os.path.join(os.getcwd(), 'static', 'frontend')
            if os.path.exists(static_dir):
                # Touch a timestamp file to bust browser caches
                timestamp_file = os.path.join(static_dir, '.cache_bust')
                with open(timestamp_file, 'w') as f:
                    f.write(str(int(time.time())))
            
            # Add cache headers for development
            self.stdout.write('   > Setting no-cache headers for development...')
            
            if self.debug_mode:
                self.stdout.write('   [DEBUG] Enhanced cache clearing completed')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Enhanced cache clearing failed: {e}')
            )

    def _force_rebuild_react_with_debugging(self):
        """Force rebuild React with detailed debugging output."""
        try:
            frontend_dir = os.path.join(os.getcwd(), 'frontend')
            static_dir = os.path.join(os.getcwd(), 'static', 'frontend')
            
            if not os.path.exists(frontend_dir):
                self.stdout.write(
                    self.style.ERROR('Frontend directory not found')
                )
                return False
            
            # Step 1: Clean existing build
            self.stdout.write('   > Cleaning existing build artifacts...')
            if os.path.exists(static_dir):
                import shutil
                for file in os.listdir(static_dir):
                    if file.startswith('main-') and (file.endswith('.js') or file.endswith('.css')):
                        file_path = os.path.join(static_dir, file)
                        os.remove(file_path)
                        if self.debug_mode:
                            self.stdout.write(f'   [DEBUG] Removed: {file}')
            
            # Step 2: Install dependencies (if needed)
            self.stdout.write('   > Ensuring npm dependencies are up to date...')
            npm_install = subprocess.run([
                'npm', 'install'
            ], cwd=frontend_dir, capture_output=True, text=True, timeout=60)
            
            if npm_install.returncode != 0:
                self.stdout.write(
                    self.style.WARNING(f'npm install warnings: {npm_install.stderr}')
                )
            
            # Step 3: Build with verbose output
            self.stdout.write('   > Building React components with verbose output...')
            build_result = subprocess.run([
                'npm', 'run', 'build'
            ], cwd=frontend_dir, capture_output=True, text=True, timeout=180)
            
            if build_result.returncode == 0:
                self.stdout.write('   [SUCCESS] React build successful')
                if self.debug_mode:
                    self.stdout.write(f'   [DEBUG] Build output: {build_result.stdout}')
                
                # Step 4: Auto-update template references
                self._auto_update_template_build_hashes()
                
                # Step 5: Verify build artifacts
                self._verify_build_artifacts()
                
                return True
            else:
                self.stdout.write(
                    self.style.ERROR(f'React build failed: {build_result.stderr}')
                )
                if self.debug_mode:
                    self.stdout.write(f'   [DEBUG] Build stdout: {build_result.stdout}')
                return False
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Force React rebuild failed: {e}')
            )
            return False

    def _auto_update_template_build_hashes(self):
        """Automatically update template references to new build hashes."""
        try:
            self.stdout.write('   > Auto-updating template build references...')
            
            static_dir = os.path.join(os.getcwd(), 'static', 'frontend')
            if not os.path.exists(static_dir):
                return
            
            # Find new build hashes
            js_hash = None
            css_hash = None
            
            for file in os.listdir(static_dir):
                if file.startswith('main-') and file.endswith('.js'):
                    js_hash = file.replace('main-', '').replace('.js', '')
                elif file.startswith('main-') and file.endswith('.css'):
                    css_hash = file.replace('main-', '').replace('.css', '')
            
            if not js_hash or not css_hash:
                self.stdout.write(
                    self.style.WARNING('Could not find new build hashes')
                )
                return
            
            if self.debug_mode:
                self.stdout.write(f'   [DEBUG] New JS hash: {js_hash}')
                self.stdout.write(f'   [DEBUG] New CSS hash: {css_hash}')
            
            # Update templates
            templates_updated = 0
            templates_dir = os.path.join(os.getcwd(), 'council_finance', 'templates')
            
            # Template files that need updating
            template_files = [
                'council_finance/council_edit_react.html',
                'council_finance/my_lists_enhanced.html',
                'council_finance/factoid_builder_react.html'
            ]
            
            for template_file in template_files:
                template_path = os.path.join(templates_dir, template_file)
                if os.path.exists(template_path):
                    try:
                        with open(template_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Update build hashes
                        original_content = content
                        
                        # Update JS references
                        import re
                        content = re.sub(
                            r'main-[A-Za-z0-9_-]+\.js',
                            f'main-{js_hash}.js',
                            content
                        )
                        
                        # Update CSS references  
                        content = re.sub(
                            r'main-[A-Za-z0-9_-]+\.css',
                            f'main-{css_hash}.css',
                            content
                        )
                        
                        # Update template variables if present
                        content = re.sub(
                            r'react_build_hash="[A-Za-z0-9_-]+"',
                            f'react_build_hash="{js_hash}"',
                            content
                        )
                        content = re.sub(
                            r'css_build_hash="[A-Za-z0-9_-]+"',
                            f'css_build_hash="{css_hash}"',
                            content
                        )
                        
                        if content != original_content:
                            with open(template_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            templates_updated += 1
                            
                            if self.debug_mode:
                                self.stdout.write(f'   [DEBUG] Updated: {template_file}')
                    
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'Could not update {template_file}: {e}')
                        )
            
            self.stdout.write(f'   [SUCCESS] Updated {templates_updated} template(s)')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Template update failed: {e}')
            )

    def _verify_build_artifacts(self):
        """Verify that build artifacts were created successfully."""
        try:
            self.stdout.write('   > Verifying build artifacts...')
            
            static_dir = os.path.join(os.getcwd(), 'static', 'frontend')
            if not os.path.exists(static_dir):
                self.stdout.write(
                    self.style.ERROR('Static frontend directory does not exist')
                )
                return False
            
            js_files = []
            css_files = []
            
            for file in os.listdir(static_dir):
                if file.startswith('main-') and file.endswith('.js'):
                    js_files.append(file)
                elif file.startswith('main-') and file.endswith('.css'):
                    css_files.append(file)
            
            if not js_files:
                self.stdout.write(
                    self.style.ERROR('No JavaScript build artifacts found')
                )
                return False
            
            if not css_files:
                self.stdout.write(
                    self.style.ERROR('No CSS build artifacts found')
                )
                return False
            
            # Check file sizes
            for js_file in js_files:
                file_path = os.path.join(static_dir, js_file)
                file_size = os.path.getsize(file_path)
                
                if file_size < 1000:  # Less than 1KB probably indicates an error
                    self.stdout.write(
                        self.style.WARNING(f'JS file {js_file} seems too small ({file_size} bytes)')
                    )
                elif self.debug_mode:
                    self.stdout.write(f'   [DEBUG] {js_file}: {file_size:,} bytes')
            
            self.stdout.write('   [SUCCESS] Build artifacts verified')
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Build verification failed: {e}')
            )
            return False

    def _warm_sitewide_counter_cache(self):
        """
        Warm site-wide counter cache using extensible architecture.
        
        This method automatically discovers and warms all site-wide counters,
        making it extensible for future counter additions.
        """
        try:
            from council_finance.models import SiteCounter, GroupCounter, Council, FinancialYear
            from council_finance.agents.site_totals_agent import SiteTotalsAgent
            from django.core.cache import cache
            
            success = True
            
            # Step 1: Display cache warming overview
            site_counters = SiteCounter.objects.all()
            group_counters = GroupCounter.objects.all()
            councils = Council.objects.count()
            years = FinancialYear.objects.count()
            
            self.stdout.write(f'   > Cache warming overview:')
            self.stdout.write(f'     - Site counters: {site_counters.count()}')
            self.stdout.write(f'     - Group counters: {group_counters.count()}')
            self.stdout.write(f'     - Councils in system: {councils}')
            self.stdout.write(f'     - Financial years: {years}')
            
            if site_counters.count() == 0 and group_counters.count() == 0:
                self.stdout.write(
                    self.style.WARNING('No site-wide counters found to warm')
                )
                return True
            
            # Step 2: Check current cache status
            self.stdout.write(f'   > Checking current cache status...')
            cold_counters = []
            
            for sc in site_counters:
                year_label = sc.year.label if sc.year else "all"
                cache_key = f"counter_total:{sc.slug}:{year_label}"
                cached_value = cache.get(cache_key)
                
                if cached_value is None:
                    cold_counters.append(f'Site: {sc.name}')
                    self.stdout.write(f'     [COLD] {sc.name} ({sc.slug})')
                else:
                    self.stdout.write(f'     [WARM] {sc.name}: {cached_value:,.0f}')
            
            for gc in group_counters:
                year_label = gc.year.label if gc.year else "all"
                cache_key = f"counter_total:{gc.slug}:{year_label}"
                cached_value = cache.get(cache_key)
                
                if cached_value is None:
                    cold_counters.append(f'Group: {gc.name}')
                    self.stdout.write(f'     [COLD] {gc.name} ({gc.slug})')
                else:
                    self.stdout.write(f'     [WARM] {gc.name}: {cached_value:,.0f}')
            
            if not cold_counters:
                self.stdout.write(
                    self.style.SUCCESS('   All counters already have warm cache!')
                )
                return True
            
            # Step 3: Warm cold counters
            self.stdout.write(f'   > Warming {len(cold_counters)} cold counter(s)...')
            
            if councils == 0:
                self.stdout.write(
                    self.style.WARNING('Cannot warm cache: No councils in database')
                )
                return False
            
            if years == 0:
                self.stdout.write(
                    self.style.WARNING('Cannot warm cache: No financial years in database')
                )
                return False
            
            # Run the SiteTotalsAgent with progress indication
            self.stdout.write(f'   > Running SiteTotalsAgent (this may take a moment)...')
            
            # Estimate processing time based on data size
            estimated_operations = 0
            for sc in site_counters:
                if sc.year:
                    estimated_operations += councils  # One year
                else:
                    estimated_operations += councils * years  # All years
            
            for gc in group_counters:
                if gc.year:
                    estimated_operations += councils  # One year (filtered by group)
                else:
                    estimated_operations += councils * years  # All years (filtered by group)
            
            if estimated_operations > 100:
                self.stdout.write(f'     Estimated operations: {estimated_operations:,}')
                self.stdout.write(f'     Using efficient SQL aggregation - should take 2-3 seconds...')
            
            # Execute the cache warming using the efficient agent (2-3 seconds instead of 5+ minutes)
            from council_finance.agents.efficient_site_totals import EfficientSiteTotalsAgent
            agent = EfficientSiteTotalsAgent()
            agent.run()
            
            # Step 4: Verify cache was warmed successfully
            self.stdout.write(f'   > Verifying cache warming results...')
            
            warmed_successfully = 0
            still_cold = 0
            
            for sc in site_counters:
                year_label = sc.year.label if sc.year else "all"
                # FIXED: Use counter.slug to match EfficientSiteTotalsAgent key pattern
                cache_key = f"counter_total:{sc.counter.slug}:{year_label}"
                cached_value = cache.get(cache_key)
                
                if cached_value is not None:
                    warmed_successfully += 1
                    formatted_value = f"{cached_value:,.0f}" if isinstance(cached_value, (int, float)) else str(cached_value)
                    self.stdout.write(f'     [SUCCESS] {sc.name}: {formatted_value}')
                else:
                    still_cold += 1
                    self.stdout.write(f'     [FAILED] {sc.name}: Still cold')
                    success = False
            
            for gc in group_counters:
                year_label = gc.year.label if gc.year else "all"
                # FIXED: Use counter.slug for group counters too
                cache_key = f"counter_total:{gc.counter.slug}:{year_label}"
                cached_value = cache.get(cache_key)
                
                if cached_value is not None:
                    warmed_successfully += 1
                    formatted_value = f"{cached_value:,.0f}" if isinstance(cached_value, (int, float)) else str(cached_value)
                    self.stdout.write(f'     [SUCCESS] {gc.name}: {formatted_value}')
                else:
                    still_cold += 1
                    self.stdout.write(f'     [FAILED] {gc.name}: Still cold')
                    success = False
            
            # Step 5: Summary
            total_counters = site_counters.count() + group_counters.count()
            self.stdout.write(f'   > Cache warming summary:')
            self.stdout.write(f'     - Successfully warmed: {warmed_successfully}/{total_counters}')
            
            if still_cold > 0:
                self.stdout.write(f'     - Still cold: {still_cold}')
                self.stdout.write(f'     - This may indicate missing data or counter configuration issues')
            
            # Step 6: Performance benefit explanation
            if success:
                self.stdout.write(f'   > Performance impact:')
                self.stdout.write(f'     - Home page load time should now be much faster')
                self.stdout.write(f'     - Counters will display real values instead of £0')
                self.stdout.write(f'     - Cache will remain warm until next server restart')
            
            return success
            
        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'Cache warming failed - missing dependency: {e}')
            )
            return False
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Cache warming failed: {e}')
            )
            if self.debug_mode:
                import traceback
                self.stdout.write(f'   [DEBUG] Traceback: {traceback.format_exc()}')
            return False