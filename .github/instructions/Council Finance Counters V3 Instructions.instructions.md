applyTo: '**'

# See also AGENTS.md

Read the AGENTS.md file for detailed instructions.

# CRITICAL: Avoiding Context Loss and Over-Engineering

## The Problem
AI agents lose context over long conversations and tend to re-engineer existing systems, creating overly complex, cross-cutting code that becomes wrapped up in itself. This leads to:

1. **Competing Systems**: Multiple ways to do the same thing (e.g., different API endpoints, multiple data access patterns)
2. **Field Name Mismatches**: Converting between slug formats (`interest-payments-per-capita`) and variable names (`interest_payments_per_capita`) 
3. **Cached State Issues**: New systems bypass existing caches/instances, creating inconsistent data
4. **Incomplete Integration**: New APIs don't integrate with existing frontend code

## Prevention Rules

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

### 3. FACTOID SYSTEM DEBUGGING
When factoids show "N/A":

1. **Check field categories**: Ensure FactoidEngine handles the field's category (`spending`, `financial`, etc.)
2. **Test field lookup directly**: Use `engine.get_field_value(field_name, council, year)` 
3. **Check for stale instances**: Look for cached FactoidInstance objects that might be outdated
4. **Verify counter-specific vs generic instances**: Counter-specific instances override generic ones

Common issues:
- Field category not supported in FactoidEngine
- Template uses slug format but context has variable format
- Stale cached instances with outdated data
- Missing field mappings for calculated fields

### 4. API INTEGRATION RULES
- **Check existing API endpoints** before creating new ones
- **Test frontend expectations** - what URL pattern does JavaScript expect?
- **Avoid URL pattern conflicts** - `/api/factoids/<template>` vs `/api/factoids/<counter>` will conflict
- **Use consistent response formats** - match what frontend expects

### 5. DEBUGGING STRATEGY
When things don't work:

1. **Test the lowest level first**: Direct field access, then computation, then API
2. **Check for multiple instances**: Look for competing cached data
3. **Verify integration points**: Template → Engine → API → Frontend  
4. **Clear caches when needed**: Delete stale instances to force recomputation

### 6. SYSTEM INTEGRITY
- Use the integrity checker script to validate the entire pipeline
- Monitor for competing systems doing the same job
- Ensure frontend JavaScript matches backend API patterns
- Test end-to-end user flows, not just individual components

## Example Fix Pattern
```bash
# 1. Understand the problem
python manage.py shell -c "engine.get_field_value('field_name', council, year)"

# 2. Check for stale data  
python manage.py shell -c "FactoidInstance.objects.filter(...).delete()"

# 3. Test integration
python test_frontend_api.py

# 4. Verify end-to-end
# Check actual webpage, not just API
```

Remember: **Simple fixes are usually better than complex re-engineering.**

# Backend

No users, including the super-admin, should see any Django admin pages. The Django admin is not used in this project. Instead, we use a custom-built control panel for managing the system. Only the super-admin should be able to access Django admin pages by exception and in edge case scenarios, and even then, it should be limited to specific tasks that cannot be done through the control panel. The control panel is designed to be user-friendly and intuitive, allowing administrators to manage the system without needing to navigate through complex Django admin pages.

# Pages

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

## Factoids

These are little 'newsflash-style' pieces of information, snippets or nuggets. They are factoids that tell us something interesting about the data we are looking at. For instance, "Did you know that Council X has the highest debt per capita in the country?" or "Council Y has reduced its debt by 20% over the last year." These factoids are designed to be engaging and informative, providing users with quick insights into council finances and performance. They can be displayed on council pages, in user feeds, or as part of the 'Following' updates.

Factoids can be created by users, allowing them to share interesting insights or observations about council data. This could include notable trends, comparisons between councils, or unique financial figures. Users can also upvote or downvote factoids, helping to surface the most relevant and interesting information for the community.

Factoids use a template system, allowing users to create custom templates for their factoids. This could include options for formatting, styling, and including specific data points. Users can also choose from a library of pre-defined templates to quickly create factoids without needing to design them from scratch.

Factoids are based on data from the fields and characteristics of councils, such as financial figures, demographics, or other relevant information. This allows users to create factoids that are grounded in real data, providing valuable insights into council performance and trends. New fields and groups of data can be added dynamically in the 'God Mode' control panel, allowing new figures and data to be related to a council. For instance, we may add a field called 'Number of Band D properties' to the council characteristics, which would then allow users to create factoids based on that data. Or we may add non-financial data such as 'Number of bus services' or 'Number of potholes filled' to the council's dataset, which could also be used to create interesting factoids. These performance indicators still relate to financial years, quarters and/or months, but they are non-financial in nature. Conversely, we may even start adding quarterly outturns of financial data, such as 'Q1 2024 Debt Levels', which would allow users to create factoids based on quarterly financial performance.

