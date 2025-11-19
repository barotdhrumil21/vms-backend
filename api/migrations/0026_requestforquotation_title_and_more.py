from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0025_auditlog_rfqitemattachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="requestforquotation",
            name="title",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]




