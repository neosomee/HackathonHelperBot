from django.test import TestCase, override_settings
from rest_framework import status

from hackathon.models import Hackathon, HackathonTeam, TeamMember, User
from hackathon.schedule_sheet import parse_schedule_csv
from hackathon.services import (
    ServiceError,
    apply_to_team,
    captain_join_hackathon,
    create_hackathon_by_user,
    create_team,
    decide_team_request,
    register_user,
    subscribe_hackathon_schedule,
)


class HackathonServiceTests(TestCase):
    def create_user(self, telegram_id, full_name="Test User", is_kaptain=False):
        user, created = register_user(
            telegram_id=telegram_id,
            full_name=full_name,
            email=f"user{telegram_id}@example.com",
            skills="Python, Django",
            is_kaptain=is_kaptain,
        )
        self.assertTrue(created)
        return user

    def create_team_with_captain(self):
        captain = self.create_user(1001, "Captain User", is_kaptain=True)
        team = create_team(
            captain_telegram_id=captain.telegram_id,
            name="Demo Team",
            description="Team for demo",
            tech_stack="Django, PostgreSQL",
            vacancies="Frontend developer",
        )
        return captain, team

    def test_register_user(self):
        user = self.create_user(1000, "Participant User")

        self.assertEqual(user.full_name, "Participant User")
        self.assertEqual(user.role, User.Role.PARTICIPANT)
        self.assertTrue(user.is_active)

    def test_create_team_adds_captain_as_accepted_member(self):
        captain, team = self.create_team_with_captain()
        captain.refresh_from_db()

        self.assertEqual(team.captain, captain)
        self.assertEqual(captain.role, User.Role.CAPTAIN)
        self.assertTrue(
            TeamMember.objects.filter(
                user=captain,
                team=team,
                status=TeamMember.Status.ACCEPTED,
            ).exists()
        )

    def test_apply_to_team_creates_pending_request(self):
        _, team = self.create_team_with_captain()
        user = self.create_user(1002, "Applicant User")

        application = apply_to_team(
            user_telegram_id=user.telegram_id,
            team_id=team.id,
        )

        self.assertEqual(application.status, TeamMember.Status.PENDING)
        self.assertEqual(application.user, user)
        self.assertEqual(application.team, team)

    def test_captain_accepts_request(self):
        captain, team = self.create_team_with_captain()
        user = self.create_user(1003, "Accepted User")
        apply_to_team(user_telegram_id=user.telegram_id, team_id=team.id)

        application = decide_team_request(
            captain_telegram_id=captain.telegram_id,
            user_telegram_id=user.telegram_id,
            team_id=team.id,
            decision="accept",
        )

        self.assertEqual(application.status, TeamMember.Status.ACCEPTED)

    def test_captain_rejects_request(self):
        captain, team = self.create_team_with_captain()
        user = self.create_user(1004, "Rejected User")
        apply_to_team(user_telegram_id=user.telegram_id, team_id=team.id)

        application = decide_team_request(
            captain_telegram_id=captain.telegram_id,
            user_telegram_id=user.telegram_id,
            team_id=team.id,
            decision="reject",
        )

        self.assertEqual(application.status, TeamMember.Status.REJECTED)

    def test_user_cannot_apply_to_same_team_twice(self):
        _, team = self.create_team_with_captain()
        user = self.create_user(1005, "Duplicate Applicant")
        apply_to_team(user_telegram_id=user.telegram_id, team_id=team.id)

        with self.assertRaises(ServiceError) as context:
            apply_to_team(user_telegram_id=user.telegram_id, team_id=team.id)

        self.assertEqual(context.exception.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(context.exception.message, "Application already exists.")

    def test_user_in_team_cannot_create_team(self):
        captain, team = self.create_team_with_captain()
        user = self.create_user(1006, "Team Member", is_kaptain=True)
        apply_to_team(user_telegram_id=user.telegram_id, team_id=team.id)
        decide_team_request(
            captain_telegram_id=captain.telegram_id,
            user_telegram_id=user.telegram_id,
            team_id=team.id,
            decision="accept",
        )

        with self.assertRaises(ServiceError) as context:
            create_team(
                captain_telegram_id=user.telegram_id,
                name="Another Team",
                description="Should not be created",
                tech_stack="Django",
                vacancies="Designer",
            )

        self.assertEqual(context.exception.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(context.exception.message, "User is already in a team.")

    def test_non_captain_cannot_process_request(self):
        _, team = self.create_team_with_captain()
        user = self.create_user(1007, "Applicant")
        other_user = self.create_user(1008, "Not Captain")
        apply_to_team(user_telegram_id=user.telegram_id, team_id=team.id)

        with self.assertRaises(ServiceError) as context:
            decide_team_request(
                captain_telegram_id=other_user.telegram_id,
                user_telegram_id=user.telegram_id,
                team_id=team.id,
                decision="accept",
            )

        self.assertEqual(context.exception.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            context.exception.message,
            "Only team captain can decide requests.",
        )

    def test_captain_join_hackathon(self):
        captain, team = self.create_team_with_captain()
        hackathon = Hackathon.objects.create(name="Spring", slug="spring", created_by=captain)
        link = captain_join_hackathon(
            captain_telegram_id=captain.telegram_id,
            hackathon_id=hackathon.id,
        )
        self.assertEqual(link.team_id, team.id)
        self.assertEqual(link.hackathon_id, hackathon.id)

        with self.assertRaises(ServiceError) as ctx:
            captain_join_hackathon(
                captain_telegram_id=captain.telegram_id,
                hackathon_id=hackathon.id,
            )
        self.assertEqual(ctx.exception.status_code, status.HTTP_409_CONFLICT)

    @override_settings(ORGANIZER_BOOTSTRAP_TELEGRAM_IDS=frozenset({888001}))
    def test_create_hackathon_bootstrap_adds_organizer(self):
        user = self.create_user(888001)
        hackathon = create_hackathon_by_user(telegram_id=888001, name="Bootstrap Event")
        self.assertTrue(hackathon.organizers.filter(pk=user.pk).exists())
        self.assertEqual(hackathon.created_by_id, user.id)

    @override_settings(ORGANIZER_BOOTSTRAP_TELEGRAM_IDS=frozenset())
    def test_create_hackathon_denied_without_rights(self):
        self.create_user(888002)
        with self.assertRaises(ServiceError) as ctx:
            create_hackathon_by_user(telegram_id=888002, name="No Access")
        self.assertEqual(ctx.exception.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(ORGANIZER_BOOTSTRAP_TELEGRAM_IDS=frozenset())
    def test_organizer_can_create_another_hackathon(self):
        captain = self.create_user(888003, is_kaptain=True)
        first = Hackathon.objects.create(name="First", slug="first-888003", created_by=captain)
        first.organizers.add(captain)
        second = create_hackathon_by_user(telegram_id=captain.telegram_id, name="Second Event")
        self.assertNotEqual(second.id, first.id)
        self.assertTrue(second.organizers.filter(pk=captain.pk).exists())

    def test_register_sets_can_create_hackathons(self):
        user, created = register_user(
            telegram_id=77010,
            full_name="Org Reg",
            email="orgreg@example.com",
            skills="Django",
            can_create_hackathons=True,
        )
        self.assertTrue(created)
        user.refresh_from_db()
        self.assertTrue(user.can_create_hackathons)

    def test_parse_schedule_csv_basic(self):
        text = "start,title,notify_minutes_before\n2030-06-01 10:00,Opening,10\n"
        rows = parse_schedule_csv(text)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].title, "Opening")
        self.assertEqual(rows[0].notify_minutes_before, 10)

    def test_subscribe_schedule_requires_team_on_hackathon(self):
        captain, team = self.create_team_with_captain()
        hackathon = Hackathon.objects.create(name="HSub", slug="h-sub-1", created_by=captain)
        hackathon.schedule_sheet_url = "https://docs.google.com/spreadsheets/d/test/edit"
        hackathon.save()

        with self.assertRaises(ServiceError) as ctx:
            subscribe_hackathon_schedule(
                telegram_id=captain.telegram_id,
                hackathon_id=hackathon.id,
            )
        self.assertEqual(ctx.exception.status_code, status.HTTP_403_FORBIDDEN)

        HackathonTeam.objects.create(hackathon=hackathon, team=team)
        subscribe_hackathon_schedule(
            telegram_id=captain.telegram_id,
            hackathon_id=hackathon.id,
        )
