from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch

from rest_framework.test import APIClient
from rest_framework import status

from .models import Article, ArticleCategory, Newsletter, UserProfile


class BaseAPITestCase(TestCase):
    """
    Base test case providing a fully prepared environment for API tests involving
    users, roles, categories, subscriptions, and article data.

    This class sets up a realistic newsroom ecosystem to support comprehensive
    testing of API endpoints related to articles, subscriptions, permissions, and
    personalized content delivery. It initializes multiple user roles, assigns
    relationships between them, and creates sample articles in different states
    (approved, draft, publisher‑linked, journalist‑linked).

    Behavior:
        - Initializes an APIClient instance for making authenticated and
          unauthenticated API requests.
        - Creates a sample article category for use across tests.
        - Creates users for each supported role:
              * reader
              * journalist
              * independent journalist
              * publisher
              * editor
        - Builds corresponding UserProfile instances and assigns role‑specific
          attributes.
        - Configures reader preferences and subscriptions:
              * Preferred categories
              * Subscribed journalists
              * Subscribed publishers
        - Creates sample articles:
              * An approved article authored by a journalist
              * An approved article published under a publisher
              * An unapproved draft article

    Attributes:
        client (APIClient):
            The DRF test client used for making API requests.
        category (ArticleCategory):
            A sample category used for article classification.
        reader, journalist, independent, publisher, editor (User):
            Test users representing all supported roles.
        reader_profile, journalist_profile, independent_profile,
        publisher_profile, editor_profile (UserProfile):
            Profiles associated with each test user.
        approved_article_journalist (Article):
            An approved article authored by a journalist.
        approved_article_publisher (Article):
            An approved article associated with a publisher.
        unapproved_article (Article):
            A draft article used to test filtering and permission logic.

    Returns:
        None
            This setup method prepares the test environment but does not return a value.
    """
    def setUp(self):
        self.client = APIClient()

        # Categories
        self.category = ArticleCategory.objects.create(name="Tech")

        # Users
        self.reader = User.objects.create_user(username="reader", password="pass")
        self.reader_profile = UserProfile.objects.create(user=self.reader, role="reader")
        self.reader_profile.preferred_categories.add(self.category)

        self.journalist = User.objects.create_user(username="journalist", password="pass")
        self.journalist_profile = UserProfile.objects.create(user=self.journalist, role="journalist")

        self.independent = User.objects.create_user(username="independent", password="pass")
        self.independent_profile = UserProfile.objects.create(user=self.independent, role="independent")

        self.publisher = User.objects.create_user(username="publisher", password="pass")
        self.publisher_profile = UserProfile.objects.create(user=self.publisher, role="publisher")

        self.editor = User.objects.create_user(username="editor", password="pass")
        self.editor_profile = UserProfile.objects.create(user=self.editor, role="editor")

        # Subscriptions
        self.reader_profile.subscribed_journalists.add(self.journalist)
        self.reader_profile.subscribed_publishers.add(self.publisher)

        # Articles
        self.approved_article_journalist = Article.objects.create(
            title="Approved by journalist",
            content="Content",
            status="approved",
            category=self.category,
            author=self.journalist,
        )

        self.approved_article_publisher = Article.objects.create(
            title="Approved by publisher",
            content="Content",
            status="approved",
            category=self.category,
            author=self.independent,
            publisher=self.publisher,
        )

        self.unapproved_article = Article.objects.create(
            title="Draft article",
            content="Content",
            status="draft",
            category=self.category,
            author=self.journalist,
        )


