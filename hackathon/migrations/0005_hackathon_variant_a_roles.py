import django.db.models.deletion
from django.db import migrations, models


def normalize_roles_variant_a(apps, schema_editor):
    User = apps.get_model("hackathon", "User")
    User.objects.filter(role__in=("ORGANIZER", "ADMIN")).update(role="PARTICIPANT")


class Migration(migrations.Migration):

    dependencies = [
        ("hackathon", "0004_alter_user_is_kaptain"),
    ]

    operations = [
        migrations.RunPython(normalize_roles_variant_a, migrations.RunPython.noop),
        migrations.CreateModel(
            name="Hackathon",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=64, unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "schedule_sheet_url",
                    models.URLField(
                        blank=True,
                        help_text="Ссылка на Google Таблицу с расписанием (опционально).",
                        max_length=500,
                    ),
                ),
                (
                    "is_team_join_open",
                    models.BooleanField(
                        default=True,
                        help_text="Капитаны могут подключать команды к этому хакатону.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_hackathons",
                        to="hackathon.user",
                    ),
                ),
                (
                    "organizers",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Права организатора только через эту связь (вариант A).",
                        related_name="organized_hackathons",
                        to="hackathon.user",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="HackathonTeam",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                (
                    "hackathon",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hackathon_teams",
                        to="hackathon.hackathon",
                    ),
                ),
                (
                    "team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hackathon_links",
                        to="hackathon.team",
                    ),
                ),
            ],
            options={
                "ordering": ("-joined_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="hackathonteam",
            constraint=models.UniqueConstraint(fields=("hackathon", "team"), name="uniq_hackathon_team"),
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[("PARTICIPANT", "Participant"), ("CAPTAIN", "Captain")],
                default="PARTICIPANT",
                max_length=32,
            ),
        ),
    ]
