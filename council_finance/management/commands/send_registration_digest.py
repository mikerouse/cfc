"""
Management command to send daily digest of new user registrations.
Runs daily at midday to email admins about new registrations.
"""
import os
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from event_viewer.models import SystemEvent


class Command(BaseCommand):
    help = 'Send daily digest of new user registrations to administrators'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--test',
            action='store_true',
            help='Run in test mode (show output but don\'t send email)',
        )
        parser.add_argument(
            '--days-back',
            type=int,
            default=1,
            help='Number of days back to look for registrations (default: 1)',
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        test_mode = options.get('test', False)
        days_back = options.get('days_back', 1)
        
        if test_mode:
            self.stdout.write(self.style.WARNING('Running in TEST MODE - no emails will be sent'))
        
        # Get time range for yesterday's registrations
        end_time = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(days=days_back)
        
        self.stdout.write(f"Checking registrations from {start_time} to {end_time}")
        
        # Query for registration events
        registration_events = SystemEvent.objects.filter(
            source='user_onboarding',
            title='New User Registration Started',
            timestamp__gte=start_time,
            timestamp__lt=end_time
        ).order_by('-timestamp')
        
        # Query for completed onboarding events
        completed_events = SystemEvent.objects.filter(
            source='user_onboarding',
            title='Onboarding Completed Successfully',
            timestamp__gte=start_time,
            timestamp__lt=end_time
        ).select_related('user')
        
        # Get age verification events for demographics
        age_events = SystemEvent.objects.filter(
            source='osa_compliance',
            title='Age Verification Completed',
            timestamp__gte=start_time,
            timestamp__lt=end_time
        )
        
        # Calculate statistics
        total_registrations = registration_events.count()
        total_completed = completed_events.count()
        
        if total_registrations == 0:
            self.stdout.write(self.style.SUCCESS('No new registrations yesterday - skipping digest email'))
            return
        
        # Analyze user demographics
        uk_users = 0
        international_users = 0
        adult_users = 0
        minor_users = 0
        email_verified = 0
        
        for event in registration_events:
            details = event.details or {}
            if details.get('country_detected') == 'UK':
                uk_users += 1
            else:
                international_users += 1
            
            if details.get('email_verified'):
                email_verified += 1
        
        for event in age_events:
            details = event.details or {}
            if details.get('is_adult'):
                adult_users += 1
            else:
                minor_users += 1
        
        # Build registration details list
        registrations = []
        for reg_event in registration_events:
            # Find matching completion event if exists
            completion = None
            for comp_event in completed_events:
                if comp_event.user and comp_event.user.id == reg_event.user_id:
                    completion = comp_event
                    break
            
            # Find age verification if exists
            age_info = None
            for age_event in age_events:
                if age_event.user_id == reg_event.user_id:
                    age_info = age_event.details or {}
                    break
            
            reg_details = reg_event.details or {}
            registrations.append({
                'timestamp': reg_event.timestamp,
                'user': reg_event.user,
                'email': reg_event.user.email if reg_event.user else 'Unknown',
                'location': 'UK' if reg_details.get('country_detected') == 'UK' else 'International',
                'age': age_info.get('age') if age_info else None,
                'auth0_provider': reg_details.get('detection_data', {}).get('auth0_provider', ''),
                'completed': completion is not None,
                'completion_time': completion.timestamp if completion else None,
            })
        
        # Calculate completion rate
        completion_rate = (total_completed / total_registrations * 100) if total_registrations > 0 else 0
        
        # Get weekly comparison (if running for 1 day)
        weekly_comparison = ""
        if days_back == 1:
            week_ago_start = start_time - timedelta(days=7)
            week_ago_end = end_time - timedelta(days=7)
            
            last_week_registrations = SystemEvent.objects.filter(
                source='user_onboarding',
                title='New User Registration Started',
                timestamp__gte=week_ago_start,
                timestamp__lt=week_ago_end
            ).count()
            
            if last_week_registrations > 0:
                change = ((total_registrations - last_week_registrations) / last_week_registrations) * 100
                if change > 0:
                    weekly_comparison = f"Up {change:.1f}% from same day last week ({last_week_registrations} registrations)"
                else:
                    weekly_comparison = f"Down {abs(change):.1f}% from same day last week ({last_week_registrations} registrations)"
            else:
                weekly_comparison = f"No registrations on same day last week"
        
        # Prepare context for email template
        context = {
            'date': start_time.date(),
            'total_registrations': total_registrations,
            'total_completed': total_completed,
            'completion_rate': completion_rate,
            'uk_users': uk_users,
            'international_users': international_users,
            'adult_users': adult_users,
            'minor_users': minor_users,
            'email_verified': email_verified,
            'registrations': registrations,
            'weekly_comparison': weekly_comparison,
            'base_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000',
        }
        
        # Render email content
        subject = f"Daily Registration Summary - {start_time.date()}"
        html_content = render_to_string('emails/registration_digest.html', context)
        text_content = self._generate_text_content(context)
        
        if test_mode:
            self.stdout.write(self.style.SUCCESS(f"\nEmail Subject: {subject}"))
            self.stdout.write(self.style.SUCCESS(f"\nEmail Content (Text):\n{text_content}"))
            self.stdout.write(self.style.SUCCESS("\nTEST MODE - Email not sent"))
        else:
            # Get recipient email from settings
            recipient_email = os.getenv('ERROR_ALERTS_EMAIL_ADDRESS')
            if not recipient_email:
                self.stdout.write(self.style.ERROR('ERROR_ALERTS_EMAIL_ADDRESS not configured in .env'))
                return
            
            # Send email
            try:
                send_mail(
                    subject=subject,
                    message=text_content,
                    html_message=html_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f'Successfully sent registration digest to {recipient_email}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to send email: {str(e)}'))
    
    def _generate_text_content(self, context):
        """Generate plain text version of the email."""
        text = f"""
Daily Registration Summary - {context['date']}
{'=' * 50}

SUMMARY STATISTICS
------------------
Total Registrations: {context['total_registrations']}
Completed Onboarding: {context['total_completed']} ({context['completion_rate']:.1f}% completion rate)

User Demographics:
- UK Users: {context['uk_users']}
- International Users: {context['international_users']}
- Adults (18+): {context['adult_users']}
- Minors (<18): {context['minor_users']}
- Pre-verified Emails: {context['email_verified']}

{context['weekly_comparison']}

REGISTRATION DETAILS
-------------------
"""
        
        for reg in context['registrations']:
            status = "Completed" if reg['completed'] else "In Progress"
            age_str = f"{reg['age']} years" if reg['age'] else "Pending"
            text += f"\n{reg['timestamp'].strftime('%H:%M')} - {reg['email']} ({reg['location']}, Age: {age_str}) - {status}"
        
        text += f"\n\nView full details at: {context['base_url']}/system-events/"
        
        return text