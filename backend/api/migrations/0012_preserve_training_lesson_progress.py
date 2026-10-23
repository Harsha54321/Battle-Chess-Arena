from django.db import migrations


LEGACY_LESSON_IDS = {
	'foundation-mate': 'mate-fundamentals',
	'fools-mate': 'king-safety-calculation',
}


def preserve_legacy_progress(apps, schema_editor):
	Progress = apps.get_model('api', 'TrainingLessonProgress')
	database = schema_editor.connection.alias
	for old_id, new_id in LEGACY_LESSON_IDS.items():
		for old_progress in Progress.objects.using(database).filter(lesson_id=old_id):
			new_progress = Progress.objects.using(database).filter(
				player_id=old_progress.player_id,
				lesson_id=new_id,
			).first()
			if new_progress:
				new_progress.attempts += old_progress.attempts
				if old_progress.completed_at and (
					new_progress.completed_at is None
					or old_progress.completed_at < new_progress.completed_at
				):
					new_progress.completed_at = old_progress.completed_at
				new_progress.save(update_fields=['attempts', 'completed_at'])
				old_progress.delete()
			else:
				old_progress.lesson_id = new_id
				old_progress.save(update_fields=['lesson_id'])


class Migration(migrations.Migration):

	dependencies = [
		('api', '0011_traininglessonprogress_trainingmatchrecord'),
	]

	operations = [
		migrations.RunPython(preserve_legacy_progress, migrations.RunPython.noop),
	]
