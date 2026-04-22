# Generated for the hackathon backend initial schema.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("telegram_id", models.BigIntegerField(unique=True)),
                ("full_name", models.CharField(max_length=255)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("skills", models.TextField(blank=True)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("participant", "Participant"),
                            ("mentor", "Mentor"),
                            ("organizer", "Organizer"),
                        ],
                        default="participant",
                        max_length=32,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ("full_name",),
            },
        ),
        migrations.CreateModel(
            name="Team",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("tech_stack", models.TextField(blank=True)),
                ("vacancies", models.TextField(blank=True)),
                ("is_open", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "captain",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="captained_teams",
                        to="hackathon.user",
                    ),
                ),
            ],
            options={
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="TeamMember",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="members",
                        to="hackathon.team",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="team_memberships",
                        to="hackathon.user",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "team"),
                        name="unique_user_team_membership",
                    ),
                ],
            },
        ),
    ]
