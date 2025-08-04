# Council Finance Counters

[![Version](https://img.shields.io/badge/version-0.1-blue.svg)](https://github.com/mikerouse/cfc/releases/tag/v0.1)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.2+-green.svg)](https://www.djangoproject.com/)

Council Finance Counters is an open-source platform that makes UK council financial data accessible, understandable, and actionable. It transforms complex financial statements into clear insights through AI-powered analysis, interactive visualisations, and social features.

## Features

- **Comprehensive Financial Tracking**: Monitor spending, income, debt, and assets across all UK councils
- **AI-Powered Insights**: Intelligent analysis generates contextual factoids about council finances
- **Interactive Counters**: Animated displays showing key financial metrics in real-time
- **Social Following**: Follow councils, lists, figures, and contributors to track changes
- **Custom Lists**: Create and share custom groupings of councils (like playlists)
- **Comparison Tools**: Compare financial data across multiple councils
- **Leaderboards**: See how councils rank on various financial metrics
- **Mobile-First Design**: Fully responsive interface optimised for all devices
- **Real-Time Updates**: WebSocket-powered live data updates
- **Community Contributions**: Wikipedia-style contribution system with moderation

## Prerequisites

- Python 3.8 or higher
- PostgreSQL 12+ (recommended) or SQLite (development only)
- Node.js 16+ and npm
- Git
- Redis (optional, for caching and real-time features)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/mikerouse/cfc.git
cd cfc
```

### 2. Set Up Python Environment

Create and activate a virtual environment:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies

```bash
npm install
```

### 5. Configure Environment

Copy the sample environment file and edit it:

```bash
cp .env.sample .env
```

Edit `.env` with your configuration:

```env
# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql://username:password@localhost:5432/council_finance
# For development with SQLite:
# DATABASE_URL=sqlite:///db.sqlite3

# Security (generate a new secret key for production)
SECRET_KEY=your-secret-key-here
DEBUG=True  # Set to False in production
ALLOWED_HOSTS=localhost,127.0.0.1

# AI Services (required for factoids)
OPENAI_API_KEY=your-openai-api-key

# Email (optional, for notifications)
BREVO_API_KEY=your-brevo-api-key
ERROR_ALERTS_EMAIL_ADDRESS=admin@yourdomain.com

# GitHub Integration (optional, for About page stats)
GITHUB_PERSONAL_ACCESS_TOKEN=your-github-token
```

### 6. Set Up Database

Run migrations to create the database schema:

```bash
python manage.py migrate
```

### 7. Create Admin Account

```bash
python manage.py createsuperuser
```

### 8. Build Frontend Assets

Build CSS with Tailwind:

```bash
npm run build-css-prod
```

Build React components:

```bash
npm run build:prod
```

### 9. Collect Static Files (Production)

```bash
python manage.py collectstatic --noinput
```

## Running the Application

### Development Server

Start the Django development server with built-in testing:

```bash
python manage.py reload
```

Options:
- `--no-tests`: Skip tests for faster startup
- `--test-only`: Run tests without starting server
- `--validate`: Run maximum validation checks

The application will be available at `http://localhost:8000/`

### Production Deployment

For production, use Gunicorn with Uvicorn workers:

```bash
gunicorn council_finance.asgi:application -w 4 -k uvicorn.workers.UvicornWorker
```

## Initial Data Setup

1. **Access Django Admin**: Navigate to `http://localhost:8000/admin/` and log in with your superuser credentials

2. **Create Financial Years**: Add financial year records (e.g., 2023/24, 2024/25)

3. **Add Councils**: Import council data or add manually through the admin

4. **Configure Data Fields**: Set up financial data fields and their categories

5. **Enable Counters**: Configure which counters should be displayed

## Testing

Run the comprehensive test suite:

```bash
python manage.py reload --test-only
```

Run specific tests:

```bash
pytest
```

Check for template errors:

```bash
python manage.py validate_heroicons
```

## Documentation

- **[FACTOIDS.md](FACTOIDS.md)**: AI-powered factoids system architecture
- **[DESIGN_PRINCIPLES.md](DESIGN_PRINCIPLES.md)**: Mobile-first design patterns and UI/UX guidelines
- **[PAGE_SPECIFICATIONS.md](PAGE_SPECIFICATIONS.md)**: Detailed page specifications and user flows
- **[AGENTS.md](AGENTS.md)**: Counter agent system and calculation logic
- **[LEADERBOARDS.md](LEADERBOARDS.md)**: Leaderboards implementation and API
- **[CLAUDE.md](CLAUDE.md)**: Development instructions for AI assistants

## Project Structure

```
cfc/
├── council_finance/       # Main Django application
│   ├── models/           # Database models
│   ├── views/            # View controllers
│   ├── templates/        # Django templates
│   ├── static/           # Static assets
│   └── services/         # Business logic services
├── frontend/             # React components
├── static/               # Global static files
│   ├── css/             # Tailwind CSS
│   └── js/              # JavaScript files
├── config/              # Configuration files
├── tests/               # Test suite
└── manage.py            # Django management script
```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/mikerouse/cfc/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mikerouse/cfc/discussions)
- **Support the Developer**: [Buy Me a Coffee](https://buymeacoffee.com/mikerouse)

## Acknowledgements

- Built with Django, React, and Tailwind CSS
- AI insights powered by OpenAI
- Icons by Heroicons
- Community contributions from many developers

---

**Version 0.1** - Initial baseline release with core functionality