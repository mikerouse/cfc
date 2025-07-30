from django.conf import settings
from django.db import models
from django.db.models import Sum
from .council import Council

class CouncilList(models.Model):
    """User created collection of councils with enhanced metadata and functionality."""

    # Color choices for visual customization
    COLOR_CHOICES = [
        ('blue', 'Blue'),
        ('green', 'Green'), 
        ('purple', 'Purple'),
        ('red', 'Red'),
        ('yellow', 'Yellow'),
        ('indigo', 'Indigo'),
        ('pink', 'Pink'),
        ('gray', 'Gray'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="council_lists",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(
        blank=True, 
        null=True,
        help_text="Optional description or notes about this list"
    )
    councils = models.ManyToManyField(Council, blank=True)
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the user's default favourites list"
    )
    color = models.CharField(
        max_length=20,
        choices=COLOR_CHOICES,
        default='blue',
        help_text="Color theme for this list"
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-updated', 'name']
        constraints = [
            # Ensure only one default list per user
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_default=True),
                name='unique_default_list_per_user'
            )
        ]

    def __str__(self) -> str:
        default_marker = " [Default]" if self.is_default else ""
        return f"{self.name}{default_marker} ({self.user.username})"

    def get_total_population(self):
        """Calculate total population for all councils in this list."""
        from .council import CouncilCharacteristic
        from .field import DataField
        
        try:
            population_field = DataField.objects.get(slug='population')
            total = CouncilCharacteristic.objects.filter(
                council__in=self.councils.all(),
                field=population_field
            ).aggregate(
                total=Sum('value', output_field=models.IntegerField())
            )['total']
            return total or 0
        except (DataField.DoesNotExist, ValueError):
            return 0

    def get_council_count(self):
        """Get the number of councils in this list."""
        return self.councils.count()

    def get_css_color_classes(self):
        """Get Tailwind CSS classes for this list's color theme."""
        color_map = {
            'blue': 'bg-blue-50 border-blue-200 text-blue-800',
            'green': 'bg-green-50 border-green-200 text-green-800',
            'purple': 'bg-purple-50 border-purple-200 text-purple-800',
            'red': 'bg-red-50 border-red-200 text-red-800',
            'yellow': 'bg-yellow-50 border-yellow-200 text-yellow-800', 
            'indigo': 'bg-indigo-50 border-indigo-200 text-indigo-800',
            'pink': 'bg-pink-50 border-pink-200 text-pink-800',
            'gray': 'bg-gray-50 border-gray-200 text-gray-800',
        }
        return color_map.get(self.color, color_map['blue'])

    @classmethod
    def get_or_create_default_list(cls, user):
        """Get or create the user's default 'My Favourites' list."""
        default_list, created = cls.objects.get_or_create(
            user=user,
            is_default=True,
            defaults={
                'name': 'My Favourites',
                'description': 'Your favourite councils for quick access',
                'color': 'blue'
            }
        )
        return default_list, created
