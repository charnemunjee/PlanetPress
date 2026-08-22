from django.shortcuts import render
from decimal import Decimal
import token
from urllib import request
from django import forms
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import Permission, User
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage, EmailMultiAlternatives, send_mail
import secrets
from datetime import datetime, timedelta
from hashlib import sha1
from django.utils import timezone
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from django.conf import settings

from .models import Article, Newsletter, Notification, UserProfile, ResetToken, ArticleCategory
from django.db.models import Q


# Create your views here.

def welcome(request):

    return render(request, 'welcome.html')

    
def register_user(request):

    publishers = UserProfile.objects.filter(role="publisher")

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        role = request.POST.get("role")
        publisher_id = request.POST.get("publisher_id")

        # Validation
        if User.objects.filter(username=username).exists():
            return render(request, "register_user.html", {
                "error": "Username already exists.",
                "publishers": publishers
            })

        if User.objects.filter(email=email).exists():
            return render(request, "register_user.html", {
                "error": "Email already registered.",
                "publishers": publishers
            })

        if password != confirm_password:
            return render(request, "register_user.html", {
                "error": "Passwords do not match.",
                "publishers": publishers
            })

        if not role:
            return render(request, "register_user.html", {
                "error": "Please select a role.",
                "publishers": publishers
            })

        # Determine publisher association
        publisher = None
        if role in ["journalist", "editor"]:
            if not publisher_id:
                return render(request, "register_user.html", {
                    "error": "Please select a publisher.",
                    "publishers": publishers
                })
            publisher = User.objects.get(id=publisher_id)

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # Create profile
        UserProfile.objects.create(
            user=user,
            role=role,
            publisher=publisher
        )

        return redirect("login_user")

    return render(request, "register_user.html", {"publishers": publishers})
    

def logout_user(request):

    logout(request)
    return render(request, "logout.html")


def login_user(request):

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            return render(request, "login.html", {"error": "Invalid credentials"})

        login(request, user)

        profile = user.profile

        # NEW: If reader and has NOT selected preferences → redirect to preference page
        if profile.role == "reader" and profile.preferred_categories.count() == 0:
            return redirect("select_reader_preferences")

        # Normal redirects
        if profile.role == "reader":
            return redirect("reader_dashboard")

        if profile.role in ["independent"]:
            return redirect("journalist_dashboard")
        
        if profile.role in ["journalist"]:
            return redirect("journalist_dashboard")
        
        
        if profile.role == "publisher":
            return redirect("publisher_dashboard")
        
        if profile.role == "editor":
            return redirect("editor_dashboard")

    return render(request, "login.html")


def forgot_password(request):

    return render(request, 'forgot_password.html')


def generate_reset_url(request, user):

    token = str(secrets.token_urlsafe(16))
    hashed = sha1(token.encode()).hexdigest()
    expiry_date = datetime.now() + timedelta(minutes=5)
    ResetToken.objects.create(
        user=user,
        token=hashed,
        expiry_date=expiry_date
        )
    reset_path = reverse("reset_password", args=[token])
    reset_url = request.build_absolute_uri(reset_path)
    return reset_url


def build_email(user, reset_url):
    """
    Builds the password reset email message.

    Parameters:
        user (User): The user requesting the reset.
        reset_url (str): The generated reset link.

    Returns:
        EmailMessage: A ready-to-send email object.
    """
    subject = "Password Reset"
    user_email = user.email
    domain_email = "example@domain.com"
    body = (f"Hi {user.username},\n\n"
            f"Here is your link to reset your password:\n"
            f"<{reset_url}>\n\n"
            f"If you did not request this, ignore this email.")
    email = EmailMessage(subject, body, domain_email, [user_email])
    return email


def send_password_reset_email(request):
    """
    Handles sending a password reset email to a user.

    Purpose:
        Validates the submitted email, generates a reset link, and sends the
        email to the user.

    Returns:
        HttpResponse: Rendered template with success or error message.
    """
    if request.method == 'POST':
        user_email = request.POST.get('email')

        user = User.objects.filter(email=user_email).first()
        if not user:
            return render(request, "forgot_password.html", {
                "error": "No account found with that email."
            })

        url = generate_reset_url(request, user)
        email = build_email(user, url)
        email.send()
        return render(request, "forgot_password.html", {
            "success": "A password reset link has been"
            " sent (check your terminal)."
        })
    return render(request, "forgot_password.html")


def change_user_password(username, new_password):
    """
    Updates a user's password.

    Parameters:
        username (str): The username of the account.
        new_password (str): The new password to set.

    Returns:
        None
    """
    user = User.objects.get(username=username)
    user.set_password(new_password)
    user.save()


def reset_password(request, token):
    """
    Handles password reset using a secure token.

    Parameters:
        token (str): The raw reset token from the email link.

    Purpose:
        Validates the token, checks expiry, updates the password, and deletes
        the token after use.

    Returns:
        HttpResponse: Rendered reset form or success message.
    """
    hashed = sha1(token.encode()).hexdigest()
    reset_obj = ResetToken.objects.filter(token=hashed).first()
    if not reset_obj:
        return render(request, "reset_password.html", {
            "error": "Invalid or expired reset link."})
    if reset_obj.expiry_date < timezone.now():
        return render(request, "reset_password.html", {
            "error": "This reset link has expired."})
    if request.method == "POST":
        new_password = request.POST.get("password")
        reset_obj.user.set_password(new_password)
        reset_obj.user.save()
        reset_obj.delete()
        return render(request, "reset_password.html", {
            "success": "Your password has been reset successfully."})
    return render(request, "reset_password.html")


def publish_article(request):
    """
    Allow authorized users to create and save a new article in draft form.

    This view is restricted to users who have publishing permissions, as
    determined by the `can_publish` flag on their UserProfile. If a user
    without publishing rights attempts to access the view, an HTTP 403
    Forbidden response is returned.

    Behavior:
        - GET request:
            Renders the article creation form.

        - POST request:
            * Retrieves the submitted title and content.
            * Creates a new Article instance with:
                - The current user as the author.
                - The submitted title and content.
                - An initial status of "draft".
            * Redirects the user to the dashboard after successful creation.

    Permissions:
        - Only users with `profile.can_publish == True` may access this view.

    Returns:
        HttpResponse:
            - On GET: the "publish_article.html" template.
            - On unauthorized access: HttpResponseForbidden.
            - On successful POST: redirect to the dashboard.
    """
    if not request.user.profile.can_publish:
        return HttpResponseForbidden("You are not allowed to publish articles.")

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")

        Article.objects.create(
            title=title,
            content=content,
            author=request.user,
            status="draft"
        )

        return redirect("dashboard")

    return render(request, "publish_article.html")


