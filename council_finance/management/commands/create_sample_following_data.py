from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
import random

from council_finance.models import (
    Council, FollowableItem, FeedUpdate, FeedInteraction, 
    FeedComment, UserFeedPreferences, TrendingContent,
    CouncilList, DataField
)


class Command(BaseCommand):
    help = 'Create sample following data for testing the enhanced Following page'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=5,
            help='Number of sample users to create',
        )
        parser.add_argument(
            '--updates',
            type=int,
            default=20,
            help='Number of sample feed updates to create',
        )

    def handle(self, *args, **options):
        self.stdout.write('Creating sample following data...')
        
        # Create sample users if they don't exist
        users = []
        for i in range(options['users']):
            username = f'user{i+1}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': f'User',
                    'last_name': f'{i+1}',
                    'is_active': True,
                }
            )
            users.append(user)
            if created:
                self.stdout.write(f'Created user: {username}')
        
        # Create feed preferences for each user
        for user in users:
            preferences, created = UserFeedPreferences.objects.get_or_create(
                user=user,
                defaults={
                    'algorithm': random.choice(['chronological', 'engagement', 'priority', 'mixed']),
                    'show_financial_updates': random.choice([True, False]),
                    'show_contributions': random.choice([True, False]),
                    'show_council_news': random.choice([True, False]),
                    'show_list_changes': random.choice([True, False]),
                    'show_system_updates': random.choice([True, False]),
                    'show_achievements': random.choice([True, False]),
                }
            )
            if created:
                self.stdout.write(f'Created feed preferences for {user.username}')
        
        # Get some councils and create follows
        councils = list(Council.objects.all()[:10])
        council_ct = ContentType.objects.get_for_model(Council)
        
        for user in users:
            # Each user follows 3-5 random councils
            followed_councils = random.sample(councils, min(len(councils), random.randint(3, 5)))
            for council in followed_councils:
                follow, created = FollowableItem.objects.get_or_create(
                    user=user,
                    content_type=council_ct,
                    object_id=council.id,
                    defaults={
                        'priority': random.choice(['low', 'normal', 'high', 'critical']),
                        'email_notifications': random.choice([True, False]),
                        'push_notifications': random.choice([True, False]),
                    }
                )
                if created:
                    self.stdout.write(f'{user.username} now follows {council.name}')
        
        # Create sample feed updates
        update_types = ['financial', 'contribution', 'council_news', 'list_change', 'system', 'achievement']
        update_titles = {
            'financial': [
                'Updated 2023 Financial Data',
                'New Budget Figures Released',
                'Quarterly Financial Report Published',
                'Capital Expenditure Updated',
                'Revenue Figures Revised'
            ],
            'contribution': [
                'Community member contributed new data',
                'Financial figures verified by expert',
                'Council website information updated',
                'Population data contribution accepted',
                'Budget analysis contribution approved'
            ],
            'council_news': [
                'Council announces new green initiative',
                'Mayor elected for new term',
                'New council meeting schedule published',
                'Public consultation period begins',
                'Council wins national award'
            ],
            'list_change': [
                'Added to "High Performing Councils" list',
                'Removed from "Budget Concerns" list',
                'Featured in "Innovation Leaders" collection',
                'Added to "Rural Development Focus" list',
                'Updated in "Metropolitan Areas" classification'
            ],
            'system': [
                'System maintenance completed',
                'New features available',
                'Data validation improved',
                'Performance enhancements deployed',
                'Security updates applied'
            ],
            'achievement': [
                'Reached 100 contributions milestone!',
                'Achieved "Data Expert" status',
                'Completed first financial audit',
                'Earned "Community Helper" badge',
                'Unlocked advanced analytics features'
            ]
        }
        
        for i in range(options['updates']):
            update_type = random.choice(update_types)
            council = random.choice(councils)
            author = random.choice(users) if random.choice([True, False]) else None
            
            # Create feed update
            update = FeedUpdate.objects.create(
                content_type=council_ct,
                object_id=council.id,
                update_type=update_type,
                title=random.choice(update_titles[update_type]),
                message=f"This is a sample {update_type.replace('_', ' ')} update for {council.name}. "
                       f"Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                       f"Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                author=author,
                is_public=True,
                targeted_followers_only=random.choice([True, False]),
                created_at=timezone.now() - timedelta(
                    hours=random.randint(1, 168)  # Random time in last week
                ),
                view_count=random.randint(0, 100),
                like_count=random.randint(0, 25),
                comment_count=random.randint(0, 10),
                share_count=random.randint(0, 5),
                rich_content={
                    'tags': random.sample(['urgent', 'budget', 'planning', 'community', 'development'], 
                                        random.randint(0, 3)),
                    'related_figures': [f'figure_{random.randint(1, 10)}' for _ in range(random.randint(0, 3))],
                    'attachments': []
                }
            )
            
            # Create some interactions for this update
            interacting_users = random.sample(users, random.randint(0, len(users)))
            for user in interacting_users:
                if random.choice([True, False]):  # 50% chance of interaction
                    interaction_type = random.choice(['like', 'share', 'bookmark'])
                    FeedInteraction.objects.get_or_create(
                        user=user,
                        update=update,
                        interaction_type=interaction_type,
                        defaults={
                            'created_at': update.created_at + timedelta(
                                minutes=random.randint(1, 60)
                            )
                        }
                    )
            
            # Create some comments
            commenting_users = random.sample(users, random.randint(0, min(3, len(users))))
            for user in commenting_users:
                comment = FeedComment.objects.create(
                    user=user,
                    update=update,
                    content=f"Great update! Thanks for keeping us informed about {council.name}.",
                    created_at=update.created_at + timedelta(
                        minutes=random.randint(1, 120)
                    ),
                    like_count=random.randint(0, 5)
                )
        
        # Create some trending content
        for council in random.sample(councils, min(5, len(councils))):
            TrendingContent.objects.create(
                content_type=council_ct,
                object_id=council.id,
                trend_score=random.uniform(0.5, 10.0),
                follow_velocity=random.uniform(0.1, 2.0),
                engagement_velocity=random.uniform(0.2, 3.0),
                view_velocity=random.uniform(0.5, 5.0),
                period_start=timezone.now() - timedelta(days=7),
                period_end=timezone.now(),
                reason=f"High engagement with {council.name} financial updates",
                is_promoted=random.choice([True, False])
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created sample following data:\n'
                f'- {len(users)} users\n'
                f'- {options["updates"]} feed updates\n'
                f'- Multiple follows, interactions, and comments\n'
                f'- {TrendingContent.objects.count()} trending items'
            )
        )
