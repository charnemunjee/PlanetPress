# posts/urls.py
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (create_newsletter,
                    delete_article,
                    delete_newsletter,
                    edit_article_per_role, 
                    journalist_edit_newsletter,
                    editor_newsletters,
                    editor_unreviewed_articles,
                    editor_reviewed_articles,
                    editor_dashboard,
                    follow_user, following_list,
                    journalist_dashboard, publisher_dashboard, 
                    reader_dashboard, reader_newsletters,
                    review_article,
                    select_reader_preferences,
                    submit_article, submit_for_review, unfollow_user,
                    update_reader_preferences, view_article, view_newsletter,
                    welcome,
                    login_user,
                    register_user,
                    forgot_password,
                    send_password_reset_email,
                    reset_password,
                    logout_user,
                    reader_all_articles,
                    reader_view_article, 
                    writer_notifications,
                    editors_edit_newsletter,
                    journalist_articles_reader,
                    publisher_articles_reader,
                    )

from .api_views import (
    ArticleListAPIView,
    SubscribedArticlesAPIView,
    ArticleDetailAPIView,
    ArticleCreateAPIView,
    ArticleUpdateAPIView,
    ArticleDeleteAPIView,
)

urlpatterns = [

    # URL pattern for welcome page, login an logout
    path("", welcome, name="welcome"),
    path("login/", login_user, name="login_user"),
    path("logout/", logout_user, name="logout_user"),

    # authentication urls
    path("register_user/", register_user, name="register_user"),
    path("forgot_password/", forgot_password, name="forgot_password"),
    path("send_password_reset_email/", send_password_reset_email, name="send_password_reset_email"),
    path("reset_password/<str:token>/", reset_password, name="reset_password"),

    # reader functionality
    path("articles/", reader_all_articles, name="reader_all_articles"),
    path("articles/<int:article_id>/", reader_view_article, name="reader_view_article"),
    path("reader/select_preferences/", select_reader_preferences, name="select_reader_preferences"),
    path("reader/update_preferences/", update_reader_preferences, name="update_reader_preferences"),
    path("reader/dashboard/", reader_dashboard, name="reader_dashboard"),
    path("follow/<int:user_id>/", follow_user, name="follow_user"),
    path("unfollow/<int:user_id>/", unfollow_user, name="unfollow_user"),
    path("following/", following_list, name="following_list"),
    path("journalist/<int:user_id>/articles/", journalist_articles_reader, name="journalist_articles_reader"),
    path("publisher/<int:user_id>/articles/", publisher_articles_reader, name="publisher_articles_reader"),

    # editor functionality
    path("editor/dashboard/", editor_dashboard, name="editor_dashboard"),
    path("editor/review/<int:article_id>/", review_article, name="review_article"),
    path("editor/unreviewed/", editor_unreviewed_articles, name="editor_unreviewed_articles"),
    path("editor/reviewed/", editor_reviewed_articles, name="editor_reviewed_articles"),
    path("editor/newsletters/", editor_newsletters, name="editor_newsletters"),
    path("editor/delete-newsletter/<int:newsletter_id>/", delete_newsletter, name="delete_newsletter_editor"),
    path("editor/edit-newsletter/<int:newsletter_id>/", editors_edit_newsletter, name="editors_edit_newsletter"),
    

    #journalist functionality
    path("journalist/dashboard/", journalist_dashboard, name="journalist_dashboard"),
    path("journalist/submit/", submit_article, name="submit_article"),
    path("journalist/delete/<int:article_id>/", delete_article, name="delete_article"),
    path("article/<int:article_id>/", view_article, name="view_article"),
    path("journalist/submit-review/<int:article_id>/", submit_for_review, name="submit_for_review"),
    path("journalist/delete-newsletter/<int:newsletter_id>/", delete_newsletter, name="delete_newsletter"),
    path("journalist/<int:newsletter_id>/edit-newsletter/", journalist_edit_newsletter, name="journalist_edit_newsletter"),


    # publisher functionality
    path("publisher/dashboard/", publisher_dashboard, name="publisher_dashboard"),
    path("edit/<int:article_id>/", edit_article_per_role, name="edit_article"),
    path("notifications/", writer_notifications, name="writer_notifications"),
    path("delete/<int:article_id>/", delete_article, name="delete_article"),

    # newsletter functionality
    path("newsletter/create/", create_newsletter, name="create_newsletter"),
    path("reader/newsletters/", reader_newsletters, name="reader_newsletters"),
    path("newsletter/<int:newsletter_id>/", view_newsletter, name="view_newsletter"),
    
    # API endpoints
    path("api/articles/", ArticleListAPIView.as_view(), name="api_articles_list"),
    path("api/articles/subscribed/", SubscribedArticlesAPIView.as_view(), name="api_articles_subscribed"),
    path("api/articles/<int:pk>/", ArticleDetailAPIView.as_view(), name="api_article_detail"),
    path("api/articles/create/", ArticleCreateAPIView.as_view(), name="api_article_create"),
    path("api/articles/<int:pk>/update/", ArticleUpdateAPIView.as_view(), name="api_article_update"),
    path("api/articles/<int:pk>/delete/", ArticleDeleteAPIView.as_view(), name="api_article_delete"),

]