class AuthRoleTests(BaseAPITestCase):
    """
    Test suite validating authentication and role‑based permissions for API endpoints
    related to article creation and subscribed‑content retrieval.

    These tests ensure that:
        - Readers can successfully access the subscribed‑articles endpoint.
        - Anonymous users receive an empty result set when accessing the same endpoint.
        - Journalists are permitted to create articles through the API.
        - Readers are forbidden from creating articles.

    The class inherits from `BaseAPITestCase`, which provides a fully prepared
    environment including users, roles, categories, subscriptions, and sample
    articles.

    Test Cases:
        test_reader_can_access_subscribed_endpoint:
            Verifies that an authenticated reader receives a 200 OK response when
            accessing the subscribed‑articles API.

        test_anonymous_cannot_see_subscribed_articles:
            Ensures that unauthenticated users receive a 200 OK response but with
            an empty dataset, confirming that the endpoint does not expose
            subscription‑based content to anonymous visitors.

        test_journalist_can_create_article:
            Confirms that a logged‑in journalist can successfully create an article
            via the API, receiving a 201 CREATED response and correct author data.

        test_reader_cannot_create_article:
            Ensures that a reader attempting to create an article receives a
            403 FORBIDDEN response, validating role‑based write restrictions.

    Returns:
        None
            This class defines test methods executed by Django’s test runner.
    """
    
    def test_reader_can_access_subscribed_endpoint(self):
        self.client.login(username="reader", password="pass")
        url = reverse("api_articles_subscribed")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_anonymous_cannot_see_subscribed_articles(self):
        url = reverse("api_articles_subscribed")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_journalist_can_create_article(self):
        self.client.login(username="journalist", password="pass")
        url = reverse("api_article_create")
        payload = {
            "title": "API Created Article",
            "content": "Body",
            "category": self.category.id,
        }
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["title"], "API Created Article")
        self.assertEqual(resp.data["author"], self.journalist.username)

    def test_reader_cannot_create_article(self):
        self.client.login(username="reader", password="pass")
        url = reverse("api_article_create")
        payload = {
            "title": "Should Fail",
            "content": "Body",
            "category": self.category.id,
        }
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class ReaderSubscriptionTests(BaseAPITestCase):
    """
    Test suite ensuring that readers only receive articles from the publishers
    and journalists they are subscribed to.

    This class verifies the filtering logic behind the subscribed‑articles API
    endpoint. It ensures that:
        - Readers receive approved articles from the journalists they follow.
        - Readers receive approved articles from the publishers they follow.
        - Unapproved or draft articles are never included in the response.

    Inherits from `BaseAPITestCase`, which provides a complete test environment
    including users, roles, subscriptions, and sample articles.

    Test Cases:
        test_reader_only_gets_subscribed_content:
            Confirms that an authenticated reader receives:
                * Approved articles from subscribed journalists.
                * Approved articles from subscribed publishers.
                * No draft or unapproved articles.
            Validates both the HTTP response and the returned article titles.

    Returns:
        None
            This class defines test methods executed by Django’s test runner.
    """
    def test_reader_only_gets_subscribed_content(self):
        self.client.login(username="reader", password="pass")
        url = reverse("api_articles_subscribed")
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        titles = {a["title"] for a in resp.data}
        self.assertIn("Approved by journalist", titles)
        self.assertIn("Approved by publisher", titles)
        self.assertNotIn("Draft article", titles)


