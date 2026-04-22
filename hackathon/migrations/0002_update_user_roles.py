from django.db import migrations, models


def normalize_roles(apps, schema_editor):
    User = apps.get_model("hackathon", "User")
    role_mapping = {
        "participant": "PARTICIPANT",
        "mentor": "CAPTAIN",
        "captain": "CAPTAIN",
        "organizer": "ORGANIZER",
        "admin": "ADMIN",
    }
    for old_role, new_role in role_mapping.items():
        User.objects.filter(role=old_role).update(role=new_role)


class Migration(migrations.Migration):
    dependencies = [
        ("hackathon", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(normalize_roles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("PARTICIPANT", "Participant"),
                    ("CAPTAIN", "Captain"),
                    ("ORGANIZER", "Organizer"),
                    ("ADMIN", "Admin"),
                ],
                default="PARTICIPANT",
                max_length=32,
            ),
        ),
    ]