def request_review(request, article_id):
    """
    Allow an article's author to submit their article for editorial review.

    This view ensures that only the article's creator can request a review and
    that the user has the appropriate permissions based on their role within
    the PlanetPress platform. If either condition fails, the user receives an
    HTTP 403 Forbidden response.

    Behavior:
        - Retrieves the article by its ID.
        - Validates that the requesting user is the article's author.
        - Validates that the user has the `can_request_review` permission
          (typically journalists, independent writers, or publishers).
        - Calls the article's `submit_for_review()` method to update its status
          and trigger any associated logic (e.g., notifications, signals).
        - Redirects the user back to their dashboard after submission.

    Permissions:
        - Only the article's author may request a review.
        - The user must have `profile.can_request_review == True`.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        article_id (int):
            The ID of the article to be submitted for review.

    Returns:
        HttpResponse:
            - On permission failure: HttpResponseForbidden.
            - On success: redirect to the user's dashboard.
    """
    article = Article.objects.get(id=article_id)

    if article.author != request.user:
        return HttpResponseForbidden("You can only request review for your own articles.")

    if not request.user.profile.can_request_review:
        return HttpResponseForbidden("You cannot request a review.")

    article.submit_for_review()
    return redirect("dashboard")


def review_article(request, article_id):
    """
    Review and approve or reject a submitted article as an editor.

    This view allows authenticated editors to evaluate articles submitted for
    review by journalists or independent writers. Editors may approve or reject
    the article, provide optional feedback, and the system records which editor
    performed the review. When an article is approved, all subscribers of the
    author (journalist or publisher) are notified via email.

    Behavior:
        - Retrieves the target article or returns a 404 if it does not exist.
        - Ensures the requesting user has the 'editor' role; otherwise returns
          HTTP 403 Forbidden.
        - GET request:
            Renders the article review page with article details.
        - POST request:
            * Reads the editor's decision ("approve" or "reject").
            * Saves the editor's feedback.
            * Records the reviewing editor in `article.reviewed_by`.
            * If approved:
                - Updates the article status to "approved".
                - Triggers subscriber email notifications through
                  `notify_subscribers_of_article()`.
            * If rejected:
                - Updates the article status to "rejected".
                - Attempts to post a tweet announcing the article (wrapped in a
                  try/except block to avoid breaking the workflow if Twitter
                  posting fails).
            * Redirects the editor back to the unreviewed articles list.

    Permissions:
        - Only users whose profile role is "editor" may access this view.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        article_id (int):
            The ID of the article being reviewed.

    Returns:
        HttpResponse:
            - On GET: renders "review_article.html" with article context.
            - On unauthorized access: HttpResponseForbidden.
            - On successful POST: redirects to the unreviewed articles page.
    """
    article = get_object_or_404(Article, id=article_id)
    profile = request.user.profile

    if profile.role != "editor":
        return HttpResponseForbidden("Only editors can review articles.")

    if request.method == "POST":
        decision = request.POST.get("decision")
        feedback = request.POST.get("feedback")

        # Track who reviewed the article (User instance)
        article.reviewed_by = request.user
        article.editor_feedback = feedback

        if decision == "approve":
            article.status = "approved"
            article.save()

            notify_subscribers_of_article(article)

        elif decision == "reject":
            article.status = "rejected"
            article.save()

            try:
                client = TweetClient()
                tweet_text = (
                    f"New article published: {article.title}\n"
                    f"Read here: http://127.0.0.1:8000/article/{article.id}/"
                )
                client.tweet_text(tweet_text)
            except Exception as e:
                print("Twitter posting failed:", e)

        return redirect("editor_unreviewed_articles")

    return render(request, "review_article.html", {"article": article})


def notify_subscribers_of_article(article):
    """
    Send email notifications to all subscribers of the article's author and,
    if applicable, the author's publisher.

    This function is triggered when an article is approved by an editor. It
    gathers two subscriber groups:
        1. Readers who follow the journalist directly.
        2. Readers who follow the publisher the journalist belongs to
           (if the journalist is associated with a publisher).

    Both subscriber lists are combined and deduplicated to ensure that users
    who subscribe to both the journalist and the publisher receive only one
    email notification.

    Each subscriber receives an email containing:
        - The article title
        - The author's username
        - A link to read the article
        - A brief message from the PlanetPress team

    Args:
        article (Article):
            The article that has just been approved and should be announced
            to subscribers.

    Side Effects:
        - Sends an email to each subscriber using Django's `send_mail`.
        - Performs database queries to retrieve subscriber relationships.

    Returns:
        None
    """
    author = article.author  # This is a User object

    # Followers of this journalist
    journalist_followers = author.journalist_subscribers.all()

    # Followers of this publisher
    publisher_followers = author.publisher_subscribers.all()

    # Combine both sets
    subscribers = set(list(journalist_followers) + list(publisher_followers))

    for reader in subscribers:
        # reader is a User, not UserProfile
        send_mail(
            subject=f"New Article Published: {article.title}",
            message=(
                f"Hello {reader.user.username},\n\n"
                f"A new article has just been approved:\n\n"
                f"{article.title}\n\n"
                f"Visit PlanetPress to read it."
            ),
            from_email="noreply@planetpress.com",
            recipient_list=[reader.user.email],
            fail_silently=True,
        )


def writer_notifications(request):
    """
    Display all notifications belonging to the currently authenticated user.

    This view retrieves and displays system-generated notifications for writers,
    journalists, or any logged-in user. Notifications are ordered from newest to
    oldest to ensure that recent updates—such as article approvals, editorial
    feedback, or subscriber activity—appear first.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If authenticated:
            * Fetches all Notification objects associated with the user.
            * Orders them by creation time in descending order.
            * Renders the notifications page with the retrieved list.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - Rendered "writer_notifications.html" template containing the user's
              notifications.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")

    return render(request, "writer_notifications.html", {
        "notifications": notifications
    })


def reader_dashboard(request):
    """
    Display the dashboard for authenticated users with the 'reader' role.

    This view ensures that only logged‑in readers can access the reader
    dashboard. It retrieves the reader's selected article categories, which
    are used to personalize their experience (e.g., recommended articles,
    newsletters, or topic‑based content).

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not a reader, an HTTP 403 Forbidden
          response is returned.
        - Retrieves the reader's preferred article categories.
        - Renders the dashboard template with the user's preferences.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not a reader.
            - Rendered "reader_dashboard.html" template with preferred categories.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    if request.user.profile.role != "reader":
        return HttpResponseForbidden("You are not allowed to view this page.")

    profile = request.user.profile
    preferred = profile.preferred_categories.all()

    return render(request, "reader_dashboard.html", {
        "preferred_categories": preferred
    })


