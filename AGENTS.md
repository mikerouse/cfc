# AGENTS.md

## What is the app?

The purpose of this app is to provide visitors with transparency data relating to UK local government entities, and in particular local councils (district, county, unitary, metropolitian borough, non-metropolitan borough, combined authority). In the future the app should be expandable to include different types of public bodies such as NHS trusts, quangos and/or UK government agencies. 

The app's approach is to use visually striking ways to give focus to financial figures found within each authority's balance sheet, cash flow statements and comprehensive income and expenditure statements as published each financial year. Each council publishes their data slightly differently, and even within the PDFs they may use differing terminology. This app aims to smooth out the language and provide consistency across the bodies in respect of their financial figures.

The emphasis is on 'visually striking' ways to show the data using counters and other interesting and novel devices like comparing spend across councils. Cross-comparison is a key feature. There will be a comparison basket, allowing up-to six councils to be compared (initially), and there will be user-centric tools allowing users to track and collate councils, as well as provide contributions and comments. Counters will be animated, and the style wll be fresh, minimalist and professional, with a look and feel similar to GOV.UK websites so that it is easy to use, easy to navigate and provides a refreshing experience for the user.

## Coding standards and expectations

- Use internal APIs and AJAX or other similar methods to get figures from the system and display them with JavaScript animations.
- Counters should always be animated using a CountUp method, ensuring each digit is animated, not the whole number or surrounding DIV.
- Prefer buttons over links, except for the proper names of things.
- Always provide progress updates and feedback to the user in the UI so they know what's happening and can be assured that actions they have requested have been executed.
- Write comments around your code to explain what you are doing and more importantly why you are doing it.
- Decorate code blocks with comments to explain what they do, how they interact, what they depend upon and any other requirements.
- Adhere to requirements such as spacing and indentations.
- Prioritise code that can be interrogated by humans more easily than code that is efficient but dense.
- Emphasise maintainability, extensibility and portability.
- Search tools should work as live or predictive features - show the results as the user types a couple or few letters, and allow the user to choose the result they want from a drop-down, which can be enriched with shortcut links or buttons depending upon what context the search is used within. 

## Things the creator cares about:

- We care about comments. There should be useful and descriptive comments.
- We care about helpers in the UI for the benefit of users.
- We care about realtime and live data using websockets or polling.
- We care about taking a holistic app-wide view - this means if we adjust functionality that affects one place we look around the app to see where else might be affected and act accordingly.
- We prioritise the user experience and ease-of-use. That means we do not use things like alert() we use modals instead.
- We care about accessibility, but not when it compromises design. We should do both.
- We log, log, log.

## Things the create does NOT care about

- Loading indicators and progress indicators
- Verbose status and debugging information
- Deleting old work and replacing it with better

## OpenAI Integration

- The app will integrate with OpenAI to use models to extract data from provided PDFs

## Migrating from WordPress Plugin to Django Agent Architecture

This document guides the migration of the `council-finance-counters` WordPress plugin into a modern, scalable **Django-based agent system**.

Each “agent” in Django represents a discrete unit of business logic previously managed by PHP classes within a WordPress plugin environment. This allows for cleaner architecture, easier testing, and more powerful orchestration. The old system can be referenced at https://github.com/mikerouse/council-debt-counters

## 🔗 Original Plugin Structure Reference

Most core logic is located in the `includes/` directory of the original WordPress plugin at https://github.com/mikerouse/council-debt-counters:
- `class-data-loader.php`: handles import of CSVs/data files.
- `class-counter-manager.php`: computes financial metrics.
- `class-councils-table.php`, `class-council-post-type.php`: model/data definitions.
- `class-settings-page.php`, `class-admin-dashboard-widget.php`: WordPress-specific admin features.
- `class-openai-helper.php`, `class-ai-extractor.php`: AI support agents.
- `class-moderation-log.php`, `class-whistleblower-*`: moderation & reporting logic.


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
   - Data cleansing and import tools

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
When developing this app, write unit tests (and other test types) to ensure robust testing is in place. Some tests should be exposed to the admin users in the backend such as things like tests to check the integrity of data, which can be run routinely. 

---

## 🛠 Configuration

- Use `.env` files for API keys and database URLs.
- `config/settings.py` is loaded dynamically and supports overrides via environment.
- Store config overrides or user-specified parameters via a `settings` model or flatfile.
- Update requirements.txt with any requirements as needed.

## 🔄 Scheduling

Use cron or Django-Q/Celery for periodic agents (e.g. daily imports):

```cron
0 3 * * * /path/to/venv/bin/python manage.py runagent ImporterAgent
```
## Styling

- Use Tailwind CSS for styles
- Clean, accessible UI
- Design based on principles set out in https://frontend.design-system.service.gov.uk/
- However, this is NOT an official UK government website and so the design should not replicate entirely GOV.UK websites, simply use them for inspiration

## ✅ Summary

This migration will:
- Separate core logic from presentation
- Enable multi-source imports and cleaner testing
- Support long-term extensibility (e.g., APIs, dashboards, ML)

Each PHP class becomes a Python agent or model. Migration is incremental—start with imports, then counters, then interface code.

Happy porting! 🎉
