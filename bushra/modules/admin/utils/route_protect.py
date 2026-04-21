from functools import wraps 
from flask import redirect, url_for
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            # Redirect non-admins to their assessment dashboard
            return redirect(url_for("admin.teacher_dash"))
        return f(*args, **kwargs)
    return decorated_function