# AGENTS.md

## What is the app?

The purpose of this app is to provide visitors with transparency data relating to UK local government entities, and in particular local councils (district, county, unitary, metropolitian borough, non-metropolitan borough, combined authority). In the future the app should be expandable to include different types of public bodies such as NHS trusts, quangos and/or UK government agencies. 

The app's approach is to use visually striking ways to give focus to financial figures found within each authority's balance sheet, cash flow statements and comprehensive income and expenditure statements as published each financial year. Each council publishes their data slightly differently, and even within the PDFs they may use differing terminology. This app aims to smooth out the language and provide consistency across the bodies in respect of their financial figures.

The emphasis is on 'visually striking' ways to show the data using counters and other interesting and novel devices like comparing spend across councils. Cross-comparison is a key feature. There will be a comparison basket, allowing up-to six councils to be compared (initially), and there will be user-centric tools allowing users to track and collate councils, as well as provide contributions and comments. Counters will be animated, and the style wll be fresh, minimalist and professional, with a look and feel similar to GOV.UK websites so that it is easy to use, easy to navigate and provides a refreshing experience for the user.

## The 'Contribute' Pages

This system is designed to be like Wikipedia, where users can contribute data and information. The 'Contribute' pages are designed to be user-friendly, allowing users to easily add or edit information about councils, financial figures, and other relevant data. The 'Contribute' pages are built with the following principles in mind:

- **User-Friendly**: The interface is designed to be intuitive and easy to navigate, allowing users to quickly find the information they need and contribute data without confusion.
- **Guided Contributions**: Users are guided through the contribution process with clear instructions and prompts, ensuring that they understand what information is required and how to provide it.
- **Validation**: Input fields are validated to ensure that the data entered is accurate and conforms to the expected format. This helps maintain the integrity of the data in the system.

The point of the 'Contribute' pages is to act as the master queue for all missing data relating to councils in a way that means users do not have to navigate to the pages of individual councils to contribute data. This allows for a more streamlined and efficient process for users to contribute information, ensuring that the system remains up-to-date and accurate.

The 'Contribute' system is also supposed to be fun and engaging, encouraging users to participate and contribute data. The design and functionality of the 'Contribute' pages are intended to make the process enjoyable, fostering a sense of community and collaboration among users.

Above all, however, the 'Contribute' system has to work. When a user contributes data it must be applied to the council in question. There should be safeguards to prevent abuse, such as rate limiting and moderation, to ensure that the contributions are genuine and beneficial to the system. However, the primary focus is on making the contribution process as seamless and effective as possible, allowing users to easily add valuable information to the system. Moderators can review changes to key data like council characteristics, but the system should be designed to allow for quick and easy contributions from users. Light touch moderation is intended to ensure contributions are appropriate and accurate, without creating unnecessary barriers to participation.

In addition to light touch moderation, the system should also provide users with feedback on their contributions. This could include notifications when their contributions are approved or if any issues arise that need to be addressed. The goal is to create a transparent and responsive system that encourages ongoing user engagement and trust in the data being contributed.

As the system evolves, the 'Contribute' pages may also include features for users to track their contributions, see how their data has been used, and engage with other users in discussions about the data. This could further enhance the sense of community and collaboration, making the 'Contribute' pages a central hub for user engagement within the app.

A future aim for moderation is to have a 'blockchain' like experience whereby contributions are accepted and then confirmed by community members, with a system of rewards or recognition for users who consistently contribute valuable data. This could help to build a more robust and engaged user base, further enhancing the quality and accuracy of the data within the system. If a contribution receives 15 upvotes or confirmations it is considered to be accurate and is applied to the council in question. This system of community validation not only helps to ensure the accuracy of the data but also fosters a sense of ownership and pride among users, encouraging them to actively participate in maintaining and improving the quality of information available within the app.

The 'Contribute' pages are not designed to replace the existing council pages but rather to complement them. They provide a streamlined and efficient way for users to contribute data without having to navigate through multiple pages. The 'Contribute' system is intended to be a central hub for user contributions, making it easier for users to engage with the app and contribute valuable information about councils and their financial figures. We accept that some users will prefer to just contribute to their favourite council, such as the one where they live and may never use the 'Contribute' queues. Their submissions however are just as valid and should be treated in the same esteem.

## The 'Lists' Pages

The 'Lists' section allows users to create custom lists, similar to how 'wish lists' work in e-commerce. They allow the user to group councils together in any way they choose - for instance by geography or by council type, the possibilities are almost endless. The lists are designed to be user-friendly and intuitive, allowing users to easily create, manage, and share their lists of councils.

Data and counters can then be applied to the lists, allowing users to see totals such as total debt levels for all councils in a given list. 

## The 'Following' Page 

Users can 'follow' councils, similar to how people follow accounts on social media websites. This allows them to see updates relating to their followed councils. This can include financial updates, such as new reports being published or new financial information being made available. When contributions are approved they should push an update to the feed. Users can comment on these feed items. Updates to the council's feed on the 'Following' page won't just be restricted to financial updates, but can also include other relevant information such as changes in council leadership, new initiatives, or community events. This helps to keep users engaged and informed about the councils they care about. This also acts as a hook for the council to engage with the platform to let people know what's going on. 