Factoids are a type of report building, that's not a chart. We will do charts separately. Factoids are designed to be quick and easy to create, allowing users to share interesting insights without needing to create complex reports or visualizations. They can be used to highlight key trends, comparisons between councils, or unique financial figures, providing a valuable way for users to engage with the data and share their observations with the community and the wider public via social media.

# Creator's rules that AI should follow

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
- Run the check_templates.py script to ensure all templates are valid and do not contain any errors.

# Rules about User Levels

This system is designed to accept contributions from the public via registered accounts, so that they may update the data relating to their own council. The user profile system also recognises and invites people who work for councils to provide us with data too. The aim of the website is to provide a platform for users to contribute data and information about councils, financial figures, and other relevant data. The user levels are designed to reflect the different roles and responsibilities of users within the system, ensuring that contributions are appropriate and beneficial to the platform.

- **Tier 1**: The default level for all users. They can view and contribute data, but their contributions may require moderation depending on the type and other rules.
- **Tier 2**: Users who have demonstrated consistent and valuable contributions. They can contribute data without moderation, but their contributions are still subject to community validation.
- **Tier 3**: Users who work for councils or have a proven track record of high-quality contributions. They can contribute data without moderation and have access to additional features such as advanced analytics and reporting tools.
- **Tier 4**: Users who are recognized as experts in the field, such as financial analysts or council officials. They have all the privileges of Tier 3 users, plus the ability to create and manage custom lists and advanced data visualizations.
- **Tier 5 (God Mode)**: The highest level, reserved for trusted contributors and moderators. They have full access to all features, including the ability to approve or reject contributions from other users, manage user accounts, and access advanced administrative tools.

Components and features should be appropriately gated to their user level, ensuring that users only have access to the features and data that are relevant to their role within the system. This helps maintain the integrity of the platform and ensures that contributions are appropriate and beneficial to all users. There should be a control panel under God Mode to set permission levels for each tier and control what they each have access to. This control panel should be user-friendly and intuitive, allowing administrators to easily manage user levels and permissions without confusion.

The system should also offer data via API, for which a secure key is required. This API should be designed to allow users to access and interact with the data in a secure and controlled manner, ensuring that sensitive information is protected while still allowing for valuable contributions and insights. Users will be able to generate API keys from their user profile, and these keys should be securely stored and managed within the system. The API should support various endpoints for accessing council data, financial figures, and user contributions, allowing developers to build applications and integrations that leverage the platform's data and functionality. We may - or may not - charge for API access in the future.

# Use of AI to assist the users 

The system is designed to leverage AI to assist users in various ways, enhancing the overall user experience and providing valuable insights into council data. AI can be used to:
- **Generate Factoids**: AI can analyze council data and generate interesting factoids based on trends, comparisons, and unique financial figures. This can help users quickly identify key insights without needing to manually sift through large datasets.
- **Suggest Contributions**: AI can analyze user behavior and preferences to suggest relevant contributions, such as councils to follow, lists to create, or financial figures to track. This can help users discover new areas of interest and engage more deeply with the platform.
- **Automate Data Validation**: AI can assist in validating user contributions by checking for consistency, accuracy, and relevance. This can help reduce the burden on moderators and ensure that contributions are appropriate and beneficial to the platform.
- **Enhance Search Functionality**: AI can improve search capabilities by understanding user intent and providing more relevant results based on context and user behavior. This can help users quickly find the information they need without having to navigate through multiple pages.
- **Suggest Fields and Characteristics**: AI can analyze existing council data and suggest new fields or characteristics that could be added to enhance the dataset. This can help keep the platform up-to-date with the latest trends and developments in council finances.
- **Suggest Lists**: AI can recommend custom lists for users based on their interests and contributions. This can help users organize and track relevant data more effectively.

The API key for OpenAI can be found in the .env file, and it should be used to access the AI capabilities within the system. The AI features should be designed to be user-friendly and intuitive, allowing users to easily access and benefit from the AI-generated insights and suggestions without requiring technical expertise.

# System Rules

## Console Commands

- You don't need to do `cd` before every python command - you are already in the project directory.
- Avoid using `&&` in terminal commands.

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