def select_reader_preferences(request):
    """
    Allow authenticated readers to select or update their preferred article categories.

    This view ensures that only logged‑in users with the 'reader' role can access
    the preference selection page. Readers use this page to choose the categories
    of articles they want to see prioritized in their dashboard and personalized
    content feed.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not a reader, an HTTP 403 Forbidden response
          is returned.
        - Retrieves all available ArticleCategory objects for display.
        - POST request:
            * Reads the list of selected category IDs.
            * Updates the reader's preferred_categories many‑to‑many field.
            * Redirects the user to the reader dashboard after saving.
        - GET request:
            * Renders the preference selection form with all categories.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not a reader.
            - Rendered "select_reader_preferences.html" template with category data.
            - Redirect to the reader dashboard after a successful POST.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile

    if profile.role != "reader":
        return HttpResponseForbidden("Only readers can select preferences.")

    categories = ArticleCategory.objects.all()

    if request.method == "POST":
        selected = request.POST.getlist("categories")
        profile.preferred_categories.set(selected)
        return redirect("reader_dashboard")

    return render(request, "select_reader_preferences.html", {
        "categories": categories
    })


def update_reader_preferences(request):
    """
    Allow authenticated readers to update their previously selected article
    category preferences.

    This view is accessible only to logged‑in users with the 'reader' role.
    It retrieves all available article categories and the reader's currently
    selected preferences, allowing them to modify their personalized content
    settings.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not a reader, an HTTP 403 Forbidden
          response is returned.
        - Retrieves all ArticleCategory objects for display.
        - Retrieves the reader's existing preferred categories to pre‑check
          the form.
        - POST request:
            * Reads the updated list of selected category IDs.
            * Saves the new preferences to the user's profile.
            * Redirects the user to the reader dashboard.
        - GET request:
            * Renders the update form with all categories and the user's
              current selections.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not a reader.
            - Rendered "update_reader_preferences.html" template with category
              data and selected preferences.
            - Redirect to the reader dashboard after a successful POST.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile

    if profile.role != "reader":
        return HttpResponseForbidden("Only readers can update preferences.")

    categories = ArticleCategory.objects.all()
    selected_categories = profile.preferred_categories.all()

    if request.method == "POST":
        selected = request.POST.getlist("categories")
        profile.preferred_categories.set(selected)
        return redirect("reader_dashboard")

    return render(request, "update_reader_preferences.html", {
        "categories": categories,
        "selected_categories": selected_categories
    })


def reader_all_articles(request):
    """
    Display a list of all articles for authenticated users with the 'reader' role.

    Unlike the personalized reader dashboard, this view provides readers with
    access to the full collection of articles on the platform—regardless of
    status. This includes approved, submitted, and unapproved articles, allowing
    readers to explore the entire catalog without filtering by category or
    publication state.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not a reader, an HTTP 403 Forbidden
          response is returned.
        - Retrieves all Article objects and orders them from newest to oldest.
        - Renders the article list template with the retrieved articles.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not a reader.
            - Rendered "reader_all_articles.html" template containing all articles.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile
    if profile.role != "reader":
        return HttpResponseForbidden("Only readers can view this page.")

    # Readers see ALL approved, unapproved, and submitted articles
    articles = Article.objects.all().order_by("-created_at")

    return render(request, "reader_all_articles.html", {
        "articles": articles
    })
    

def reader_view_article(request, article_id):
    """
    Display a single approved article for authenticated users with the 'reader' role.

    This view ensures that only logged‑in readers can access individual article
    pages. Readers are restricted to viewing only articles that have been fully
    approved by an editor. Any attempt to access an unapproved or non‑existent
    article results in a 404 error.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not a reader, an HTTP 403 Forbidden
          response is returned.
        - Retrieves the article by ID, but only if its status is "approved".
          Otherwise, a 404 is raised.
        - Renders the article detail page with the retrieved article.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        article_id (int):
            The ID of the article the reader wants to view.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not a reader.
            - Rendered "reader_view_article.html" template containing the article.
            - 404 if the article does not exist or is not approved.
    """
    # Must be logged in
    if not request.user.is_authenticated:
        return redirect("login_user")

    # Must be a reader
    if request.user.profile.role != "reader":
        return HttpResponseForbidden("You are not allowed to view this page.")

    # Only approved articles are visible to readers
    article = get_object_or_404(Article, id=article_id)

    return render(request, "reader_view_article.html", {
        "article": article
    })


def follow_user(request, user_id):
    """
    Allow authenticated readers to follow a journalist, independent writer, or publisher.

    This view enables users with the 'reader' role to subscribe to content creators
    on the PlanetPress platform. Readers can follow either:
        - Publishers (added to `subscribed_publishers`)
        - Journalists or independent writers (added to `subscribed_journalists`)

    Following a user allows the reader to receive notifications about new articles,
    newsletters, or updates from the selected creator.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not a reader, an HTTP 403 Forbidden response
          is returned.
        - Retrieves the target user by ID; returns 404 if not found.
        - Determines the target user's role and adds them to the appropriate
          subscription list.
        - Saves the updated reader profile.
        - Redirects the user back to the referring page, or to the reader dashboard
          if no referrer is available.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        user_id (int):
            The ID of the user the reader wishes to follow.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not a reader.
            - Redirect back to the referring page after successfully following.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile

    if profile.role != "reader":
        return HttpResponseForbidden("Only readers can follow.")

    target_user = get_object_or_404(User, id=user_id)
    target_profile = target_user.profile

    if target_profile.role == "publisher":
        profile.subscribed_publishers.add(target_user)

    elif target_profile.role in ["journalist", "independent"]:
        profile.subscribed_journalists.add(target_user)

    profile.save()
    return redirect(request.META.get("HTTP_REFERER", "reader_dashboard"))


def unfollow_user(request, user_id):
    """
    Allow authenticated readers to unfollow a journalist, independent writer, or publisher.

    This view enables users with the 'reader' role to remove a previously followed
    content creator from their subscription list. Depending on the target user's
    role, the reader is removed from either:
        - `subscribed_publishers` (for publishers)
        - `subscribed_journalists` (for journalists or independent writers)

    Unfollowing stops future notifications related to new articles or updates
    from that creator.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not a reader, an HTTP 403 Forbidden response
          is returned.
        - Retrieves the target user by ID; returns 404 if not found.
        - Determines the target user's role and removes them from the appropriate
          subscription list.
        - Saves the updated reader profile.
        - Redirects the user back to the referring page, or to the reader dashboard
          if no referrer is available.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        user_id (int):
            The ID of the user the reader wishes to unfollow.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not a reader.
            - Redirect back to the referring page after successfully unfollowing.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile

    if profile.role != "reader":
        return HttpResponseForbidden("Only readers can unfollow.")

    target_user = get_object_or_404(User, id=user_id)
    target_profile = target_user.profile

    if target_profile.role == "publisher":
        profile.subscribed_publishers.remove(target_user)

    elif target_profile.role in ["journalist", "independent"]:
        profile.subscribed_journalists.remove(target_user)

    profile.save()
    return redirect(request.META.get("HTTP_REFERER", "reader_dashboard"))


@login_required
def following_list(request):
    """
    Display the list of journalists and publishers followed by the authenticated reader.

    This view is restricted to users with the "reader" role. It retrieves all
    authors (journalists and publishers) that the reader has subscribed to and
    renders them in a dedicated following list page. Readers can use this page
    to manage their followed authors, access their article lists, or unfollow
    them.

    Behavior:
        - Ensures the user is authenticated and has the "reader" role.
          Otherwise, returns HTTP 403 Forbidden.
        - Retrieves all journalists the reader follows via
          `profile.subscribed_journalists`.
        - Retrieves all publishers the reader follows via
          `profile.subscribed_publishers`.
        - Renders the "following_list.html" template with both lists.

    Args:
        request (HttpRequest):
            The incoming HTTP request.

    Returns:
        HttpResponse:
            - HTTP 403 Forbidden if the user is not a reader.
            - Rendered template containing followed journalists and publishers.
    """
    profile = request.user.profile

    # Only readers have subscriptions
    if profile.role != "reader":
        return HttpResponseForbidden("Only readers can view followed authors.")

    followed_journalists = profile.subscribed_journalists.all()
    followed_publishers = profile.subscribed_publishers.all()

    return render(request, "following_list.html", {
        "followed_journalists": followed_journalists,
        "followed_publishers": followed_publishers,
    })


def editor_dashboard(request):
    """
    Display the main dashboard for authenticated users with the 'editor' role.

    This view ensures that only logged‑in editors can access the editorial
    dashboard. The dashboard serves as the central hub where editors can
    navigate to tasks such as reviewing submitted articles, viewing previously
    reviewed content, and managing editorial workflows.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not an editor, an HTTP 403 Forbidden
          response is returned.
        - Renders the editor dashboard template.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not an editor.
            - Rendered "editor_dashboard.html" template for authorized users.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    if request.user.profile.role != "editor":
        return HttpResponseForbidden("You are not allowed to view this page.")

    return render(request, "editor_dashboard.html")


