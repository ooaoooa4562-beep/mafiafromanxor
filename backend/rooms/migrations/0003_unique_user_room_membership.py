from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('rooms', '0002_one_room_per_user'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='roomplayer',
            constraint=models.UniqueConstraint(fields=('user',), name='unique_user_room_membership'),
        ),
    ]
