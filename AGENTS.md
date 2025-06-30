# AGENTS.md

## Migrating from WordPress Plugin to Django Agent Architecture

This document guides the migration of the `council-finance-counters` WordPress plugin into a modern, scalable **Django-based agent system**.

Each “agent” in Django represents a discrete unit of business logic previously managed by PHP classes. This allows for cleaner architecture, easier testing, and more powerful orchestration.

---

## 🔗 Original Plugin Structure Reference

Most core logic is located in the `includes/` directory of the plugin:
- `class-data-loader.php`: handles import of CSVs/data files.
- `class-counter-manager.php`: computes financial metrics.
- `class-councils-table.php`, `class-council-post-type.php`: model/data definitions.
- `class-settings-page.php`, `class-admin-dashboard-widget.php`: WordPress-specific admin features.
- `class-openai-helper.php`, `class-ai-extractor.php`: AI support agents.
- `class-moderation-log.php`, `class-whistleblower-*`: moderation & reporting logic.

---

## 📦 Django Agent System Overview

In Django, each logical unit becomes a Python class inheriting from a shared `AgentBase`. These agents live in the `agents/` folder and run independently, scheduled via cron or CLI.

Typical mapping:

| WordPress Class                | Django Agent Equivalent                  |
|-------------------------------|------------------------------------------|
| `class-data-loader.php`       | `ImporterAgent` (CSV/API/data ingest)    |
| `class-counter-manager.php`   | `CounterAgent` (calculations + output)   |
| `class-docs-manager.php`      | `DocumentAgent` (downloads/exports)      |
| `class-error-logger.php`      | `LoggerAgent` or integrated Django logs  |
| `class-openai-helper.php`     | `OpenAIAgent` (content or data synthesis)|
| `class-whistleblower-*.php`   | `WhistleblowerAgent` (form processor)    |

---

## 🏗️ Django Project Structure

```
council_finance/
├── agents/
│   ├── __init__.py
│   ├── base.py             # AgentBase with discovery
│   ├── importer_agent.py   # replaces class-data-loader.php
│   ├── counter_agent.py    # replaces class-counter-manager.php
│   ├── report_agent.py     # replaces output/export logic
├── models/
│   └── council.py          # e.g., Council, FigureSubmission, Year, etc.
├── manage.py
├── config/
│   ├── settings.py
│   └── urls.py
├── requirements.txt
└── scripts/
    └── dev.sh              # local dev bootstrap
```

---

## 🚀 Steps for Migration

1. **Data Models**  
   Create Django models for the following concepts:
   - `Council`
   - `Financial Year`
   - `FigureSubmission`
   - `DebtAdjustment`
   - `WhistleblowerReport`
   - `ModerationLog`

   Migrate definitions from `class-council-post-type.php` and `class-custom-fields.php`.

2. **Agents**
   - **ImporterAgent**: move logic from `class-data-loader.php`
   - **CounterAgent**: mirror `class-counter-manager.php` and calculation utils
   - **DocumentAgent**: migrate file downloads, stats, CSVs, PDFs
   - **OpenAIAgent**: wrap any OpenAI calls used in `class-openai-helper.php`
   - **ModerationAgent**: port logs from `class-moderation-log.php`

3. **Views & APIs**
   Create Django views to replace WP shortcodes (`class-shortcode-renderer.php`), if needed. Consider using Django REST Framework for external APIs.

4. **Admin UI**
   Use Django’s built-in admin to replicate:
   - Settings pages
   - Data dashboards
   - Moderation tools

---

## 🧪 Testing

Test each migrated agent as a standalone unit:

```bash
python manage.py runagent ImporterAgent --source "https://example.com/figures.csv"
```

Write tests in `agents/tests/` for each module:

```python
class CounterAgentTest(TestCase):
    def test_basic_debt_calculation(self):
        agent = CounterAgent()
        result = agent.run(year=2023)
        self.assertGreater(result['debt'], 0)
```

---

## 🛠 Configuration

- Use `.env` files for API keys and database URLs.
- `config/settings.py` is loaded dynamically and supports overrides via environment.
- Store config overrides or user-specified parameters via a `settings` model or flatfile.

---

## 🔄 Scheduling

Use cron or Django-Q/Celery for periodic agents (e.g. daily imports):

```cron
0 3 * * * /path/to/venv/bin/python manage.py runagent ImporterAgent
```

---

## 🧼 Legacy Cleanup Plan

Once all business logic has been migrated:
- Retire `class-*` files from `includes/`
- Export useful sample data (e.g. `samples/*.csv`)
- Retain PHP repo as read-only reference

---

## ✅ Summary

This migration will:
- Separate core logic from presentation
- Enable multi-source imports and cleaner testing
- Support long-term extensibility (e.g., APIs, dashboards, ML)

Each PHP class becomes a Python agent or model. Migration is incremental—start with imports, then counters, then interface code.

Happy porting! 🎉