Users can also 'follow' lists, allowing them to see updates relating to the lists they are interested in. This could include new councils being added to a list, changes in the financial figures of councils within a list, or other relevant updates. The 'Following' page is designed to be a central hub for users to stay connected with the councils and lists they care about, providing a personalized feed of updates and information.

Users can also 'follow' individual financial figures, allowing them to see updates and changes to specific financial metrics across all councils. This could include changes in debt levels, budget allocations, or other key financial indicators. By following these figures, users can stay informed about trends and developments in council finances that are of particular interest to them.

Users can also 'follow' specific contributors, allowing them to see updates and contributions made by those users. This could include new data submissions, comments on council pages, or other relevant contributions. By following contributors, users can engage more deeply with the community and stay informed about the work being done by others in the platform.

Users can prioritise which updates they see first, allowing them to customize their feed based on their interests and preferences. This could include options to filter updates by council, list, financial figure, or contributor, ensuring that users can easily find the information that matters most to them. Users can choose to receive notifications about updates to their followed councils, lists, financial figures, or contributors. This could include email notifications, in-app alerts, or push notifications on mobile devices. By providing these options, users can stay informed about the latest developments and contributions in the platform without having to constantly check for updates.

Data and telemetry based on the 'Following' page and interactions therein should be collected to help improve the user experience and trigger algorithm-based features such as which council to promote to the home page. For instance, where a council is suddenly getting a lot of follows, comments or visits we would want to look to promote that council and understand the reason for the attention. For instance, if a council is getting a lot of follows it may be because they are doing something interesting or have recently made a significant change that users want to know more about. This could be a new initiative, a change in leadership, or a significant financial update. By promoting these councils on the home page, we can help users discover new and relevant information that they may not have been aware of otherwise.

## Creator's rules

- We care about comments. There should be useful and descriptive comments.
- We care about helpers in the UI for the benefit of users.
- We care about realtime and live data using websockets or polling.
- We care about taking a holistic app-wide view - this means if we adjust functionality that affects one place we look around the app to see where else might be affected and act accordingly.
- We prioritise the user experience and ease-of-use. That means we do not use things like alert() we use modals instead.
- We care about accessibility, but not when it compromises design. We should do both.
- We log, log, log.
- We like loading indicators and progress indicators.
- We like verbose status and debugging information.
- We delete old work and replace it with better.
- We don't do stub implementations, we do things properly.
- We build with the future in mind.
- We use Tailwind CSS for styling. We do not need to use Bootstrap or any other CSS framework, even if it was used in the past.
- We do not break other parts of the system when fixing things, and we do not stub things out.

## Rules about User Levels

This system is designed to accept contributions from the public via registered accounts, so that they may update the data relating to their own council. The user profile system also recognises and invites people who work for councils to provide us with data too. The aim of the website is to provide a platform for users to contribute data and information about councils, financial figures, and other relevant data. The user levels are designed to reflect the different roles and responsibilities of users within the system, ensuring that contributions are appropriate and beneficial to the platform.

- **Tier 1**: The default level for all users. They can view and contribute data, but their contributions may require moderation depending on the type and other rules.
- **Tier 2**: Users who have demonstrated consistent and valuable contributions. They can contribute data without moderation, but their contributions are still subject to community validation.
- **Tier 3**: Users who work for councils or have a proven track record of high-quality contributions. They can contribute data without moderation and have access to additional features such as advanced analytics and reporting tools.
- **Tier 4**: Users who are recognized as experts in the field, such as financial analysts or council officials. They have all the privileges of Tier 3 users, plus the ability to create and manage custom lists and advanced data visualizations.
- **Tier 5 (God Mode)**: The highest level, reserved for trusted contributors and moderators. They have full access to all features, including the ability to approve or reject contributions from other users, manage user accounts, and access advanced administrative tools.

Components and features should be appropriately gated to their user level, ensuring that users only have access to the features and data that are relevant to their role within the system. This helps maintain the integrity of the platform and ensures that contributions are appropriate and beneficial to all users. There should be a control panel under God Mode to set permission levels for each tier and control what they each have access to. This control panel should be user-friendly and intuitive, allowing administrators to easily manage user levels and permissions without confusion.

The system should also offer data via API, for which a secure key is required. This API should be designed to allow users to access and interact with the data in a secure and controlled manner, ensuring that sensitive information is protected while still allowing for valuable contributions and insights. Users will be able to generate API keys from their user profile, and these keys should be securely stored and managed within the system. The API should support various endpoints for accessing council data, financial figures, and user contributions, allowing developers to build applications and integrations that leverage the platform's data and functionality. We may - or may not - charge for API access in the future.

## OpenAI Integration

- The app will integrate with OpenAI to use models to extract data from provided PDFs.

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