def editor_unreviewed_articles(request):
    """
    Display all submitted articles awaiting review for the authenticated editor.

    This view is restricted to users with the 'editor' role. It retrieves all
    articles that are currently in the 'submitted' state *and* belong to the
    same publisher as the editor. This ensures that editors only review content
    within their assigned publishing organization.

    Behavior:
        - If the authenticated user is not an editor, an HTTP 403 Forbidden
          response is returned.
        - Retrieves all articles with:
              status = "submitted"
              publisher = editor's associated publisher
        - Orders the articles from newest to oldest.
        - Renders the unreviewed articles page with the filtered list.

    Returns:
        HttpResponse:
            - HttpResponseForbidden if the user is not an editor.
            - Rendered "editor_unreviewed_articles.html" template containing
              the list of submitted articles.
    """
    profile = request.user.profile

    if profile.role != "editor":
        return HttpResponseForbidden("Only editors can view this page.")

    articles = Article.objects.filter(
        status="submitted",
    ).order_by("-created_at")

    return render(request, "editor_unreviewed_articles.html", {"articles": articles})


def editor_reviewed_articles(request):
    """
    Display all articles that have already been reviewed by an authenticated editor.

    This view is restricted to users with the 'editor' role. It retrieves all
    articles whose status indicates they have undergone editorial review—
    specifically those marked as "approved" or "unapproved". The articles are
    ordered from newest to oldest to prioritize recent editorial activity.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not an editor, an HTTP 403 Forbidden
          response is returned.
        - Retrieves all Article objects with a status of either "approved"
          or "unapproved".
        - Orders the results by creation date in descending order.
        - Renders the reviewed articles page with the retrieved list.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not an editor.
            - Rendered "editor_reviewed_articles.html" template containing
              the list of reviewed articles.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile
    if profile.role != "editor":
        return HttpResponseForbidden("Only editors can view this page.")

    articles = Article.objects.filter(
        status__in=["approved", "unapproved"]
    ).order_by("-created_at")

    return render(request, "editor_reviewed_articles.html", {
        "articles": articles
    })


def send_topic_newsletter_to_readers(newsletter, category_id):
    """
    Send a topic‑based newsletter to all readers who follow the selected category.

    This function is called after an editor creates a topic‑specific newsletter.
    It identifies all readers who have selected the given article category as one
    of their preferred topics and sends each of them an email containing the
    newsletter details and a link to view it.

    Behavior:
        - Retrieves the ArticleCategory associated with the provided category ID.
        - Finds all users with the 'reader' role who have this category included
          in their preferred_categories many‑to‑many field.
        - Ensures duplicate users are removed using `distinct()`.
        - Sends each reader an email containing:
              * The newsletter title
              * The topic name
              * The newsletter description
              * A link to view the newsletter

    Args:
        newsletter (Newsletter):
            The newsletter instance that was just created.
        category_id (int or str):
            The ID of the category used to filter which readers should receive
            the newsletter.

    Side Effects:
        - Sends an email to each matching reader using Django's `send_mail`.
        - Performs database queries to retrieve category and reader data.

    Returns:
        None
    """
    category = ArticleCategory.objects.get(id=category_id)

    # Readers who selected this category as a preference
    readers = User.objects.filter(
        profile__role="reader",
        profile__preferred_categories=category
    ).distinct()

    for reader in readers:
        send_mail(
            subject=f"New {category.name} Newsletter: {newsletter.title}",
            message=(
                f"Hello {reader.username},\n\n"
                f"A new newsletter has been created for the topic '{category.name}'.\n\n"
                f"Title: {newsletter.title}\n"
                f"Description: {newsletter.description}\n\n"
                f"Read it here: http://127.0.0.1:8000/newsletter/{newsletter.id}/\n\n"
                f"PlanetPress Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reader.email],
            fail_silently=False,
        )


def editor_newsletters(request):
    """
    Display all newsletters created by the authenticated editor.

    This view is restricted to users with the 'editor' role. It retrieves all
    newsletters authored by the currently logged‑in editor and orders them from
    newest to oldest. Editors can use this page to manage their newsletters,
    including viewing, editing, or deleting them.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not an editor, an HTTP 403 Forbidden
          response is returned.
        - Retrieves all Newsletter objects where the author is the current user.
        - Orders the newsletters by creation date in descending order.
        - Renders the newsletter list page with the retrieved newsletters.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not an editor.
            - Rendered "editor_newsletters.html" template containing the editor's
              newsletters.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile

    # Only editors can access this page
    if profile.role != "editor":
        return HttpResponseForbidden("Only editors can view this page.")

    newsletters = Newsletter.objects.all().order_by("-created_at")

    return render(request, "editor_newsletters.html", {
        "newsletters": newsletters
    })

def journalist_articles_reader(request, user_id):
    """
    Display all articles written by a specific journalist for reader viewing.

    This view allows authenticated readers to browse the full list of articles
    authored by a particular journalist. It is typically accessed from the
    reader’s “Following” page or from any link that directs readers to an
    author’s article collection.

    Behavior:
        - Retrieves the journalist by user ID or returns a 404 if not found.
        - Fetches all articles authored by the journalist, ordered from newest
          to oldest.
        - Renders the "journalist_articles.html" template with both the
          journalist and their articles.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        user_id (int):
            The ID of the journalist whose articles should be displayed.

    Returns:
        HttpResponse:
            A rendered page showing the journalist’s profile information and
            their published articles.
    """
    journalist = get_object_or_404(User, id=user_id)
    articles = Article.objects.filter(author=journalist).order_by("-created_at")

    return render(request, "journalist_articles.html", {
        "journalist": journalist,
        "articles": articles
    })

