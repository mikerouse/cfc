---
applyTo: '**'
---
Coding standards, domain knowledge, and preferences that AI should follow.

# AGENTS.md

Read the AGENTS.md file for detailed instructions.

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

# Council Finance Counters V3 Instructions

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