# Generated by Django 3.2.3 on 2021-10-27 12:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='checkout_webhook_url',
            field=models.URLField(help_text='URL to receive checkout updates', null=True),
        ),
        migrations.AlterField(
            model_name='store',
            name='url',
            field=models.URLField(help_text='URL for your store public site or information page'),
        ),
    ]