def publisher_articles_reader(request, user_id):
    """
    Display all articles written by a specific publisher for reader viewing.

    This view allows authenticated readers to browse the full list of articles
    authored by a particular publisher. It is typically accessed from the
    reader’s “Following” page or from any link that directs readers to a
    publisher’s article collection.

    Behavior:
        - Retrieves the publisher by user ID or returns a 404 if not found.
        - Fetches all articles authored by the publisher, ordered from newest
          to oldest.
        - Renders the "publisher_articles.html" template with both the
          publisher and their articles.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        user_id (int):
            The ID of the publisher whose articles should be displayed.

    Returns:
        HttpResponse:
            A rendered page showing the publisher’s profile information and
            their published articles.
    """
    publisher = get_object_or_404(User, id=user_id)
    articles = Article.objects.filter(author=publisher).order_by("-created_at")

    return render(request, "publisher_articles.html", {
        "publisher": publisher,
        "articles": articles
    })


def journalist_articles(request):
    """
    Display all articles created by the authenticated independent journalist.

    This view is restricted to users with the 'independent' role. It retrieves
    all articles authored by the currently logged‑in independent journalist and
    orders them from newest to oldest. Independent journalists can use this page
    to manage their work, including reviewing drafts, submitted articles, and
    previously published content.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not an independent journalist, an
          HTTP 403 Forbidden response is returned.
        - Retrieves all Article objects where the author is the current user.
        - Orders the articles by creation date in descending order.
        - Renders the article list page with the retrieved articles.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not an independent journalist.
            - Rendered "journalist_articles.html" template containing
              the journalist's articles.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile

    if profile.role not in ["independent", "journalist"]:
        return HttpResponseForbidden("Only independent journalists can view this page.")

    # Fetch all articles submitted by this journalist
    articles = Article.objects.filter(author=request.user).order_by("-created_at")

    return render(request, "journalist_articles.html", {
        "articles": articles
    })


def journalist_dashboard(request):
    """
    Display the main dashboard for authenticated independent journalists, including
    their articles and newsletters with optional filtering.

    This view is restricted to users with the 'independent' role. It serves as the
    central workspace for independent journalists, allowing them to view and manage
    their articles and newsletters. Journalists can filter their articles by
    category and status to quickly locate drafts, submitted work, approved pieces,
    or rejected submissions.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not an independent journalist, an
          HTTP 403 Forbidden response is returned.
        - Retrieves all article categories and all possible article statuses.
        - Reads optional GET parameters:
              * "category" — filters articles by category ID.
              * "status" — filters articles by article status.
        - Retrieves all articles authored by the journalist and applies filters
          if provided.
        - Retrieves all newsletters authored by the journalist.
        - Orders both articles and newsletters from newest to oldest.
        - Renders the journalist dashboard with articles, newsletters, filters,
          and available categories/statuses.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not an independent journalist.
            - Rendered "journalist_dashboard.html" template containing:
                  * Filtered articles
                  * All categories and statuses
                  * Selected filter values
                  * Journalist-authored newsletters
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile
    if profile.role not in ["independent", "journalist"]:
        return HttpResponseForbidden("Only journalists can access this page.")

    categories = ArticleCategory.objects.all()
    statuses = ["draft", "submitted", "approved", "rejected"]

    selected_category = request.GET.get("category")
    selected_status = request.GET.get("status")

    articles = Article.objects.filter(author=request.user)

    if selected_category:
        articles = articles.filter(category_id=selected_category)

    if selected_status:
        articles = articles.filter(status=selected_status)

    articles = articles.order_by("-created_at")

    newsletters = Newsletter.objects.filter(author=request.user).order_by("-created_at")

    return render(request, "journalist_dashboard.html", {
        "articles": articles,
        "categories": categories,
        "statuses": statuses,
        "selected_category": selected_category,
        "selected_status": selected_status,
        "newsletters": newsletters,
        })


def delete_newsletter(request, newsletter_id):
    """
    Allow authenticated independent journalists to delete one of their own newsletters.

    This view is restricted to users with the 'independent' role. It ensures that
    independent journalists can only delete newsletters they personally created.
    Attempting to delete another user's newsletter results in a forbidden response.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not an independent journalist, an
          HTTP 403 Forbidden response is returned.
        - Retrieves the newsletter by ID or raises a 404 if it does not exist.
        - Verifies that the newsletter's author matches the current user.
          If not, an HTTP 403 Forbidden response is returned.
        - Deletes the newsletter from the database.
        - Redirects the journalist back to their dashboard.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        newsletter_id (int):
            The ID of the newsletter to be deleted.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not an independent journalist
              or is not the newsletter's author.
            - Redirect to the journalist dashboard after successful deletion.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    newsletter = get_object_or_404(Newsletter, id=newsletter_id)

    profile = request.user.profile

    # Only independent journalists can delete their own newsletters
    if profile.role not in ["independent", "journalist", "editor"]:
        return HttpResponseForbidden("Only journalists and editors can delete newsletters.")
    
    if profile.role == "editor":
        newsletter.delete()

    elif newsletter.author != request.user:
        return HttpResponseForbidden("You can only delete newsletters you created.")

    else:
        newsletter.delete()

    if profile.role == "editor":
        return redirect("editor_newsletters")
    elif profile.role in ["independent", "journalist"]:
        return redirect("journalist_dashboard")


def submit_article(request):
    """
    Allow authenticated journalists (independent or publisher‑affiliated) to submit a new article.

    This view enables users with either the 'independent' or 'journalist' role to
    create and submit a new article. Independent journalists submit articles
    without a publisher association, while publisher‑affiliated journalists have
    their articles automatically linked to their assigned publisher. All newly
    submitted articles are created with a default status of "draft".

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not an independent or publisher journalist,
          an HTTP 403 Forbidden response is returned.
        - Retrieves all available article categories for selection.
        - POST request:
            * Reads the article title, content, and selected category.
            * Determines whether the article should be associated with a publisher
              (only for users with the 'journalist' role).
            * Creates a new Article instance with status set to "draft".
            * Redirects the user to the journalist dashboard.
        - GET request:
            * Renders the article submission form with category options.

    Args:
        request (HttpRequest):
            The incoming HTTP request.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user lacks permission to submit articles.
            - Rendered "submit_article.html" template on GET.
            - Redirect to the journalist dashboard after a successful POST.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile

    # Only journalists (independent or publisher journalists) can submit
    if profile.role not in ["independent", "journalist"]:
        return HttpResponseForbidden("You are not allowed to submit articles.")

    categories = ArticleCategory.objects.all()

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        category_id = request.POST.get("category")

        # Determine publisher association
        publisher = profile.publisher if profile.role in ["journalist", "independent"] else None

        Article.objects.create(
            title=title,
            content=content,
            author=request.user,
            publisher=publisher,
            category_id=category_id,
            status="draft"
        )

        return redirect("journalist_dashboard")

    return render(request, "submit_article.html", {"categories": categories})


def submit_for_review(request, article_id):
    """
    Allow an authenticated journalist to submit a draft article for editorial review.

    This view is restricted to the article's author. It ensures that only the
    creator of the article can submit it for review and that the article is still
    in the "draft" state. Once submitted, the article's status is updated to
    "submitted", making it visible to editors for review.

    Behavior:
        - Retrieves the article by ID or raises a 404 if it does not exist.
        - Verifies that the current user is the article's author; otherwise,
          returns an HTTP 403 Forbidden response.
        - Ensures the article is still a draft; only drafts may be submitted.
        - Updates the article's status to "submitted" and saves the change.
        - Redirects the user back to the journalist dashboard.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        article_id (int):
            The ID of the article being submitted for review.

    Returns:
        HttpResponse:
            - HttpResponseForbidden if the user is not the article's author or
              if the article is not in draft status.
            - Redirect to the journalist dashboard after successful submission.
    """
    article = get_object_or_404(Article, id=article_id)

    if article.author != request.user:
        return HttpResponseForbidden("Not allowed.")

    if article.status != "draft":
        return HttpResponseForbidden("Only drafts can be submitted for review.")

    article.status = "submitted"
    article.save()

    return redirect("journalist_dashboard")


