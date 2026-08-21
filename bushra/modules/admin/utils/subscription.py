from datetime import date, datetime


DUE_SOON_DAYS = 7
# Hardcoded until billing is stored.
SUBSCRIPTION_DUE_ON = date(2026, 9, 5)


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _date_label(value):
    return f"{value.day} {value.strftime('%b %Y')}"


def subscription_for_branch(branch, today=None):
    """Monthly plan status from a fixed due date (placeholder)."""
    if not branch:
        return None

    today = today or date.today()
    due_on = _as_date(SUBSCRIPTION_DUE_ON)
    if not due_on:
        return None

    days_left = (due_on - today).days
    date_label = _date_label(due_on)

    if days_left < 0:
        return {
            "state": "overdue",
            "status_label": "Overdue",
            "detail": date_label,
            "renewal_date": date_label,
            "days_left": days_left,
        }

    if days_left <= DUE_SOON_DAYS:
        if days_left == 0:
            detail = "due today"
        elif days_left == 1:
            detail = "in 1 day"
        else:
            detail = f"in {days_left} days"

        return {
            "state": "due_soon",
            "status_label": "Due soon",
            "detail": detail,
            "renewal_date": date_label,
            "days_left": days_left,
        }

    return {
        "state": "active",
        "status_label": "Active",
        "detail": f"{days_left} days left",
        "renewal_date": date_label,
        "days_left": days_left,
    }
