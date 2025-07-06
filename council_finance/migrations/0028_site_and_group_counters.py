from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("council_finance", "0027_add_counter_council_types_capabilities"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteCounter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(unique=True)),
                ("duration", models.PositiveIntegerField(default=2000)),
                ("precision", models.PositiveIntegerField(default=0)),
                (
                    "show_currency",
                    models.BooleanField(default=True, help_text="Prefix with £ and include comma separators"),
                ),
                (
                    "friendly_format",
                    models.BooleanField(default=False, help_text="Use short forms e.g. £1m"),
                ),
                (
                    "promote_homepage",
                    models.BooleanField(default=False, help_text="Show on the home page"),
                ),
                (
                    "counter",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="council_finance.counterdefinition"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="GroupCounter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(unique=True)),
                ("duration", models.PositiveIntegerField(default=2000)),
                ("precision", models.PositiveIntegerField(default=0)),
                (
                    "show_currency",
                    models.BooleanField(default=True, help_text="Prefix with £ and include comma separators"),
                ),
                (
                    "friendly_format",
                    models.BooleanField(default=False, help_text="Use short forms e.g. £1m"),
                ),
                (
                    "promote_homepage",
                    models.BooleanField(default=False, help_text="Show on the home page"),
                ),
                (
                    "council_list",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="council_finance.councillist"),
                ),
                (
                    "counter",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="council_finance.counterdefinition"),
                ),
                (
                    "council_types",
                    models.ManyToManyField(blank=True, to="council_finance.counciltype"),
                ),
                (
                    "councils",
                    models.ManyToManyField(blank=True, to="council_finance.council"),
                ),
            ],
        ),
    ]