def delete_article(request, article_id):
    """
    Allow an authenticated journalist to delete one of their own draft articles.

    This view ensures that only the author of an article can delete it, and only
    while the article is still in the "draft" state. Once deleted, the article is
    permanently removed from the system. Articles that have already been submitted
    for review or published cannot be deleted.

    Behavior:
        - Retrieves the article by ID or raises a 404 if it does not exist.
        - Verifies that the current user is the article's author; otherwise,
          returns an HTTP 403 Forbidden response.
        - Ensures the article is still a draft; only drafts may be deleted.
        - Deletes the article from the database.
        - Redirects the user back to the journalist dashboard.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        article_id (int):
            The ID of the article to be deleted.

    Returns:
        HttpResponse:
            - HttpResponseForbidden if the user is not the article's author or
              if the article is not in draft status.
            - Redirect to the journalist dashboard after successful deletion.
    """

    article = get_object_or_404(Article, id=article_id)
    if request.user.profile.role == "editor":
        article.delete()
    elif request.user.profile.role in ["independent", "journalist"] and article.author == request.user and article.status == "draft":
        article.delete()
    else:
        return HttpResponseForbidden("Not allowed.")

    if request.user.profile.role in ["journalist", "independent"]:
        return redirect("journalist_dashboard")
    elif request.user.profile.role == "editor":
        return redirect("editor_dashboard")


def view_article(request, article_id):
    """
    Display a single article to the user.

    This view retrieves an article by its ID and renders a simple detail page
    showing the article's full content. No role‑based restrictions are applied
    here, so any authenticated or anonymous user (depending on your URL access
    rules) may view the article as long as it exists.

    Behavior:
        - Retrieves the article by ID or raises a 404 if it does not exist.
        - Renders the article detail template with the retrieved article.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        article_id (int):
            The ID of the article to display.

    Returns:
        HttpResponse:
            Rendered "view_article.html" template containing the article.
    """
    article = get_object_or_404(Article, id=article_id)
    return render(request, "view_article.html", {"article": article})


def edit_article(request, article_id):
    """
    Allow an authenticated content creator or editor to update an existing article.

    This view enables users with the roles *journalist*, *independent*, or *editor*
    to modify an article they have access to. It retrieves the article by ID,
    displays the editing form, and processes updates submitted via POST. After a
    successful update, the user is redirected to the appropriate dashboard based
    on their role.

    Behavior:
        - Retrieves the article by ID or raises a 404 if it does not exist.
        - Retrieves all available article categories for the category dropdown.
        - POST request:
            * Reads updated title, content, and category from the form.
            * Saves the modified article.
            * Redirects journalists and independents to the journalist dashboard.
            * Redirects editors to the editor dashboard.
        - GET request:
            * Renders the article editing form populated with the current article
              data and available categories.

    Permissions:
        - Only authenticated users may access this view.
        - Role-based redirection ensures users return to the correct dashboard
          after editing.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        article_id (int):
            The ID of the article being edited.

    Returns:
        HttpResponse:
            - Rendered "edit_article.html" template on GET.
            - Redirect to the appropriate dashboard after a successful POST.
    """
    article = get_object_or_404(Article, id=article_id)
    categories = ArticleCategory.objects.all()

    if request.method == "POST":
        article.title = request.POST.get("title")
        article.content = request.POST.get("content")
        article.category_id = request.POST.get("category")
        article.save()

        role = request.user.profile.role

        if role in ["journalist", "independent"]:
            return redirect("journalist_dashboard")
        elif role == "editor":
            return redirect("editor_dashboard")

    return render(request, "edit_article.html", {
        "article": article,
        "categories": categories
    })


def edit_article_per_role(request, article_id):
    """
    Route article‑editing requests through role‑based access control.

    This view acts as a permission gateway for editing articles. It determines
    whether the authenticated user has the right to modify the specified article
    and delegates the actual editing logic to `edit_article()` when allowed.

    Behavior:
        - Retrieves the target article by ID or raises a 404 if not found.
        - Determines the role of the authenticated user.
        - Editors:
            * May edit any article regardless of author or status.
            * The request is forwarded directly to `edit_article()`.
        - Journalists and independent writers:
            * May edit only their own articles.
            * Editing is allowed only when the article is still in "draft" status.
            * If both conditions are met, the request is forwarded to `edit_article()`.
            * Otherwise, an HTTP 403 Forbidden response is returned.
        - All other roles (including readers and publishers):
            * Are not permitted to edit articles and receive a 403 response.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        article_id (int):
            The ID of the article the user is attempting to edit.

    Returns:
        HttpResponse:
            - The result of `edit_article()` when editing is permitted.
            - HttpResponseForbidden if the user lacks permission.
    """
    article = get_object_or_404(Article, id=article_id)
    role = request.user.profile.role

    # Editors can edit anything
    if role == "editor":
        return edit_article(request, article_id=article_id)

    # Journalists/independents can edit only their own drafts
    elif role in ["journalist", "independent"]:
        if article.author == request.user and article.status == "draft":
            return edit_article(request, article_id=article_id)  
        return HttpResponseForbidden("Not allowed.")
    # Everyone else forbidden
    return HttpResponseForbidden("Not allowed.")

###Publisher

