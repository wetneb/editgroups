# Generated by Django 2.0.3 on 2018-03-13 17:05

from django.db import migrations, models


def compute_nb_reverted_edits(apps, schema_editor):
    Batch = apps.get_model('store', 'Batch')
    for idx, batch in enumerate(Batch.objects.all().iterator()):
        if idx % 1000 == 0:
            print(idx)
        batch.nb_new_pages = batch.edits.all().filter(changetype='new').count()
        batch.nb_reverted_edits = batch.edits.filter(reverted=True).count()
        batch.save(update_fields=['nb_new_pages', 'nb_reverted_edits'])

def do_nothing(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0011_batch_nb_reverted_edits'),
    ]

    operations = [
        migrations.RunPython(
            compute_nb_reverted_edits, do_nothing
        ),
    ]
