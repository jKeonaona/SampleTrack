from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapper
