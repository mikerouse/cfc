"""
Test command for the new data architecture.
This creates sample data to test the new models.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from council_finance.models import Council, DataField, FinancialYear
from council_finance.models.new_data_model import (
    CouncilCharacteristic,
    FinancialFigure,
    ContributionV2
)


class Command(BaseCommand):
    help = 'Create test data for the new data architecture'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test data first',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write("🧹 Clearing existing test data...")
            CouncilCharacteristic.objects.all().delete()
            FinancialFigure.objects.all().delete()
            ContributionV2.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("✅ Test data cleared"))
            return

        self.stdout.write("🚀 Creating test data for new architecture...")
        
        # Get or create test objects
        council = Council.objects.first()
        if not council:
            self.stdout.write(self.style.ERROR("❌ No councils found. Please create a council first."))
            return
        
        # Find characteristic and financial fields
        try:
            hq_field = DataField.objects.get(slug='council_hq_post_code')
        except DataField.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ council_hq_post_code field not found"))
            return
        
        # Find or create financial field
        try:
            debt_field = DataField.objects.get(slug='total_debt')
        except DataField.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ total_debt field not found"))
            return
        
        # Get financial year
        year = FinancialYear.objects.first()
        if not year:
            year = FinancialYear.objects.create(
                label='2023-24'
            )
        
        # Get or create test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        # Create sample characteristic
        characteristic, created = CouncilCharacteristic.objects.get_or_create(
            council=council,
            field=hq_field,
            defaults={
                'value': 'SW1A 1AA',
                'updated_by': user
            }
        )
        
        if created:
            self.stdout.write(f"✅ Created characteristic: {council.name} - {hq_field.name} = {characteristic.value}")
        else:
            self.stdout.write(f"ℹ️  Characteristic already exists: {council.name} - {hq_field.name} = {characteristic.value}")
        
        # Create sample financial figure
        figure, created = FinancialFigure.objects.get_or_create(
            council=council,
            field=debt_field,
            year=year,
            defaults={
                'value': '50000000',
                'updated_by': user
            }
        )
        
        if created:
            self.stdout.write(f"✅ Created financial figure: {council.name} - {debt_field.name} ({year.label}) = £{figure.value}")
        else:
            self.stdout.write(f"ℹ️  Financial figure already exists: {council.name} - {debt_field.name} ({year.label}) = £{figure.value}")
        
        # Create sample pending contribution
        contribution, created = ContributionV2.objects.get_or_create(
            user=user,
            council=council,
            field=hq_field,
            year=None,  # Characteristics don't have years
            value='SW1A 2BB',
            current_value=characteristic.value,
            defaults={
                'source_description': 'Updated from council website',
                'status': 'pending'
            }
        )
        
        if created:
            self.stdout.write(f"✅ Created pending contribution: {council.name} - {hq_field.name} = {contribution.value}")
        else:
            self.stdout.write(f"ℹ️  Pending contribution already exists: {council.name} - {hq_field.name} = {contribution.value}")
        
        self.stdout.write(self.style.SUCCESS("🎉 Test data creation completed!"))
        
        # Show summary
        self.stdout.write(f"\n📊 Summary:")
        self.stdout.write(f"   • Council characteristics: {CouncilCharacteristic.objects.count()}")
        self.stdout.write(f"   • Financial figures: {FinancialFigure.objects.count()}")
        self.stdout.write(f"   • Pending contributions: {ContributionV2.objects.filter(status='pending').count()}")
        
        self.stdout.write(f"\n🔗 Next steps:")
        self.stdout.write(f"   • Visit /contribute/pending_v2/ to see pending contributions")
        self.stdout.write(f"   • Test the new contribution system")
        self.stdout.write(f"   • Run migration: python manage.py migrate_to_new_data_model --dry-run")
