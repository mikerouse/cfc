# Development Setup and Automation

This document explains how to handle development server restarts and cache clearing when making changes to the Council Finance Counters application.

## Quick Development Refresh

When you make changes to templates, JavaScript, or Python code and don't see them reflected in your browser, you likely have caching issues. Here are several ways to fix this:

### Option 1: Super Easy Commands ⭐ (Recommended)

**The easiest way - just run:**
```bash
cfc-reload
```

**Or use the Django management command:**
```bash
python manage.py reload
```

**Alternative names for the same functionality:**
```cmd
# Windows
cfc-reload.bat

# Linux/Mac  
./cfc-reload.sh
```

These commands will:
- Stop any running Django development servers
- Clear Python cache files (`__pycache__` directories and `.pyc` files)
- Clear static file caches
- Run Django checks to ensure no errors
- Start a fresh development server

### Option 1b: Install Global Command (Optional)

To run `cfc-reload` from anywhere on your system:

**Windows:**
```cmd
# Run as administrator
install-global-command.bat
```

**Linux/Mac:**
```bash
# Add to your ~/.bashrc or ~/.zshrc
export PATH="$PATH:/path/to/your/cfc/directory"
```

### Option 2: Use Django Management Command

For more targeted cache clearing:

```bash
# Clear Python cache only
python manage.py clear_dev_cache

# Clear Python + template cache
python manage.py clear_dev_cache --templates

# Clear everything (Python, templates, static files)
python manage.py clear_dev_cache --all
```

### Option 3: Manual Steps

If the automated scripts don't work, you can manually:

1. **Stop the development server** (Ctrl+C in the terminal running Django)

2. **Clear browser cache** - In your browser:
   - Chrome/Edge: Ctrl+Shift+R (hard refresh)
   - Firefox: Ctrl+F5
   - Or open Developer Tools → Network tab → check "Disable cache"

3. **Clear Python cache:**
   ```bash
   # Windows
   for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"
   
   # Linux/Mac
   find . -name "__pycache__" -type d -exec rm -rf {} +
   ```

4. **Restart Django server:**
   ```bash
   python manage.py runserver
   ```

## Browser Cache Prevention

The application automatically includes cache-busting headers in development mode. You should see a `cache-version` meta tag in the HTML head that changes on each server restart.

## Common Issues

### Issue: Changes to templates/JavaScript not appearing
**Solution:** Use the refresh script or hard refresh your browser (Ctrl+Shift+R)

### Issue: Formula Builder not working after changes
**Solution:** This is often due to JavaScript caching. Use the refresh script and hard refresh the browser.

### Issue: "Module not found" errors after changes
**Solution:** Python cache may be stale. Use `python manage.py clear_dev_cache` or restart the server.

### Issue: Static files (CSS/JS) not updating
**Solution:** Clear static file cache with `python manage.py clear_dev_cache --all`

## Development Tips

1. **Always use the refresh script** when switching between branches or after major changes
2. **Keep browser dev tools open** with cache disabled during development
3. **Use incognito/private browsing** for testing to avoid cache issues
4. **Check the terminal** for any Django error messages when changes don't appear

## Automation Features

The development automation includes:

- **Smart process detection**: Automatically finds and stops running Django servers
- **Comprehensive cache clearing**: Removes Python, template, and static file caches
- **Error checking**: Runs Django checks before starting the server
- **Cross-platform support**: Works on Windows, Linux, and macOS
- **Cache busting**: Automatic cache version injection in development mode

## Production Notes

In production, cache clearing should be handled differently:
- Use proper static file versioning
- Implement CDN cache invalidation
- Use database-backed caching instead of in-memory
- Consider using Redis or Memcached for session/cache storage