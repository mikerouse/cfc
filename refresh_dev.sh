#!/bin/bash
echo "Refreshing development environment..."

# Kill any existing Python processes running Django
echo "Stopping existing Django server..."
pkill -f "python.*manage.py.*runserver" 2>/dev/null || true

# Wait a moment for processes to fully stop
sleep 2

# Clear Django cache
echo "Clearing Python cache..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Clear static cache if it exists
if [ -d "static/CACHE" ]; then
    echo "Clearing static cache..."
    rm -rf "static/CACHE"
fi

# Run Django checks
echo "Running Django checks..."
python manage.py check

# Start development server
echo "Starting Django development server..."
echo ""
echo "Development server will start on http://127.0.0.1:8000/"
echo "Press Ctrl+C to stop the server"
echo ""
python manage.py runserver