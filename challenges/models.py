from django.db import models
from django.db.models import Avg


class Challenge(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    views = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

    @property
    def num_solves(self):
        return self.solves.count()

    @property
    def average_rating(self):
        avg = self.ratings.aggregate(Avg("stars"))["stars__avg"]
        return round(avg, 1) if avg else 0

    @property
    def average_difficulty(self):
        avg = self.difficulty_votes.aggregate(Avg("difficulty"))["difficulty__avg"]
        return round(avg, 1) if avg else 0


class TestCase(models.Model):
    challenge = models.ForeignKey(
        Challenge, related_name="testcases", on_delete=models.CASCADE
    )
    number = models.PositiveIntegerField()
    input_text = models.TextField(blank=True, null=True)
    input_file = models.FileField(upload_to="challenge_inputs/", blank=True, null=True)
    output_text = models.TextField(blank=True, null=True)
    output_file = models.FileField(
        upload_to="challenge_outputs/", blank=True, null=True
    )
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ["number"]
        unique_together = ("challenge", "number")

    def __str__(self):
        return f'{self.challenge.title} - Test Case {self.number} ({"Hidden" if self.is_hidden else "Public"})'


# Track unique views per session to prevent inflation
class ChallengeView(models.Model):
    challenge = models.ForeignKey(
        Challenge, related_name="unique_views", on_delete=models.CASCADE
    )
    session_key = models.CharField(max_length=64)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("challenge", "session_key")


# Session-based models: no User FK required
class Solve(models.Model):
    session_key = models.CharField(max_length=64)
    challenge = models.ForeignKey(
        Challenge, related_name="solves", on_delete=models.CASCADE
    )
    solved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("session_key", "challenge")


class Rating(models.Model):
    session_key = models.CharField(max_length=64)
    challenge = models.ForeignKey(
        Challenge, related_name="ratings", on_delete=models.CASCADE
    )
    stars = models.PositiveIntegerField(choices=[(i, str(i)) for i in range(1, 6)])

    class Meta:
        unique_together = ("session_key", "challenge")


DIFFICULTY_LABELS = {
    1: "Practice",
    2: "Very Easy",
    3: "Easy",
    4: "Medium-Easy",
    5: "Medium",
    6: "Medium-Hard",
    7: "Hard",
    8: "Very Hard",
    9: "Extreme",
    10: "Impossible",
}


class DifficultyVote(models.Model):
    session_key = models.CharField(max_length=64)
    challenge = models.ForeignKey(
        Challenge, related_name="difficulty_votes", on_delete=models.CASCADE
    )
    difficulty = models.PositiveIntegerField(
        choices=[(i, DIFFICULTY_LABELS[i]) for i in range(1, 11)]
    )

    class Meta:
        unique_together = ("session_key", "challenge")


class Comment(models.Model):
    session_key = models.CharField(max_length=64)
    nickname = models.CharField(max_length=50, default="Anonymous")
    challenge = models.ForeignKey(
        Challenge, related_name="comments", on_delete=models.CASCADE
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
