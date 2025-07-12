from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("council_finance", "0043_activity_log_request"),
    ]

    operations = [
        migrations.RenameField(
            model_name="activitylog",
            old_name="button",
            new_name="log_type",
        ),
        migrations.AlterField(
            model_name="activitylog",
            name="log_type",
            field=models.CharField(max_length=20, choices=[("user", "User Activity"), ("debug", "Function Debug")], default="user"),
        ),
    ]
