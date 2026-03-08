from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.db import transaction
from django.db.models import Count, Avg, Q
from django.contrib import messages
from .models import (
    Challenge,
    TestCase,
    ChallengeView,
    Solve,
    Rating,
    DifficultyVote,
    Comment,
    DIFFICULTY_LABELS,
)
from .forms import ChallengeForm

MAX_PREVIEW_CHARS = 2000


def _read_file_preview(file_field):
    """return string if <= MAX_PREVIEW_CHARS, else/except None."""
    if not file_field:
        return None
    try:
        file_field.open("rb")
        content = file_field.read()
        file_field.close()

        if b"\x00" in content:
            return "[Binary Data]"

        text = content.decode("utf-8")
        if len(text) <= MAX_PREVIEW_CHARS:
            return text
    except UnicodeDecodeError:
        return "[Binary Data / Invalid Text Encoding]"
    except Exception:
        pass
    return None


# TODO: figure out how to be less suceptible to malicious usage?
# TODO: - proof of work before giving out session key? (would be fine for views/ratings, but what about comments in discussion?)
# TODO: - ???
def _get_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def challenge_list(request):
    sort_by = request.GET.get("sort", "newest")
    search_q = request.GET.get("q", "").strip()
    min_diff = request.GET.get("min_diff", "")
    max_diff = request.GET.get("max_diff", "")
    min_stars = request.GET.get("min_stars", "")

    challenges = Challenge.objects.annotate(
        solves_count=Count("solves", distinct=True),
        avg_stars=Avg("ratings__stars"),
        avg_diff=Avg("difficulty_votes__difficulty"),
    )

    # Search filter
    if search_q:
        challenges = challenges.filter(title__icontains=search_q)

    # Difficulty filter
    if min_diff:
        try:
            challenges = challenges.filter(avg_diff__gte=float(min_diff))
        except (ValueError, TypeError):
            pass
    if max_diff:
        try:
            challenges = challenges.filter(avg_diff__lte=float(max_diff))
        except (ValueError, TypeError):
            pass

    # Min stars filter
    if min_stars:
        try:
            challenges = challenges.filter(avg_stars__gte=float(min_stars))
        except (ValueError, TypeError):
            pass

    # Sorting
    valid_sorts = {
        "newest": "-created_at",
        "oldest": "created_at",
        "views": "-views",
        "solves": "-solves_count",
        "stars": "-avg_stars",
        "difficulty_hard": "-avg_diff",
        "difficulty_easy": "avg_diff",
    }
    db_sort = valid_sorts.get(sort_by, "-created_at")
    challenges = challenges.order_by(db_sort)

    return render(
        request,
        "challenges/challenge_list.html",
        {
            "challenges": challenges,
            "current_sort": sort_by,
            "search_q": search_q,
            "min_diff": min_diff,
            "max_diff": max_diff,
            "min_stars": min_stars,
        },
    )


def challenge_detail(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk)
    session_key = _get_session_key(request)

    # Unique view tracking
    _, created = ChallengeView.objects.get_or_create(
        challenge=challenge, session_key=session_key
    )
    if created:
        challenge.views += 1
        challenge.save(update_fields=["views"])

    public_tests = challenge.testcases.filter(is_hidden=False)
    hidden_tests = challenge.testcases.filter(is_hidden=True)

    # Enrich test cases with preview data
    def enrich(tc):
        tc.input_preview = tc.input_text or _read_file_preview(tc.input_file)
        tc.output_preview = tc.output_text or _read_file_preview(tc.output_file)
        return tc

    public_tests = [enrich(tc) for tc in public_tests]
    hidden_tests_list = [enrich(tc) for tc in hidden_tests]

    is_solved = challenge.solves.filter(session_key=session_key).exists()

    if not hidden_tests.exists():
        is_solved = True

    show_spoilers = request.GET.get("spoilers") == "1"
    comments = challenge.comments.all()

    # Check if user already rated/voted
    has_rated = Rating.objects.filter(
        session_key=session_key, challenge=challenge
    ).exists()
    has_voted_diff = DifficultyVote.objects.filter(
        session_key=session_key, challenge=challenge
    ).exists()

    # Solved test cases from session
    solved_tcs = request.session.get(f"solved_tcs_{pk}", [])

    return render(
        request,
        "challenges/challenge_detail.html",
        {
            "challenge": challenge,
            "public_tests": public_tests,
            "hidden_tests": hidden_tests_list,
            "has_hidden_tests": hidden_tests.exists(),
            "is_solved": is_solved,
            "solved_tcs": solved_tcs,
            "show_spoilers": show_spoilers,
            "comments": comments,
            "has_rated": has_rated,
            "has_voted_diff": has_voted_diff,
            "difficulty_labels": DIFFICULTY_LABELS,
        },
    )


