from django.test import TestCase, Client
from django.urls import reverse
from .models import (
    Challenge,
    TestCase as TC,
    Solve,
    Rating,
    DifficultyVote,
    Comment,
    ChallengeView,
)


class ChallengeFeatureTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.challenge = Challenge.objects.create(
            title="Test Challenge", description="This is a test challenge"
        )
        TC.objects.create(
            challenge=self.challenge,
            number=1,
            input_text="1 2",
            output_text="3",
            is_hidden=False,
        )

    def test_challenge_list_sorting(self):
        url = reverse("challenge_list")
        response = self.client.get(url, {"sort": "newest"})
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url, {"sort": "stars"})
        self.assertEqual(response.status_code, 200)

    def test_challenge_list_search(self):
        url = reverse("challenge_list")
        response = self.client.get(url, {"q": "Test"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Challenge")

        response = self.client.get(url, {"q": "nonexistent"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Test Challenge")

    def test_challenge_detail_view(self):
        url = reverse("challenge_detail", args=[self.challenge.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # first visit
        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.views, 1)

        # second visit from same session should NOT increment
        response = self.client.get(url)
        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.views, 1)

    def test_submit_rating(self):
        url = reverse("challenge_rate", args=[self.challenge.pk])
        response = self.client.post(url, {"stars": 4})
        self.assertEqual(response.status_code, 302)

        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.average_rating, 4.0)

    def test_submit_difficulty(self):
        url = reverse("challenge_difficulty", args=[self.challenge.pk])
        response = self.client.post(url, {"difficulty": 7})
        self.assertEqual(response.status_code, 302)

        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.average_difficulty, 7.0)

    def test_submit_comment(self):
        url = reverse("challenge_comment", args=[self.challenge.pk])
        response = self.client.post(
            url, {"text": "Nice challenge!", "nickname": "Tester"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.challenge.comments.count(), 1)
        self.assertEqual(self.challenge.comments.first().nickname, "Tester")
