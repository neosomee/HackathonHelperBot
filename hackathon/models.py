from django.db import models


class User(models.Model):
    class Role(models.TextChoices):
        PARTICIPANT = "participant", "Participant"
        MENTOR = "mentor", "Mentor"
        ORGANIZER = "organizer", "Organizer"

    telegram_id = models.BigIntegerField(unique=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    skills = models.TextField(blank=True)
    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.PARTICIPANT,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("full_name",)

    def __str__(self):
        return self.full_name


class Team(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    captain = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="captained_teams",
    )
    tech_stack = models.TextField(blank=True)
    vacancies = models.TextField(blank=True)
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class TeamMember(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="team_memberships",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="members",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "team"),
                name="unique_user_team_membership",
            ),
        ]

    def __str__(self):
        return f"{self.user} -> {self.team} ({self.status})"
