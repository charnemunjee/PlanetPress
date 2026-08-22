from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import ArticleCategory

@receiver(post_migrate)
def create_default_categories(sender, **kwargs):
    default_categories = [
        "Politics",
        "Business",
        "Technology",
        "Science",
        "Health",
        "Environment",
        "Education",
        "Crime & Justice",
        "Entertainment",
        "Arts & Culture",
        "Lifestyle",
        "Travel",
        "Food",
        "Sports",
        "Fitness",
        "World News",
        "Africa News",
        "Local News",
        "Opinion",
        "Editorials",
        "Analysis",
    ]

    for name in default_categories:
        ArticleCategory.objects.get_or_create(name=name)