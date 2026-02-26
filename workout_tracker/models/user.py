from shared.user import User  # noqa: F401 – re-exported for other imports
from .. import login_manager, db


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
