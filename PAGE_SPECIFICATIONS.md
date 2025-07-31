# PAGE SPECIFICATIONS
*Council Finance Counters Platform*
*Generated: 2025-07-31*

This document contains detailed specifications for key pages and their unique functionality, business rules, and user interactions.

---

## The 'Contribute' Pages

This system is designed to be like Wikipedia, where users can contribute data and information. The 'Contribute' pages are designed to be user-friendly, allowing users to easily add or edit information about councils, financial figures, and other relevant data.

### Core Principles
- **User-Friendly**: The interface is designed to be intuitive and easy to navigate, allowing users to quickly find the information they need and contribute data without confusion.
- **Guided Contributions**: Users are guided through the contribution process with clear instructions and prompts, ensuring that they understand what information is required and how to provide it.
- **Validation**: Input fields are validated to ensure that the data entered is accurate and conforms to the expected format. This helps maintain the integrity of the data in the system.

### Purpose and Architecture
The point of the 'Contribute' pages is to act as the **master queue for all missing data** relating to councils in a way that means users do not have to navigate to the pages of individual councils to contribute data. This allows for a more streamlined and efficient process for users to contribute information, ensuring that the system remains up-to-date and accurate.

### User Experience Goals
The 'Contribute' system is also supposed to be **fun and engaging**, encouraging users to participate and contribute data. The design and functionality of the 'Contribute' pages are intended to make the process enjoyable, fostering a sense of community and collaboration among users.

### Data Integrity Requirements
Above all, however, the 'Contribute' system **has to work**. When a user contributes data it must be applied to the council in question. There should be safeguards to prevent abuse, such as rate limiting and moderation, to ensure that the contributions are genuine and beneficial to the system.

### Moderation System
- **Light touch moderation**: Moderators can review changes to key data like council characteristics, but the system should be designed to allow for quick and easy contributions from users
- **Transparent feedback**: The system should provide users with feedback on their contributions. This could include notifications when their contributions are approved or if any issues arise that need to be addressed
- **Community validation**: Future aim for a 'blockchain' like experience whereby contributions are accepted and then confirmed by community members
- **Recognition system**: System of rewards or recognition for users who consistently contribute valuable data
- **Approval threshold**: If a contribution receives 15 upvotes or confirmations it is considered to be accurate and is applied to the council in question

### Integration Philosophy
The 'Contribute' pages are **not designed to replace** the existing council pages but rather to complement them. They provide a streamlined and efficient way for users to contribute data without having to navigate through multiple pages. We accept that some users will prefer to just contribute to their favourite council, such as the one where they live and may never use the 'Contribute' queues. Their submissions however are just as valid and should be treated in the same esteem.

---

## The 'Lists' Pages

The 'Lists' section allows users to create custom lists, similar to how 'wish lists' work in e-commerce. They allow the user to group councils together in any way they choose - for instance by geography or by council type, the possibilities are almost endless.

### Core Functionality
- **Custom grouping**: Users can group councils by any criteria (geography, council type, population size, etc.)
- **User-friendly management**: Lists are designed to be intuitive, allowing users to easily create, manage, and share their lists of councils
- **Data aggregation**: Data and counters can then be applied to the lists, allowing users to see totals such as total debt levels for all councils in a given list
- **Flexible organization**: The possibilities for list creation are almost endless, giving users complete control over how they organize council data

### Use Cases
- **Geographic analysis**: Group councils by region, county, or proximity
- **Comparative analysis**: Group similar council types for benchmarking
- **Personal interest**: Create lists of councils users are particularly interested in
- **Research purposes**: Organize councils for academic or professional research
- **Thematic grouping**: Group by political control, size, financial performance, etc.

---

## The 'Following' Page 

Users can 'follow' councils, similar to how people follow accounts on social media websites. This allows them to see updates relating to their followed councils.

