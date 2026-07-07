from ....modals import db
from ....modals.students_db import Student
from sqlalchemy import func

import threading

branch_locks = {}

def get_branch_lock(branch_id):
    if branch_id not in branch_locks:
        branch_locks[branch_id] = threading.Lock()
    return branch_locks[branch_id]

def get_next_adm_no(branch_id):
    lock = get_branch_lock(branch_id)

    with lock:
        max_adm = (
            db.session.query(func.max(Student.admission_number))
            .filter(Student.branch_id == branch_id)
            .scalar()
        )

        return (max_adm or 0) + 1