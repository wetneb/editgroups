# Generated by Django 2.1.5 on 2019-06-20 10:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0016_change_batch_manager'),
    ]

    operations = [
        migrations.AddField(
            model_name='batch',
            name='last_modified',
            field=models.DateTimeField(auto_now=True),
        ),
    ]