### Follow Types and Content
#### Following Councils
- **Financial updates**: New reports being published or new financial information being made available
- **Contribution updates**: When contributions are approved they should push an update to the feed
- **Council activities**: Changes in council leadership, new initiatives, or community events
- **User engagement**: Users can comment on these feed items
- **Council engagement**: Acts as a hook for the council to engage with the platform to let people know what's going on

#### Following Lists
- **List updates**: Users can 'follow' lists, allowing them to see updates relating to the lists they are interested in
- **Content changes**: New councils being added to a list, changes in the financial figures of councils within a list, or other relevant updates
- **Collaborative features**: The 'Following' page is designed to be a central hub for users to stay connected with the councils and lists they care about

#### Following Financial Figures
- **Metric tracking**: Users can 'follow' individual financial figures, allowing them to see updates and changes to specific financial metrics across all councils
- **Trend analysis**: Changes in debt levels, budget allocations, or other key financial indicators
- **Cross-council insights**: By following these figures, users can stay informed about trends and developments in council finances that are of particular interest to them

#### Following Contributors
- **Community engagement**: Users can 'follow' specific contributors, allowing them to see updates and contributions made by those users
- **Activity tracking**: New data submissions, comments on council pages, or other relevant contributions
- **Network building**: By following contributors, users can engage more deeply with the community and stay informed about the work being done by others in the platform

### Personalization and Control
- **Priority settings**: Users can prioritise which updates they see first, allowing them to customize their feed based on their interests and preferences
- **Filtering options**: Options to filter updates by council, list, financial figure, or contributor, ensuring that users can easily find the information that matters most to them
- **Notification preferences**: Users can choose to receive notifications about updates to their followed councils, lists, financial figures, or contributors
- **Notification channels**: Email notifications, in-app alerts, or push notifications on mobile devices

### Analytics and Intelligence
Data and telemetry based on the 'Following' page and interactions therein should be collected to help improve the user experience and trigger algorithm-based features:

#### Trending Detection
- **Council promotion**: Where a council is suddenly getting a lot of follows, comments or visits we would want to look to promote that council and understand the reason for the attention
- **Interest analysis**: If a council is getting a lot of follows it may be because they are doing something interesting or have recently made a significant change that users want to know more about
- **Content discovery**: This could be a new initiative, a change in leadership, or a significant financial update
- **Homepage promotion**: By promoting these councils on the home page, we can help users discover new and relevant information that they may not have been aware of otherwise

#### Algorithmic Features
- **Smart recommendations**: Suggest councils, lists, or contributors based on following patterns
- **Trend identification**: Surface emerging stories or significant changes
- **Engagement optimization**: Use following data to improve content prioritization
- **Community insights**: Understand what drives user engagement and interest

---

## Backend Management Rule

No users, including the super-admin, should see any Django admin pages. The Django admin is not used in this project. Instead, we use a custom-built control panel for managing the system.

### Access Control
- **Super-admin exception**: Only the super-admin should be able to access Django admin pages by exception and in edge case scenarios
- **Limited scope**: Even then, it should be limited to specific tasks that cannot be done through the control panel
- **Custom control panel**: The control panel is designed to be user-friendly and intuitive, allowing administrators to manage the system without needing to navigate through complex Django admin pages

### Design Philosophy
The control panel prioritizes user experience over administrative convenience, ensuring that all management tasks can be performed through a consistent, well-designed interface that matches the rest of the application.

---

## User Levels and Permissions

This system is designed to accept contributions from the public via registered accounts, so that they may update the data relating to their own council. The user profile system also recognises and invites people who work for councils to provide us with data too.

### Tier System
The user levels are designed to reflect the different roles and responsibilities of users within the system, ensuring that contributions are appropriate and beneficial to the platform.

#### Tier 1 (Default Users)
- **Access level**: The default level for all users
- **Capabilities**: Can view and contribute data
- **Moderation**: Their contributions may require moderation depending on the type and other rules
- **Purpose**: General public engagement and basic contributions