def challenge_upload(request):
    error_msg = None
    if request.method == "POST":
        form = ChallengeForm(request.POST)
        if form.is_valid():
            num_testcases = int(request.POST.get("num_testcases", 1))

            parsed_tcs = []
            has_public = False

            for i in range(1, num_testcases + 1):
                in_text = request.POST.get(f"input_text_{i}", "").strip()
                in_file = request.FILES.get(f"input_file_{i}")
                out_text = request.POST.get(f"output_text_{i}", "").strip()
                out_file = request.FILES.get(f"output_file_{i}")
                is_hidden = request.POST.get(f"is_hidden_{i}") == "on"

                if not in_text and not in_file and not out_text and not out_file:
                    continue

                if not out_text and not out_file:
                    error_msg = f"Test Case {i} must have either an expected output text or an output file."
                    break

                if not is_hidden:
                    has_public = True

                parsed_tcs.append(
                    {
                        "number": len(parsed_tcs) + 1,
                        "input_text": in_text,
                        "input_file": in_file,
                        "output_text": out_text,
                        "output_file": out_file,
                        "is_hidden": is_hidden,
                    }
                )

            if not error_msg and not parsed_tcs:
                error_msg = "You must provide at least one test case."
            if not error_msg and not has_public:
                error_msg = "You must have at least one public (non-hidden) test case."

            if not error_msg:
                try:
                    with transaction.atomic():
                        challenge = form.save()
                        for tc in parsed_tcs:
                            TestCase.objects.create(
                                challenge=challenge,
                                number=tc["number"],
                                input_text=tc["input_text"],
                                input_file=tc["input_file"],
                                output_text=tc["output_text"],
                                output_file=tc["output_file"],
                                is_hidden=tc["is_hidden"],
                            )
                        return redirect("challenge_list")
                except Exception as e:
                    error_msg = f"An error occurred while saving: {str(e)}"
    else:
        form = ChallengeForm()

    return render(
        request, "challenges/challenge_upload.html", {"form": form, "error": error_msg}
    )


def challenge_submit(request, pk):
    if request.method != "POST":
        return redirect("challenge_detail", pk=pk)

    session_key = _get_session_key(request)
    challenge = get_object_or_404(Challenge, pk=pk)
    hidden_tests = challenge.testcases.filter(is_hidden=True)

    wrong_tcs = []
    correct_tcs = []

    for tc in hidden_tests:
        expected = b""
        if tc.output_text:
            expected = tc.output_text.encode("utf-8")
        elif tc.output_file:
            try:
                tc.output_file.open("rb")
                expected = tc.output_file.read()
                tc.output_file.close()
            except Exception:
                expected = b""

        sub_text = request.POST.get(f"solve_text_{tc.id}", "")
        sub_file = request.FILES.get(f"solve_file_{tc.id}")

        submitted = b""
        if sub_text:
            submitted = sub_text.encode("utf-8")
        elif sub_file:
            try:
                submitted = sub_file.read()
            except Exception:
                submitted = b""

        if not sub_text and not sub_file:
            continue

        # (Windows \r\n and Mac \r to Unix \n)
        # I hope this doesnt break some challenge?
        # I mean... its not as bad as trimming input.
        expected = expected.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        submitted = submitted.replace(b"\r\n", b"\n").replace(b"\r", b"\n")

        if expected == submitted:
            correct_tcs.append(tc.number)
        else:
            wrong_tcs.append(tc.number)

    if not correct_tcs and not wrong_tcs:
        messages.warning(
            request, "You didn't submit any outputs. Please fill in at least one."
        )
    elif wrong_tcs:
        wrong_str = ", ".join(str(n) for n in sorted(wrong_tcs))
        correct_str = (
            ", ".join(str(n) for n in sorted(correct_tcs)) if correct_tcs else "none"
        )
        messages.error(
            request,
            f"Incorrect output for test case(s): {wrong_str}. Correct in this submission: {correct_str}.",
        )

    # (across potentially multiple submissions)
    all_hidden_numbers = set(hidden_tests.values_list("number", flat=True))
    solved_key = f"solved_tcs_{pk}"
    previously_solved = set(request.session.get(solved_key, []))
    previously_solved.update(correct_tcs)
    request.session[solved_key] = list(previously_solved)

    if previously_solved >= all_hidden_numbers:
        Solve.objects.get_or_create(session_key=session_key, challenge=challenge)
        messages.success(
            request, "🎉 Congratulations! You've solved ALL hidden test cases!"
        )
    elif correct_tcs and not wrong_tcs:
        remaining = all_hidden_numbers - previously_solved
        messages.success(
            request,
            f"✅ Test case(s) {', '.join(str(n) for n in sorted(correct_tcs))} correct! {len(remaining)} remaining.",
        )

    return HttpResponseRedirect(reverse("challenge_detail", args=[pk]) + "#submit")


