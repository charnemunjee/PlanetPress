from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone


# Create your models here.
class ArticleCategory(models.Model):
    """
    Represents a topic or classification under which articles are grouped.

    Categories help organize content across the PlanetPress platform and allow:
    - Journalists to assign a topic to their articles.
    - Readers to subscribe to topics they are interested in.
    - Editors to generate topic‑based newsletters.
    - API clients to filter articles by category.

    Fields:
        name (CharField):
            The unique name of the category (e.g., "Technology", "Politics").
            Maximum length is 50 characters.
    """
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
    

class Article(models.Model):
    """
    Represents a news article created by a journalist or independent writer.

    Articles may optionally belong to a publisher and always belong to a category.
    Editors can review, approve, or reject articles, and may leave feedback.

    Fields:
        title (CharField):
            The headline or title of the article (max 255 characters).

        content (TextField):
            The full body text of the article.

        author (ForeignKey to User):
            The journalist or independent writer who created the article.

        publisher (ForeignKey to User, optional):
            The publisher responsible for the article.
            Null for independent journalists.
            Uses SET_NULL to preserve articles if the publisher account is removed.

        category (ForeignKey to ArticleCategory):
            The topic or classification the article belongs to.

        status (CharField):
            The workflow state of the article.
            Common values include:
                - "draft"
                - "submitted"
                - "approved"
                - "rejected"
            Defaults to "draft".

        editor_feedback (TextField, optional):
            Comments or revision notes left by an editor during review.

        created_at (DateTimeField):
            Timestamp automatically set when the article is first created.

        updated_at (DateTimeField):
            Timestamp automatically updated whenever the article is modified.
    """
    title = models.CharField(max_length=255)
    content = models.TextField()

    author = models.ForeignKey(User, on_delete=models.CASCADE)

    # Article belongs to either a publisher or an independent journalist
    publisher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="publisher_articles"
    )

    reviewed_by = models.ForeignKey(
    User,
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="reviewed_articles"
)

    category = models.ForeignKey(ArticleCategory, on_delete=models.SET_NULL, null=True)

    status = models.CharField(max_length=20, default="draft")
    editor_feedback = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class UserProfile(models.Model):
    """
    Extends the Django User model with role-based permissions, publisher
    relationships, and subscription functionality for the PlanetPress platform.

    This model defines all user roles in the system—reader, independent
    journalist, journalist, editor, and publisher—and automatically assigns
    capabilities based on the selected role. It also manages relationships
    between publishers and their teams, as well as reader subscriptions to
    journalists, publishers, and content categories.

    Roles:
        - reader: Can read articles and subscribe to journalists/publishers.
        - independent: Can publish independently without belonging to a publisher.
        - journalist: Belongs to a publisher and can publish/request review.
        - editor: Belongs to a publisher and can review, approve, and manage content.
        - publisher: Owns a publishing organization and manages journalists/editors.

    Fields:
        user (OneToOneField):
            The associated Django User account.

        role (CharField):
            The user's role within the platform. Determines permissions and behavior.

        publisher (ForeignKey to User, optional):
            The publisher this user belongs to (for journalists/editors).
            Independent journalists and publishers have this set to None.

        subscribed_publishers (ManyToManyField to User):
            Publishers that a reader follows. Used for personalized article feeds
            and newsletter delivery.

        subscribed_journalists (ManyToManyField to User):
            Journalists that a reader follows. Used for personalized content feeds.

        can_read (BooleanField):
            Whether the user can read articles. Always True.

        can_publish (BooleanField):
            Whether the user can publish articles (journalists, independents, publishers).

        can_request_review (BooleanField):
            Whether the user can submit articles for editorial review.

        can_review (BooleanField):
            Whether the user can review and approve articles (editors only).

        can_update (BooleanField):
            Whether the user can update articles (journalists, editors, publishers).

        can_delete (BooleanField):
            Whether the user can delete articles (journalists, editors, publishers).

        preferred_categories (ManyToManyField to ArticleCategory):
            Categories a reader is interested in. Used for topic‑based newsletters
            and personalized recommendations.

    save():
        Overrides the default save method to automatically assign permissions
        and publisher relationships based on the user's role. Ensures consistent
        behavior across the platform and prevents invalid role configurations.

    __str__():
        Returns a readable representation of the profile in the format:
        "<username> (<role>)".
    """
    ROLE_CHOICES = [
        ("reader", "Reader"),
        ("independent", "Independent Journalist"),
        ("journalist", "Journalist"),
        ("editor", "Editor"),
        ("publisher", "Publisher"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    # Journalists and editors belong to a publisher
    publisher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="publisher_team"
    )

    # NEW: Reader subscriptions
    subscribed_journalists = models.ManyToManyField(
        User,
        related_name="journalist_subscribers",
        blank=True
        )
    
    subscribed_publishers = models.ManyToManyField(
        User,
        related_name="publisher_subscribers",
        blank=True
        )


    # Capability flags
    can_read = models.BooleanField(default=True)
    can_publish = models.BooleanField(default=False)
    can_request_review = models.BooleanField(default=False)
    can_review = models.BooleanField(default=False)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    # Reader-selected categories
    preferred_categories = models.ManyToManyField(
        ArticleCategory,
        blank=True,
        related_name="readers"
    )

    def save(self, *args, **kwargs):

        # Readers
        if self.role == "reader":
            self.can_publish = False
            self.can_request_review = False
            self.can_review = False
            self.publisher = None

        # Independent journalists
        elif self.role == "independent":
            self.can_publish = True
            self.can_request_review = True
            self.can_review = False
            self.can_update = True
            self.can_delete = True
            self.publisher = None

        # Journalists belonging to a publisher
        elif self.role == "journalist":
            self.can_publish = True
            self.can_request_review = True
            self.can_review = False
            self.can_update = True
            self.can_delete = True

        # Editors belonging to a publisher
        elif self.role == "editor":
            self.can_publish = False
            self.can_request_review = False
            self.can_review = True
            self.can_update = True
            self.can_delete = True

        # Publishers
        elif self.role == "publisher":
            self.can_publish = True
            self.can_request_review = True
            self.can_review = False
            self.can_update = True
            self.can_delete = True
            self.publisher = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class ResetToken(models.Model):
    """
    Stores password reset tokens for secure account recovery.

    Fields:
        user (ForeignKey):
            The user requesting a password reset.
        token (CharField):
            A unique, securely generated token used to validate the reset request.
        expiry_date (DateTimeField):
            The timestamp indicating when the token becomes invalid.
        used (BooleanField):
            Marks whether the token has already been consumed.

    Purpose:
        Ensures secure, time‑limited password reset functionality by tracking
        token usage and expiration.

    Methods:
        None custom, but Django provides default model behavior.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=500)
    expiry_date = models.DateTimeField()
    used = models.BooleanField(default=False)

    def __str__(self):
        return f"Token for {self.user.username}"


class Newsletter(models.Model):
    """
    Represents a curated collection of articles created within the PlanetPress
    platform for distribution to readers.

    A newsletter may be authored by an editor, journalist, or publisher and can
    contain any number of articles. Newsletters are commonly used for topic‑based
    digests, editorial roundups, or automated content delivery to subscribed
    readers. They may also be sent via email or exposed through the REST API.

    Fields:
        title (CharField):
            The title or headline of the newsletter. Maximum length is 255
            characters.

        description (TextField):
            An optional summary or introduction describing the theme or purpose
            of the newsletter.

        author (ForeignKey to User):
            The user who created the newsletter. If the user is deleted, all
            newsletters they authored are also removed. This field may be null
            for system‑generated newsletters.

        articles (ManyToManyField to Article):
            The set of articles included in the newsletter. This relationship
            allows newsletters to contain zero or more articles.

        created_at (DateTimeField):
            Timestamp automatically set when the newsletter is created.

    __str__():
        Returns the newsletter's title for readable display in admin interfaces,
        logs, and debugging contexts.
    """

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    author = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name="newsletters",
    null=True,
    blank=True
    )

    articles = models.ManyToManyField(
        Article,
        related_name="newsletters",
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Notification(models.Model):
    """
    Represents a system‑generated alert or message delivered to a specific user
    within the PlanetPress platform.

    Notifications are used to inform users about important events such as:
    - New newsletters from subscribed publishers or journalists
    - Article approvals, rejections, or editorial feedback
    - Updates from followed journalists or publishers
    - System messages or platform‑level announcements

    Each notification is tied to a single user and includes a message body,
    a read/unread state, and a timestamp indicating when it was created.
    Notifications are typically displayed in a user's dashboard and may be
    marked as read once viewed.

    Fields:
        user (ForeignKey to User):
            The user who receives the notification. If the user is deleted,
            all associated notifications are removed.

        message (TextField):
            The content of the notification. This may include plain text or
            dynamically generated system messages.

        is_read (BooleanField):
            Indicates whether the user has viewed or acknowledged the
            notification. Defaults to False.

        created_at (DateTimeField):
            Timestamp automatically set when the notification is created.
            Useful for sorting notifications chronologically.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)








