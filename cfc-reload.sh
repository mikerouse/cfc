#!/bin/bash
echo "Council Finance Counters - Development Reload"
echo "============================================="

# Kill any existing Python processes
echo "[1/4] Stopping Django server..."
pkill -f "python.*manage.py.*runserver" 2>/dev/null || true

# Wait for processes to stop
sleep 2

# Clear Django cache
echo "[2/4] Clearing caches..."
python manage.py clear_dev_cache >/dev/null 2>&1

# Run Django checks
echo "[3/4] Running checks..."
python manage.py check

if [ $? -ne 0 ]; then
    echo
    echo "❌ Django checks failed! Please fix the errors above before starting the server."
    exit 1
fi

# Start development server
echo "[4/4] Starting development server..."
echo
echo "✅ CFC development server starting..."
echo "   Navigate to: http://127.0.0.1:8000/"
echo "   Press Ctrl+C to stop"
echo
python manage.py runserver