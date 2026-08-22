from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from posts.twitter_client import TweetClient
from .models import Article
from .serializers import ArticleSerializer
from .permissions import IsJournalistOrEditor, IsOwnerOrEditor


class ArticleListAPIView(generics.ListAPIView):
    """
    API endpoint that provides a read‑only list of all approved articles.

    This view returns only articles whose status is set to "approved", ensuring
    that unpublished, draft, or rejected content is never exposed through the
    public API. Articles are ordered from newest to oldest to prioritize recent
    publications. The endpoint is publicly accessible and does not require
    authentication.

    Attributes:
        queryset (QuerySet):
            A queryset of approved Article objects ordered by creation date
            in descending order.
        serializer_class (Serializer):
            The serializer used to convert Article instances into JSON.
        permission_classes (list):
            A list of permission classes; `AllowAny` permits unrestricted access.

    Returns:
        Response:
            A paginated or unpaginated list of serialized approved articles,
            depending on the project's REST framework settings.
    """
    queryset = Article.objects.filter(status="approved").order_by("-created_at")
    serializer_class = ArticleSerializer
    permission_classes = [permissions.AllowAny]


class SubscribedArticlesAPIView(generics.ListAPIView):
    """
    API endpoint that returns a list of approved articles from the reader's
    subscribed publishers and journalists.

    This view is accessible only to authenticated users, and it returns data
    **only** when the requesting user has the 'reader' role. It filters approved
    articles based on the reader's subscriptions:
        - Articles written by journalists the reader follows.
        - Articles published by publishers the reader follows.

    Articles are deduplicated and ordered from newest to oldest to prioritize
    recent content. Unauthenticated users and non‑readers receive an empty
    queryset.

    Behavior:
        - If the user is not authenticated, returns an empty queryset.
        - If the user is not a reader, returns an empty queryset.
        - Retrieves the reader's subscribed publishers and journalists.
        - Filters approved articles that match either subscription group.
        - Ensures uniqueness with `distinct()`.
        - Orders results by creation date in descending order.

    Attributes:
        serializer_class (Serializer):
            The serializer used to convert Article instances into JSON.

    Returns:
        QuerySet:
            A filtered, distinct, ordered list of approved articles based on the
            reader's subscriptions.
    """
    serializer_class = ArticleSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Article.objects.none()

        profile = user.profile

        # Readers only
        if profile.role != "reader":
            return Article.objects.none()

        subscribed_publishers = profile.subscribed_publishers.all()
        subscribed_journalists = profile.subscribed_journalists.all()

        return Article.objects.filter(
            status="approved"
        ).filter(
            Q(publisher__in=subscribed_publishers) |
            Q(author__in=subscribed_journalists)
        ).distinct().order_by("-created_at")
    

class ArticleDetailAPIView(generics.RetrieveAPIView):
    """
    API endpoint that retrieves the details of a single approved article.

    This view exposes only articles whose status is set to "approved", ensuring
    that drafts, rejected submissions, and unreviewed content are never made
    publicly accessible through the API. The endpoint is open to all users,
    including unauthenticated visitors, and returns a serialized representation
    of the requested article.

    Attributes:
        queryset (QuerySet):
            A queryset containing only approved Article objects.
        serializer_class (Serializer):
            The serializer used to convert an Article instance into JSON.
        permission_classes (list):
            A list of permission classes; `AllowAny` permits unrestricted access.

    Returns:
        Response:
            A serialized representation of the requested approved article, or a
            404 response if the article does not exist or is not approved.
    """
    queryset = Article.objects.filter(status="approved")
    serializer_class = ArticleSerializer
    permission_classes = [permissions.AllowAny]


