def user_roles(request):
    user = request.user

    is_admin = user.is_authenticated and (
        user.is_superuser or user.groups.filter(name='Admin').exists()
    )

    is_manager = user.is_authenticated and user.groups.filter(name='Manager').exists()

    is_staff = user.is_authenticated and user.groups.filter(name='Staff').exists()

    return {
        'is_admin': is_admin,
        'is_manager': is_manager,
        'is_staff': is_staff,
    }
