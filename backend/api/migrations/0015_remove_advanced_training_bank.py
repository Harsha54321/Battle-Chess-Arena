from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_trainingpuzzleprogress_next_move_index'),
    ]

    operations = [
        migrations.DeleteModel(name='TrainingPuzzleProgress'),
        migrations.DeleteModel(name='TrainingLevelReview'),
        migrations.DeleteModel(name='TrainingPuzzle'),
        migrations.DeleteModel(name='TrainingMatchRecord'),
    ]