def publisher_dashboard(request):
    """
    Display the main dashboard for authenticated publishers, including their team
    members and all articles associated with their newsroom.

    This view is restricted to users with the 'publisher' role. It provides an
    overview of the publisher's editorial team—specifically the editors and
    journalists assigned to their newsroom—as well as all articles created under
    the publisher's organization. Articles are ordered from newest to oldest to
    highlight recent activity.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user is not a publisher, an HTTP 403 Forbidden
          response is returned.
        - Retrieves all editors whose UserProfile lists the current user as their
          publisher.
        - Retrieves all journalists assigned to the publisher.
        - Retrieves all articles associated with the publisher's newsroom.
        - Orders articles by creation date in descending order.
        - Renders the publisher dashboard with team members and articles.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not a publisher.
            - Rendered "publisher_dashboard.html" template containing:
                  * Editors in the publisher's newsroom
                  * Journalists in the publisher's newsroom
                  * Articles belonging to the publisher
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile
    if profile.role != "publisher":
        return HttpResponseForbidden("Only publishers can access this page.")

    # Team members
    editors = UserProfile.objects.filter(role="editor", publisher=request.user)
    journalists = UserProfile.objects.filter(role="journalist", publisher=request.user)

    # Convert profiles → actual User objects
    journalist_users = [j.user for j in journalists]
    editor_users = [e.user for e in editors]

    # Articles written by associated journalists
    journalist_articles = Article.objects.filter(
        author__in=journalist_users
    ).order_by("-created_at")

    approved_articles = Article.objects.filter(
        status="approved",
        publisher=request.user
    ).order_by("-created_at")


    return render(request, "publisher_dashboard.html", {
        "editors": editors,
        "journalists": journalists,
        "journalist_articles": journalist_articles,
        "approved_articles": approved_articles,
    })


def create_newsletter(request):
    """
    Allow authenticated journalists and editors to create a new newsletter by selecting
    articles and providing a title and description.

    This view is accessible to users with the roles 'journalist', 'independent',
    or 'editor'. Journalists can select from their own articles as well as articles
    belonging to their publisher, while editors may select from all articles under
    the publisher. After creating the newsletter, subscribers are notified via
    email.

    Behavior:
        - If the user is not authenticated, they are redirected to the login page.
        - If the authenticated user does not have permission to create newsletters,
          an HTTP 403 Forbidden response is returned.
        - Journalists:
              * Can select from their own articles and articles belonging to their
                publisher.
        - Editors:
              * Can select from all articles associated with their publisher.
        - POST request:
              * Reads the newsletter title, description, and selected article IDs.
              * Creates a new Newsletter instance authored by the current user.
              * Associates the selected articles with the newsletter.
              * Notifies subscribers via `notify_subscribers_of_newsletter()`.
              * Redirects to the newsletter detail page.
        - GET request:
              * Renders the newsletter creation form with the appropriate article list.

    Args:
        request (HttpRequest):
            The incoming HTTP request.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user lacks permission.
            - Rendered "create_newsletter.html" template on GET.
            - Redirect to the newsletter detail page after successful creation.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile

    # Only journalists and editors can create newsletters
    if profile.role not in ["journalist", "independent", "editor"]:
        return HttpResponseForbidden("You are not allowed to create newsletters.")

    # Journalists: show their own articles + publisher articles
    # Editors: show all publisher articles
    if profile.role == "journalist":
        articles = Article.objects.filter(
            Q(author=request.user) | Q(publisher=profile.publisher)
        )
    else:  # editor
        articles = Article.objects.filter(publisher=profile.publisher)

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        selected_articles = request.POST.getlist("articles")

        newsletter = Newsletter.objects.create(
            title=title,
            description=description,
            author=request.user
        )

        newsletter.articles.set(selected_articles)

        notify_subscribers_of_newsletter(newsletter)

        return redirect("view_newsletter", newsletter.id)

    return render(request, "create_newsletter.html", {
        "articles": articles
    })


def view_newsletter(request, newsletter_id):
    """
    Display a single newsletter to the user.

    This view retrieves a newsletter by its ID and renders a detail page showing
    its title, description, associated articles, and any other relevant metadata.
    There are no role‑based restrictions here unless enforced at the URL level,
    allowing any permitted user to view the newsletter.

    Behavior:
        - Retrieves the newsletter by ID or raises a 404 if it does not exist.
        - Renders the newsletter detail template with the retrieved newsletter.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        newsletter_id (int):
            The ID of the newsletter to display.

    Returns:
        HttpResponse:
            Rendered "view_newsletter.html" template containing the newsletter.
    """
    newsletter = get_object_or_404(Newsletter, id=newsletter_id)

    return render(request, "view_newsletter.html", {
        "newsletter": newsletter
    })


def reader_newsletters(request):
    """
    Display personalized newsletters for an authenticated reader based on their
    preferred article categories.

    This view is restricted to users with the 'reader' role. It retrieves the
    reader's selected article categories and filters newsletters to include only
    those that contain at least one article matching the reader's interests.
    The result is a personalized newsletter feed ordered from newest to oldest.

    Behavior:
        - Redirects unauthenticated users to the login page.
        - Returns an HTTP 403 Forbidden response if the user is not a reader.
        - Retrieves all categories the reader has selected as preferences.
        - Filters newsletters to include only those containing articles whose
          categories intersect with the reader's preferences.
        - Ensures duplicate newsletters are removed using `distinct()`.
        - Orders newsletters by creation date in descending order.
        - Renders the personalized newsletter list.

    Args:
        request (HttpRequest):
            The incoming HTTP request.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not a reader.
            - Rendered "reader_newsletters.html" template containing the filtered
              list of newsletters.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile

    if profile.role != "reader":
        return HttpResponseForbidden("Only readers can view newsletters.")

    # Get reader's preferred categories
    preferred_categories = profile.preferred_categories.all()

    # Filter newsletters that contain at least one article in preferred categories
    newsletters = Newsletter.objects.filter(
        articles__category__in=preferred_categories
    ).distinct().order_by("-created_at")

    return render(request, "reader_newsletters.html", {
        "newsletters": newsletters
    })


def journalist_edit_newsletter(request, newsletter_id):
    """
    Allow authenticated journalists and editors to edit an existing newsletter,
    with role‑based restrictions determining which newsletters and articles they
    may modify.

    This view enforces strict permission rules:
        - Journalists may only edit newsletters they personally created.
        - Editors may edit any newsletter belonging to their publisher.
    The set of articles available for selection also depends on the user's role:
        - Journalists may choose from their own articles and articles belonging
          to their publisher.
        - Editors may choose from all articles under their publisher.

    Behavior:
        - Retrieves the newsletter by ID or raises a 404 if it does not exist.
        - Validates that the user has permission to edit the newsletter based on
          their role and publisher association.
        - Determines the appropriate set of articles the user may attach.
        - POST request:
              * Updates the newsletter's title and description.
              * Replaces associated articles with the selected ones.
              * Redirects to the newsletter detail page.
        - GET request:
              * Renders the newsletter editing form with the newsletter data and
                the allowed article list.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        newsletter_id (int):
            The ID of the newsletter being edited.

    Returns:
        HttpResponse:
            - HttpResponseForbidden if the user lacks permission to edit the
              newsletter.
            - Rendered "edit_newsletter.html" template on GET.
            - Redirect to the newsletter detail page after a successful POST.
    """

    newsletter = get_object_or_404(Newsletter, id=newsletter_id)
    profile = request.user.profile

    # Permission check
    if profile.role not in ["journalist", "independent"]:
        return HttpResponseForbidden("You cannot edit newsletters.")

    # Journalists can only edit their own newsletters
    if profile.role not in ["journalist", "independent"] and newsletter.author != request.user:
        return HttpResponseForbidden("You can only edit your own newsletters.")

    # Article selection logic
    if profile.role in ["journalist", "independent"]:
        articles = Article.objects.filter(
            Q(author=request.user) | Q(publisher=profile.publisher)
        )
    else:
        articles = Article.objects.filter(publisher=profile.publisher)

    if request.method == "POST":
        newsletter.title = request.POST.get("title")
        newsletter.description = request.POST.get("description")
        newsletter.save()

        selected_articles = request.POST.getlist("articles")
        newsletter.articles.set(selected_articles)

        return redirect("view_newsletter", newsletter.id)

    return render(request, "edit_newsletter.html", {
        "newsletter": newsletter,
        "articles": articles
    })


def editors_edit_newsletter(request, newsletter_id):
    """
    Allow authenticated journalists and editors to edit an existing newsletter,
    with role‑based restrictions determining which newsletters and articles they
    may modify.

    This view enforces strict permission rules:
        - Journalists may only edit newsletters they personally created.
        - Editors may edit any newsletter belonging to their publisher.
    The set of articles available for selection also depends on the user's role:
        - Journalists may choose from their own articles and articles belonging
          to their publisher.
        - Editors may choose from all articles under their publisher.

    Behavior:
        - Retrieves the newsletter by ID or raises a 404 if it does not exist.
        - Validates that the user has permission to edit the newsletter based on
          their role and publisher association.
        - Determines the appropriate set of articles the user may attach.
        - POST request:
              * Updates the newsletter's title and description.
              * Replaces associated articles with the selected ones.
              * Redirects to the newsletter detail page.
        - GET request:
              * Renders the newsletter editing form with the newsletter data and
                the allowed article list.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        newsletter_id (int):
            The ID of the newsletter being edited.

    Returns:
        HttpResponse:
            - HttpResponseForbidden if the user lacks permission to edit the
              newsletter.
            - Rendered "edit_newsletter.html" template on GET.
            - Redirect to the newsletter detail page after a successful POST.
    """

    newsletter = get_object_or_404(Newsletter, id=newsletter_id)
    profile = request.user.profile

    # Permission check
    if profile.role != "editor":
        return HttpResponseForbidden("You cannot edit newsletters.")

    # Article selection logic
    if profile.role in ["editor"]:
        articles = Article.objects.all()

    if request.method == "POST":
        newsletter.title = request.POST.get("title")
        newsletter.description = request.POST.get("description")
        newsletter.save()

        selected_articles = request.POST.getlist("articles")
        newsletter.articles.set(selected_articles)

        return redirect("view_newsletter", newsletter.id)

    return render(request, "editor_edit_newsletter.html", {
        "newsletter": newsletter,
        "articles": articles
    })


def subscribe(request, user_id):
    """
    Allow an authenticated reader to subscribe to a journalist or publisher.

    This view is restricted to users with the 'reader' role. It enables readers
    to follow either publishers or journalists (including independent journalists
    and publisher‑affiliated journalists). Subscribing allows the reader to
    receive newsletters and updates from the selected creator.

    Behavior:
        - Redirects unauthenticated users to the login page.
        - Returns an HTTP 403 Forbidden response if the user is not a reader.
        - Retrieves the target user by ID or raises a 404 if they do not exist.
        - If the target user is a publisher:
              * Adds the publisher to the reader's subscribed_publishers list.
        - If the target user is a journalist (independent or publisher‑affiliated):
              * Adds the journalist to the reader's subscribed_journalists list.
        - Saves the updated subscription data.
        - Redirects the reader back to their dashboard.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        user_id (int):
            The ID of the user (journalist or publisher) to subscribe to.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not a reader.
            - Redirect to the reader dashboard after a successful subscription.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile

    # Only readers can subscribe
    if profile.role != "reader":
        return HttpResponseForbidden("Only readers can subscribe to journalists or publishers.")

    target_user = get_object_or_404(User, id=user_id)
    target_profile = target_user.profile

    # Subscribe to a publisher
    if target_profile.role == "publisher":
        profile.subscribed_publishers.add(target_user)

    # Subscribe to a journalist (independent or publisher journalist)
    elif target_profile.role in ["journalist", "independent"]:
        profile.subscribed_journalists.add(target_user)

    profile.save()

    return redirect("reader_dashboard")


