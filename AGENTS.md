applyTo: '**'

# Council Finance Counters V3

This app aims to provide transparency data by seeking out the published annual Statement of Accounts for each local authority (council) in the United Kingdom. It extracts key financial metrics and presents them in an accessible format for tracking, comment, sharing and analysis. The app uses AI-powered factoids to provide insights and context for the data, and cross-compares councils against each other using leaderboards and other novel visualizations.

## Core System Documentation:
- **[AGENTS.md](../../AGENTS.md)** - A copy of these instructions for other AI and human agents
- **[FACTOIDS.md](../../docs/FACTOIDS.md)** - Complete AI-powered factoids system architecture and implementation
- **[DESIGN_PRINCIPLES.md](../../docs/DESIGN_PRINCIPLES.md)** - Mobile-first design patterns, grid system, and UI/UX guidelines
- **[PAGE_SPECIFICATIONS.md](../../docs/PAGE_SPECIFICATIONS.md)** - Detailed page rules, user flows, and business logic for key pages
- **[LEADERBOARDS.md](../../docs/LEADERBOARDS.md)** - Complete leaderboards system implementation, API, and enhancement roadmap
- **[EVENT_VIEWER.md](../../docs/EVENT_VIEWER.md)** - Comprehensive monitoring, logging, and debugging system
- **[COUNTER_CACHING.md](../../docs/COUNTER_CACHING.md)** - Database-backed 3-tier counter caching system with smart invalidation
- **[README.md](../../README.md)** - Project setup and deployment instructions

## Key Features

**Key Pages**:
- **Contribute**: Wikipedia-style data contribution system with light-touch moderation
- **Lists**: Custom council grouping (like wish lists) with data aggregation
- **Following**: Social media-style following of councils, lists, figures, and contributors
- **Backend Management**: Custom control panel only (no Django admin for users)

## Creator's commandments that AI agents should always follow

- We care about code comments. There should be useful and descriptive comments to help future developers.
- We care about helpers in the UI for the benefit of users. We help our users.
- We care about code quality. This means we do not use quick hacks or shortcuts, we do things properly.
- We care about code readability. This means we use descriptive variable names, we break up long functions, we use whitespace and indentation properly.
- We care about code maintainability. This means we write code that is easy to understand and modify in the future.
- We care about code efficiency. This means we write code that is performant and does not waste resources.
- We care about security. This means we do not expose sensitive information, we use secure coding practices, we validate user input.
- We care about testing. This means we write unit tests, integration tests, and end-to-end tests.
- We care about documentation. This means we write clear and concise documentation for our code, our APIs, and our systems.
- We care about error handling. This means we handle errors gracefully, we log errors, we provide useful error messages to users.
- We care about version control. This means we use git properly, we write clear commit messages, we use branches for features and bug fixes.
- We care about realtime and live data using websockets or polling.
- We care about taking a holistic app-wide view - this means if we adjust functionality that affects one place we look around the app to see where else might be affected and act accordingly.
- We care about consistency. This means we use consistent naming conventions, we use consistent coding styles, we use consistent UI patterns.
- We prioritise the user experience and ease-of-use. That means we do not use things like alert() we use modals instead.
- We care about accessibility, but not when it compromises design. We should do both.
- We log, log, log.
- We like loading indicators and progress indicators.
- We like verbose status and debugging information.
- We delete legacy work and replace it with better. We don't leave old code in place "just in case".
- We use Django and Python best practices.
- We use Tailwind CSS for styling. We do not need to use Bootstrap or any other CSS framework, even if it was used in the past.
- **We do not break other parts of the system** when fixing things, and we **do not** stub things out.
- **Run the check_templates.py script** to ensure all templates are valid and do not contain any errors.
- **Use UK English throughout the system** - this means "analyse" not "analyze", "colour" not "color", "favourite" not "favorite", etc. All text, comments, variable names, and user-facing content should follow UK English conventions.

## Render

Using the Render MCP server (render-mcp in mcp.json), set my workspace to the workspace called 'Mike's Workspace' (ID tea-cvul2v15pdvs73c620ug) and use the 'council-finance-counters' project. The Postgresql database is 'council-finance-counters'. The servers are 'cfc' for the main web server and 'cfc-tika' for the Apache Tika document parsing server.

