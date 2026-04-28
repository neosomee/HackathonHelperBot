from django.db import models


class User(models.Model):
    class Role(models.TextChoices):
        PARTICIPANT = "PARTICIPANT", "Participant"
        CAPTAIN = "CAPTAIN", "Captain"
        ORGANIZER = "ORGANIZER", "Organizer"
        ADMIN = "ADMIN", "Admin"

    telegram_id = models.BigIntegerField(unique=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    skills = models.TextField(blank=True)

    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.PARTICIPANT,
    )

    is_kaptain = models.BooleanField(
        default=False,
        help_text="Auto-synced with role=CAPTAIN",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("full_name",)

    def save(self, *args, **kwargs):
        self.is_kaptain = self.role == self.Role.CAPTAIN
        super().save(*args, **kwargs)

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

    max_members = models.PositiveSmallIntegerField(default=5)

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

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)

    status = models.CharField(max_length=20, choices=Status.choices)

    telegram_message_id = models.BigIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "team"], name="uniq_user_team")
        ]

    def __str__(self):
        return f"{self.user} -> {self.team} ({self.status})"