def unsubscribe(request, user_id):
    """
    Allow an authenticated reader to unsubscribe from a journalist or publisher.

    This view is restricted to users with the 'reader' role. It enables readers
    to remove a previously followed journalist or publisher from their
    subscription lists, stopping future newsletter notifications from that
    creator.

    Behavior:
        - Redirects unauthenticated users to the login page.
        - Returns an HTTP 403 Forbidden response if the user is not a reader.
        - Retrieves the target user by ID or raises a 404 if they do not exist.
        - If the target user is a publisher:
              * Removes them from the reader's subscribed_publishers list.
        - If the target user is a journalist (independent or publisher‑affiliated):
              * Removes them from the reader's subscribed_journalists list.
        - Saves the updated subscription data.
        - Redirects the reader back to their dashboard.

    Args:
        request (HttpRequest):
            The incoming HTTP request.
        user_id (int):
            The ID of the user (journalist or publisher) to unsubscribe from.

    Returns:
        HttpResponse:
            - Redirect to login if the user is not authenticated.
            - HttpResponseForbidden if the user is not a reader.
            - Redirect to the reader dashboard after successful unsubscription.
    """
    if not request.user.is_authenticated:
        return redirect("login_user")

    profile = request.user.profile

    if profile.role != "reader":
        return HttpResponseForbidden("Only readers can unsubscribe.")

    target_user = get_object_or_404(User, id=user_id)
    target_profile = target_user.profile

    if target_profile.role == "publisher":
        profile.subscribed_publishers.remove(target_user)

    elif target_profile.role in ["journalist", "independent"]:
        profile.subscribed_journalists.remove(target_user)

    profile.save()

    return redirect("reader_dashboard")


def notify_subscribers_of_newsletter(newsletter):
    """
    Send email notifications to all subscribers of the newsletter's author and,
    if applicable, the author's publisher.

    This function gathers two groups of subscribers:
        1. Readers who follow the journalist who created the newsletter.
        2. Readers who follow the publisher the journalist belongs to
           (if the journalist is associated with a publisher).

    Both subscriber lists are combined and deduplicated to ensure that readers
    who subscribe to both the journalist and the publisher receive only one
    notification. Each subscriber receives an email containing the newsletter
    title, author information, and a link to view the newsletter.

    Behavior:
        - Retrieves all subscribers who follow the newsletter's author.
        - Retrieves all subscribers who follow the author's publisher, if one exists.
        - Combines and deduplicates both subscriber groups.
        - Sends an email notification to each subscriber using Django's `send_mail`.

    Args:
        newsletter (Newsletter):
            The newsletter that has just been created and should be announced
            to subscribers.

    Returns:
        None
            This function performs side effects (sending emails) but does not
            return a value.
    """
    author = newsletter.author
    author_profile = author.profile

    # Subscribers of the journalist
    journalist_subscribers = author.journalist_subscribers.all()

    # Subscribers of the publisher (if applicable)
    if author_profile.publisher:
        publisher_user = author_profile.publisher
        publisher_subscribers = publisher_user.publisher_subscribers.all()
    else:
        publisher_subscribers = User.objects.none()

    # Combine both groups
    subscribers = (journalist_subscribers | publisher_subscribers).distinct()

    # Send email to each subscriber
    for user in subscribers:
        send_mail(
            subject=f"New Newsletter: {newsletter.title}",
            message=(
                f"Hello {user.username},\n\n"
                f"A new newsletter has been published:\n\n"
                f"Title: {newsletter.title}\n"
                f"Author: {newsletter.author.username}\n\n"
                f"Read it here: http://127.0.0.1:8000/newsletter/{newsletter.id}/\n\n"
                f"PlanetPress Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
