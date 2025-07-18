"""
Functions moved from general.py to other modules:

API module (api.py):
- search_councils
- list_field_options
- field_info_api
- council_recent_activity_api
- field_recent_activity_api
- user_preferences_ajax

Auth module (auth.py):
- signup_view
- confirm_email
- resend_confirmation
- profile_view
- user_preferences_view
- update_postcode
- confirm_profile_change
- notifications_page
- mark_notification_read
- mark_all_notifications_read
- dismiss_notification
- my_profile

Moderation module (moderation.py):
- flag_content
- flagged_content_list
- resolve_flag
- take_content_action
- take_user_action
- my_flags
- moderator_panel (from contrib_views)

Councils module (councils.py):
- council_list
- council_detail
- council_counters
- council_change_log
- edit_figures_table
- generate_share_link
- leaderboards

Pages module (pages.py):
- home
- about
- terms_of_use
- privacy_cookies
- corrections

These functions should be removed from general.py to avoid duplication.
"""

# This is a documentation file to track what was moved