#### Tier 2 (Consistent Contributors)
- **Access level**: Users who have demonstrated consistent and valuable contributions
- **Capabilities**: Can contribute data without moderation
- **Validation**: Their contributions are still subject to community validation
- **Purpose**: Experienced community members with proven track record

#### Tier 3 (Council Staff/Experts)
- **Access level**: Users who work for councils or have a proven track record of high-quality contributions
- **Capabilities**: Can contribute data without moderation and have access to additional features such as advanced analytics and reporting tools
- **Purpose**: Professional users with institutional knowledge

#### Tier 4 (Domain Experts)
- **Access level**: Users who are recognized as experts in the field, such as financial analysts or council officials
- **Capabilities**: All the privileges of Tier 3 users, plus the ability to create and manage custom lists and advanced data visualizations
- **Purpose**: Subject matter experts and power users

#### Tier 5 (God Mode)
- **Access level**: The highest level, reserved for trusted contributors and moderators
- **Capabilities**: Full access to all features, including the ability to approve or reject contributions from other users, manage user accounts, and access advanced administrative tools
- **Purpose**: System administrators and senior moderators

### Access Control Implementation
Components and features should be appropriately gated to their user level, ensuring that users only have access to the features and data that are relevant to their role within the system. This helps maintain the integrity of the platform and ensures that contributions are appropriate and beneficial to all users.

### Administrative Control Panel
There should be a control panel under God Mode to set permission levels for each tier and control what they each have access to. This control panel should be user-friendly and intuitive, allowing administrators to easily manage user levels and permissions without confusion.

### API Access
The system should also offer data via API, for which a secure key is required. This API should be designed to allow users to access and interact with the data in a secure and controlled manner, ensuring that sensitive information is protected while still allowing for valuable contributions and insights.

#### API Key Management
- **User-generated keys**: Users will be able to generate API keys from their user profile
- **Secure storage**: These keys should be securely stored and managed within the system
- **Comprehensive endpoints**: The API should support various endpoints for accessing council data, financial figures, and user contributions
- **Developer integration**: Allow developers to build applications and integrations that leverage the platform's data and functionality
- **Future monetization**: We may - or may not - charge for API access in the future

---

## AI Integration for User Assistance

The system is designed to leverage AI to assist users in various ways, enhancing the overall user experience and providing valuable insights into council data.

### AI Capabilities

#### Content Generation
- **Generate Factoids**: AI can analyze council data and generate interesting factoids based on trends, comparisons, and unique financial figures. This can help users quickly identify key insights without needing to manually sift through large datasets.

#### Recommendation Systems
- **Suggest Contributions**: AI can analyze user behavior and preferences to suggest relevant contributions, such as councils to follow, lists to create, or financial figures to track. This can help users discover new areas of interest and engage more deeply with the platform.
- **Suggest Lists**: AI can recommend custom lists for users based on their interests and contributions. This can help users organize and track relevant data more effectively.

#### Data Quality Assurance
- **Automate Data Validation**: AI can assist in validating user contributions by checking for consistency, accuracy, and relevance. This can help reduce the burden on moderators and ensure that contributions are appropriate and beneficial to the platform.

#### Enhanced User Experience
- **Enhance Search Functionality**: AI can improve search capabilities by understanding user intent and providing more relevant results based on context and user behavior. This can help users quickly find the information they need without having to navigate through multiple pages.
- **Suggest Fields and Characteristics**: AI can analyze existing council data and suggest new fields or characteristics that could be added to enhance the dataset. This can help keep the platform up-to-date with the latest trends and developments in council finances.

### Technical Implementation
The API key for OpenAI can be found in the .env file, and it should be used to access the AI capabilities within the system. The AI features should be designed to be user-friendly and intuitive, allowing users to easily access and benefit from the AI-generated insights and suggestions without requiring technical expertise.

### Integration Philosophy
AI should enhance rather than replace human decision-making and community engagement. The goal is to make the platform more intelligent and helpful while maintaining the human-centered approach to council finance transparency.