class EditorApprovalDeleteTests(BaseAPITestCase):
    """
    Test suite validating editor permissions for approving and deleting articles,
    as well as ensuring journalists cannot delete content they do not own.

    These tests confirm the correct enforcement of newsroom permission rules:
        - Editors can approve unapproved articles.
        - Editors can delete any article belonging to their publisher ecosystem.
        - Journalists are restricted from deleting articles they did not author.

    Inherits from `BaseAPITestCase`, which provides a complete environment with
    users, roles, subscriptions, and sample articles.

    Test Cases:
        test_editor_can_approve_article:
            Ensures that an authenticated editor can update an article’s status
            from draft (or any non‑approved state) to "approved". After the PUT
            request, the article is refreshed from the database to verify the
            status change.

        test_editor_can_delete_article:
            Confirms that an editor can delete an article, receiving a
            204 NO CONTENT response. The test also verifies that the article
            no longer exists in the database.

        test_journalist_cannot_delete_others_article:
            Validates that a journalist cannot delete an article authored by
            someone else. The API should return a 403 FORBIDDEN response,
            enforcing ownership‑based restrictions.

    Returns:
        None
            This class defines test methods executed by Django’s test runner.
    """
    def test_editor_can_approve_article(self):
        self.client.login(username="editor", password="pass")
        url = reverse("api_article_update", kwargs={"pk": self.unapproved_article.id})
        payload = {
            "title": self.unapproved_article.title,
            "content": self.unapproved_article.content,
            "category": self.category.id,
            "status": "approved",
        }
        resp = self.client.put(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        self.unapproved_article.refresh_from_db()
        self.assertEqual(self.unapproved_article.status, "approved")

    def test_editor_can_delete_article(self):
        self.client.login(username="editor", password="pass")
        url = reverse("api_article_delete", kwargs={"pk": self.approved_article_journalist.id})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Article.objects.filter(id=self.approved_article_journalist.id).exists())

    def test_journalist_cannot_delete_others_article(self):
        self.client.login(username="journalist", password="pass")
        url = reverse("api_article_delete", kwargs={"pk": self.approved_article_publisher.id})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class NewsletterTests(BaseAPITestCase):
    """
    Test suite validating newsletter creation behavior for editors, including
    attaching multiple approved articles to a newly created topic‑based newsletter.

    This class ensures that the newsletter creation workflow functions correctly
    when performed by an editor, who is authorized to curate and publish
    newsletters. It verifies that:
        - Editors can successfully submit a newsletter creation request.
        - The system redirects after successful creation.
        - The newsletter is stored in the database with the correct title.
        - All selected articles are properly associated with the newsletter.

    Inherits from `BaseAPITestCase`, which provides a complete testing environment
    including users, roles, categories, subscriptions, and sample articles.

    Test Cases:
        test_editor_can_create_newsletter_with_articles:
            Confirms that an authenticated editor can create a topic‑based
            newsletter containing multiple approved articles. After submitting
            the POST request, the test verifies:
                * A redirect response (302) indicating successful creation.
                * The newsletter exists in the database.
                * The correct number of articles is attached to the newsletter.

    Returns:
        None
            This class defines test methods executed by Django’s test runner.
    """
    def test_editor_can_create_newsletter_with_articles(self):
        self.client.login(username="editor", password="pass")
        url = reverse("create_topic_newsletter")  # your view name
        payload = {
            "title": "Tech Digest",
            "description": "Latest tech news",
            "category": self.category.id,
            "articles": [self.approved_article_journalist.id, self.approved_article_publisher.id],
        }
        resp = self.client.post(url, payload)
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)  # redirect after create

        self.assertTrue(Newsletter.objects.filter(title="Tech Digest").exists())
        newsletter = Newsletter.objects.get(title="Tech Digest")
        self.assertEqual(newsletter.articles.count(), 2)


class SignalAndIntegrationTests(BaseAPITestCase):
    """
    Test suite verifying that signal‑driven behaviors and external integrations
    (email notifications and Twitter posting) are correctly triggered by API actions.

    These tests ensure that:
        - Creating a newsletter triggers the email‑notification logic.
        - Approving an article triggers the Twitter posting integration.
        - External services are mocked to avoid real network calls during testing.

    Inherits from `BaseAPITestCase`, which provides a complete environment with
    users, roles, categories, subscriptions, and sample articles.

    Test Cases:
        test_newsletter_email_logic_called:
            Uses `unittest.mock.patch` to replace `send_mail` with a mock.
            Confirms that when an editor creates a newsletter, the email‑sending
            logic is invoked. A redirect (302) indicates successful creation, and
            the mock verifies that the email function was called.

        test_twitter_post_on_approval:
            Mocks the `TweetClient` class to prevent real API calls.
            Ensures that when an editor updates an article’s status to "approved",
            the Twitter client is instantiated and its `tweet_text` method is
            called exactly once, confirming that the integration logic executed.

    Returns:
        None
            This class defines test methods executed by Django’s test runner.
    """
    @patch("posts.views.send_mail")
    def test_newsletter_email_logic_called(self, mock_send_mail):
        self.client.login(username="editor", password="pass")
        url = reverse("create_topic_newsletter")
        payload = {
            "title": "Tech Digest",
            "description": "Latest tech news",
            "category": self.category.id,
            "articles": [self.approved_article_journalist.id],
        }
        resp = self.client.post(url, payload)
        self.assertEqual(resp.status_code, status.HTTP_302_FOUND)
        self.assertTrue(mock_send_mail.called)

    @patch("posts.api_views.TweetClient")
    def test_twitter_post_on_approval(self, mock_tweet_client_cls):
        self.client.login(username="editor", password="pass")
        url = reverse("api_article_update", kwargs={"pk": self.unapproved_article.id})
        payload = {
            "title": self.unapproved_article.title,
            "content": self.unapproved_article.content,
            "category": self.category.id,
            "status": "approved",
        }
        resp = self.client.put(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        mock_tweet_client_cls.assert_called_once()
        mock_tweet_client_cls.return_value.tweet_text.assert_called_once()