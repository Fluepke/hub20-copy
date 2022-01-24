# Generated by Django 4.0 on 2022-01-24 03:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ethereum_money', '0013_alter_ethereumtoken_logouri_alter_usertokenlist_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='tokenlist',
            name='version',
            field=models.CharField(default='1.0.0', max_length=32),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='tokenlist',
            unique_together={('url', 'version')},
        ),
    ]