class ArticleCreateAPIView(generics.CreateAPIView):
    """
    API endpoint that allows authenticated journalists or editors to create new articles.

    This view uses the `IsJournalistOrEditor` permission class to ensure that only
    users with the appropriate newsroom roles can submit new articles through the API.
    When an article is created, the authenticated user is automatically assigned as
    the article's author, preventing clients from spoofing or overriding authorship
    in the request payload.

    Behavior:
        - Accepts POST requests containing article data.
        - Validates the incoming data using `ArticleSerializer`.
        - Automatically sets the `author` field to the requesting user.
        - Saves the new article instance to the database.

    Attributes:
        serializer_class (Serializer):
            The serializer used to validate and serialize article data.
        permission_classes (list):
            A list of permission classes restricting access to journalists and editors.

    Methods:
        perform_create(serializer):
            Saves the article with the authenticated user set as the author.

    Returns:
        Response:
            A serialized representation of the newly created article, or validation
            errors if the request data is invalid.
    """
    serializer_class = ArticleSerializer
    permission_classes = [IsJournalistOrEditor]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ArticleUpdateAPIView(generics.RetrieveUpdateAPIView):
    """
    API endpoint that allows journalists or editors to update an existing article,
    with automatic detection of approval changes to trigger a Twitter announcement.

    This view supports retrieving and updating article instances. Access is
    restricted to users who are either:
        - The article's author (journalist), or
        - An editor with permission to modify articles in their newsroom.

    When an article is updated, the system checks whether its status has changed
    from any non‑approved state to "approved". If so, a tweet is automatically
    posted announcing the newly published article using the integrated Twitter
    client. This prevents duplicate tweets and ensures that only newly approved
    articles trigger social media distribution.

    Behavior:
        - Retrieves the article by ID for both GET and PUT/PATCH requests.
        - Validates permissions using `IsJournalistOrEditor` and `IsOwnerOrEditor`.
        - Saves updated article data through the serializer.
        - Compares the previous status with the new status.
        - If the article transitions to "approved":
              * Constructs a tweet containing the article title and link.
              * Attempts to post the tweet via `TweetClient`.
              * Logs any failures without interrupting the update process.

    Attributes:
        queryset (QuerySet):
            All Article objects, allowing retrieval and updates.
        serializer_class (Serializer):
            The serializer used to validate and serialize article data.
        permission_classes (list):
            Permission classes ensuring only authorized users may update articles.

    Methods:
        perform_update(serializer):
            Saves the updated article and triggers a tweet if the article has just
            been approved.

    Returns:
        Response:
            A serialized representation of the updated article, or validation errors
            if the request data is invalid.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsJournalistOrEditor, IsOwnerOrEditor]
    def perform_update(self, serializer):
        old_article = Article.objects.get(id=self.kwargs["pk"])
        new_article = serializer.save()

        # Detect approval change
        if old_article.status != "approved" and new_article.status == "approved":
            try:
                client = TweetClient()
                tweet_text = (
                    f"New article published: {new_article.title}\n"
                    f"Read here: http://127.0.0.1:8000/article/{new_article.id}/"
                )
                client.tweet_text(tweet_text)
            except Exception as e:
                print("Twitter posting failed:", e)


class ArticleDeleteAPIView(generics.DestroyAPIView):
    """
    API endpoint that allows authorized users to delete an article.

    This view supports the deletion of an existing article and is restricted to
    users who meet both permission requirements:
        - `IsJournalistOrEditor`: ensures the user is a journalist or editor.
        - `IsOwnerOrEditor`: ensures the user is either the article's author or
          an editor with the authority to manage newsroom content.

    Only users who satisfy **both** conditions may delete an article. This prevents
    unauthorized deletions while allowing editors to manage their publisher’s
    content and journalists to remove their own work when appropriate.

    Behavior:
        - Retrieves the article by ID.
        - Validates that the requesting user has permission to delete it.
        - Deletes the article from the database.
        - Returns a standard DRF `204 No Content` response upon success.

    Attributes:
        queryset (QuerySet):
            All Article objects, enabling lookup for deletion.
        serializer_class (Serializer):
            The serializer used for consistency with DRF conventions.
        permission_classes (list):
            Permission classes ensuring only authorized users may delete articles.

    Returns:
        Response:
            A `204 No Content` response if deletion is successful, or a `403 Forbidden`
            response if the user lacks permission.
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsJournalistOrEditor, IsOwnerOrEditor]