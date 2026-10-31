from django.conf import settings
from django.db import migrations, models


def keep_one_membership_per_user(apps, schema_editor):
    RoomPlayer = apps.get_model('rooms', 'RoomPlayer')
    db = schema_editor.connection.alias
    seen_users = set()
    memberships = RoomPlayer.objects.using(db).order_by('-joined_at', '-id').iterator()
    for membership in memberships:
        if membership.user_id in seen_users:
            membership.delete()
        else:
            seen_users.add(membership.user_id)


class Migration(migrations.Migration):
    # PostgreSQL may reject AddConstraint in the same transaction as deletes
    # because the deletes leave pending trigger events. Commit the cleanup
    # before changing the table schema.
    atomic = False

    dependencies = [
        ('rooms', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(keep_one_membership_per_user, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='roomplayer',
            constraint=models.UniqueConstraint(fields=('user',), name='unique_user_room_membership'),
        ),
    ]
