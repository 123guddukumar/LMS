# Generated by Django 4.2 on 2025-06-10 20:17

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0006_lessonprogress_last_accessed_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="enrollment",
            name="enrollment_date",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
    ]
