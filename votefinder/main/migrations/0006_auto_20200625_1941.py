# Generated by Django 2.2.13 on 2020-06-25 19:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_auto_20200625_1940'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='game',
            unique_together={('thread_id', 'home_forum')},
        ),
    ]