# TODO: maybe sessions with more solved challenges get more weight in their votes?
# TODO: or some ELO system?
@transaction.atomic
def challenge_rate(request, pk):
    if request.method == "POST":
        session_key = _get_session_key(request)
        stars = int(request.POST.get("stars", 0))
        if 1 <= stars <= 5:
            challenge = get_object_or_404(Challenge, pk=pk)
            Rating.objects.update_or_create(
                session_key=session_key, challenge=challenge, defaults={"stars": stars}
            )
            messages.success(request, "Your rating has been saved.")
    return HttpResponseRedirect(reverse("challenge_detail", args=[pk]) + "#community")


@transaction.atomic
def challenge_difficulty(request, pk):
    if request.method == "POST":
        session_key = _get_session_key(request)
        diff = int(request.POST.get("difficulty", 0))
        if 1 <= diff <= 10:
            challenge = get_object_or_404(Challenge, pk=pk)
            DifficultyVote.objects.update_or_create(
                session_key=session_key,
                challenge=challenge,
                defaults={"difficulty": diff},
            )
            messages.success(request, "Your difficulty vote has been saved.")
    return HttpResponseRedirect(reverse("challenge_detail", args=[pk]) + "#community")


def challenge_comment(request, pk):
    if request.method == "POST":
        session_key = _get_session_key(request)
        text = request.POST.get("text", "").strip()
        nickname = request.POST.get("nickname", "").strip() or "Anonymous"
        if text:
            challenge = get_object_or_404(Challenge, pk=pk)
            Comment.objects.create(
                session_key=session_key,
                challenge=challenge,
                text=text,
                nickname=nickname,
            )
            messages.success(request, "Your comment has been posted.")
    return HttpResponseRedirect(reverse("challenge_detail", args=[pk]) + "#discussion")


def testcase_download(request, tc_id, which):
    """input or output as a .txt file."""
    tc = get_object_or_404(TestCase, pk=tc_id)
    if which == "output" and tc.is_hidden:
        return HttpResponse("Forbidden", status=403)

    if which == "input":
        if tc.input_file:
            tc.input_file.open("rb")
            content = tc.input_file.read()
            tc.input_file.close()
        elif tc.input_text:
            content = tc.input_text.encode("utf-8")
        else:
            content = b""
        filename = f"{tc.challenge.title}_tc{tc.number}_input.txt"
    elif which == "output":
        if tc.output_file:
            tc.output_file.open("rb")
            content = tc.output_file.read()
            tc.output_file.close()
        elif tc.output_text:
            content = tc.output_text.encode("utf-8")
        else:
            content = b""
        filename = f"{tc.challenge.title}_tc{tc.number}_output.txt"
    else:
        return HttpResponse("Bad request", status=400)

    response = HttpResponse(content, content_type="application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