Confirm you have accessed the correct workspace and project by telling me the CPU / memory usage for the 'cfc' server.

## Context7

Always use context7 when I need code generation, setup or configuration steps, or library/API documentation. This means you should automatically use the Context7 MCP tools to resolve library id and get library docs without me having to explicitly ask.

## Critical Context Loss Prevention Rules

### 1. UNDERSTAND BEFORE CHANGING
- **ALWAYS** check existing patterns before creating new ones
- Run `grep_search` to find how similar problems are already solved
- Test existing systems before assuming they're broken
- Check for existing API endpoints before creating new ones

### 2. DATA FIELD NAMING CONVENTIONS
The system has TWO field naming formats that must be handled correctly:

- **Slug format**: `interest-payments-per-capita` (used in URLs, templates, database slugs)
- **Variable format**: `interest_payments_per_capita` (used in code, context data)

**CRITICAL**: Template rendering must convert between formats:
```python
# WRONG - looking for slug format in context
value = context_data.get('interest-payments-per-capita')  # Will be None

# CORRECT - convert to variable format  
field_variable_name = field_name.replace('-', '_')
value = context_data.get(field_variable_name)  # Will find the value
```

## Heroicon Usage Guidelines

**Supported Syntaxes** (both work, but be consistent):
```django
{# Size-based syntax (recommended) #}
{% heroicon "icon-name" size="mini" class="w-4 h-4" %}

{# Outline/Solid syntax #}
{% heroicon_outline "icon-name" class="w-4 h-4" %}
{% heroicon_solid "icon-name" class="w-4 h-4" %}
```

**CRITICAL - Dynamic Variable Usage**:
**NEVER** use dynamic variables in heroicon calls - this causes template failures:
```django
{# WRONG - This will fail at runtime #}
{% heroicon feature.icon size="medium" class="w-6 h-6" %}
{% heroicon variable_name size="small" class="w-4 h-4" %}

{# CORRECT - Use conditional logic instead #}
{% if feature.icon == 'chart-bar' %}
    {% heroicon "chart-bar" size="medium" class="w-6 h-6" %}
{% elif feature.icon == 'cog' %}
    {% heroicon "cog" size="medium" class="w-6 h-6" %}
{% else %}
    {% heroicon "document" size="medium" class="w-6 h-6" %}
{% endif %}

{# BEST - Hardcode icon names directly #}
{% heroicon "chart-bar" size="medium" class="w-6 h-6" %}
```

**Known Valid Icons**: `cog`, `eye`, `document`, `search`, `refresh`, `check`, `home`, `chat`, `share`, `plus`, `pencil`, `information-circle`, `rss`, `chart-bar`

**Common Invalid Icons and Replacements**:
- `arrow-path` → `refresh`
- `building-office` → `home` 
- `chat-bubble-oval-left` → `chat`
- `arrow-up-tray` → `share`
- `cog-6-tooth` → `cog`
- `document-text` → `document`
- `magnifying-glass-plus` → `search`
- `code-bracket` → `document`
- `exclamation-triangle` → `information-circle`
- `sparkles` → `cog`
- `users` → `rss`

**Best Practices**:
1. **Always use hardcoded icon names** - never use variables in heroicon calls
2. **Always test heroicons** when adding new ones to templates
3. **Run validation** before committing template changes: `python manage.py validate_heroicons`
4. **Use --fix flag** to automatically replace invalid icons with safe fallbacks
5. **Stick to known valid icons** from the list above when possible
6. **Use conditional logic** if you need dynamic icons based on context data

**Common Error Pattern**:
If you see "code-bracket is not a valid icon!" or similar errors, it's usually because:
1. You're using a variable in the heroicon call: `{% heroicon variable_name %}`
2. The icon name is invalid or misspelled
3. You need to use conditional logic instead of dynamic variables

## 🔄 Scheduling

Use cron or Django-Q/Celery for periodic agents (e.g. daily imports):

```cron
0 3 * * * /path/to/venv/bin/python manage.py runagent ImporterAgent
```
