from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0007_backend_integrity"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailylog",
            name="review_remarks",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="dailylog",
            name="review_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending review"),
                    ("approved", "Approved"),
                    ("revision_requested", "Needs correction"),
                ],
                default="pending",
                max_length=24,
            ),
        ),
    ]
