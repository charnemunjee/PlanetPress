from django.shortcuts import redirect
from django.urls import reverse

class RolePermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        protected_paths = {
            "publish_article": ["independent", "publisher"],
            "review_article": ["editor"],
            "request_review": ["independent", "publisher"],
        }

        path_name = request.resolver_match.url_name if request.resolver_match else None

        if path_name in protected_paths:
            allowed_roles = protected_paths[path_name]
            if request.user.is_authenticated:
                if request.user.profile.role not in allowed_roles:
                    return redirect("dashboard")

        return self.get_response(request)