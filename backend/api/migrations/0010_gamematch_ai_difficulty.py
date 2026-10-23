from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_matchmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamematch',
            name='ai_difficulty',
            field=models.CharField(
                choices=[
                    ('beginner', 'Beginner'),
                    ('intermediate', 'Intermediate'),
                    ('advanced', 'Advanced'),
                ],
                default='beginner',
                max_length=20,
            ),
        ),
    ]
