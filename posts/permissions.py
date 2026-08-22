from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsJournalistOrEditor(BasePermission):
    """
    Permission class that grants access only to authenticated users with a newsroom role.

    This permission ensures that only users who are journalists, independent
    journalists, or editors can perform actions such as creating, updating, or
    deleting articles through the API. It is typically applied to views that
    modify newsroom content, preventing unauthorized users—such as readers or
    unauthenticated visitors—from performing write operations.

    Behavior:
        - Returns False if the user is not authenticated.
        - Retrieves the user's role from their profile.
        - Allows access only if the role is one of:
              * "journalist"
              * "independent"
              * "editor"

    Methods:
        has_permission(request, view):
            Checks whether the requesting user is authenticated and has a valid
            newsroom role.

    Returns:
        bool:
            True if the user is an authenticated journalist, independent
            journalist, or editor; otherwise False.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        role = request.user.profile.role
        # For POST, PUT, DELETE
        return role in ["journalist", "independent", "editor"]

class IsOwnerOrEditor(BasePermission):
    """
    Permission class that grants access to the owner of an object or editors.

    This permission ensures that only the user who created an article (the owner)
    or a user with the "editor" role can update or delete the article. It is
    typically applied to views that modify specific article instances.

    Behavior:
        - Returns False if the user is not authenticated.
        - Retrieves the user's role from their profile.
        - Allows access if the user is an editor or the owner of the object.

    Methods:
        has_object_permission(request, view, obj):
            Checks whether the requesting user has permission to access a specific
            article instance.

    Returns:
        bool:
            True if the user is an editor or the owner of the article; otherwise False.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        role = request.user.profile.role
        # Editors can edit/delete anything, journalists only their own
        return role == "editor" or obj.author == request.user