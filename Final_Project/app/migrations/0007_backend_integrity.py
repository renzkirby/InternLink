from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0006_company_school"),
    ]

    operations = [
        migrations.AlterField(
            model_name="internship",
            name="required_hours",
            field=models.PositiveIntegerField(default=600),
        ),
        migrations.AddConstraint(
            model_name="internship",
            constraint=models.UniqueConstraint(
                condition=Q(("status", "ongoing")),
                fields=("student",),
                name="unique_ongoing_internship_per_student",
            ),
        ),
        migrations.AddConstraint(
            model_name="internship",
            constraint=models.CheckConstraint(
                condition=Q(("required_hours__gt", 0)),
                name="internship_required_hours_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="dailylog",
            constraint=models.UniqueConstraint(
                fields=("internship", "date"),
                name="unique_daily_log_per_internship_date",
            ),
        ),
        migrations.AlterField(
            model_name="evaluation",
            name="evaluator_role",
            field=models.CharField(
                choices=[("supervisor", "Supervisor"), ("coordinator", "Coordinator")],
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name="evaluation",
            constraint=models.UniqueConstraint(
                fields=("internship", "evaluator_role"),
                name="unique_evaluation_per_role",
            ),
        ),
    ]
