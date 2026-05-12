"""
Authentication layer — SQLite-backed user store with Flask-Login.

Tables:
  users    — id, name, email, password_hash, role ('faculty'|'student'), created_at
  sim_runs — id, user_id, scenario, days, fill_rate, total_cost, ran_at

Demo credentials (seeded on first run):
  faculty@university.edu / faculty123  (role: faculty)
  student1@university.edu / student123 (role: student)
  student2@university.edu / student123 (role: student)
"""

import os
import sqlite3

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

# Vercel's filesystem is read-only except /tmp; fall back to local for dev.
DB_PATH = os.environ.get(
    "DB_PATH",
    "/tmp/supplychain.db" if os.environ.get("VERCEL") else "supplychain.db",
)


# ── User model ────────────────────────────────────────────────────────────────

class User(UserMixin):
    def __init__(self, row):
        self.id         = str(row["id"])
        self.name       = row["name"]
        self.email      = row["email"]
        self.role       = row["role"]
        self.created_at = row["created_at"]

    @property
    def is_faculty(self):
        return self.role == "faculty"

    @property
    def initials(self):
        parts = self.name.split()
        return (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else self.name[:2].upper()


# ── DB helpers ────────────────────────────────────────────────────────────────

def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                email         TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                role          TEXT    NOT NULL DEFAULT 'student',
                created_at    TEXT    DEFAULT (datetime('now'))
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS sim_runs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                scenario   TEXT    NOT NULL,
                days       INTEGER NOT NULL,
                fill_rate  REAL,
                total_cost REAL,
                ran_at     TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        _seed(db)
        db.commit()


def _seed(db):
    demo = [
        ("Dr. Sarah Chen",  "faculty@university.edu",  "faculty123", "faculty"),
        ("Alex Johnson",    "student1@university.edu", "student123", "student"),
        ("Maria Garcia",    "student2@university.edu", "student123", "student"),
    ]
    for name, email, pwd, role in demo:
        if not db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            db.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
                (name, email, generate_password_hash(pwd), role),
            )


# ── CRUD ──────────────────────────────────────────────────────────────────────

def get_user(user_id: str):
    with _conn() as db:
        row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return User(row) if row else None


def authenticate(email: str, password: str):
    """Returns User on success, None on failure."""
    with _conn() as db:
        row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        return User(row)
    return None


def all_users():
    with _conn() as db:
        rows = db.execute(
            "SELECT id, name, email, role, created_at FROM users ORDER BY role, name"
        ).fetchall()
        return [dict(r) for r in rows]


def create_user(name: str, email: str, password: str, role: str):
    """Returns (ok: bool, error: str|None)."""
    with _conn() as db:
        try:
            db.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
                (name, email, generate_password_hash(password), role),
            )
            db.commit()
            return True, None
        except sqlite3.IntegrityError:
            return False, "Email already registered."


def update_role(user_id: str, role: str):
    with _conn() as db:
        db.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
        db.commit()


def delete_user(user_id: str):
    with _conn() as db:
        db.execute("DELETE FROM users WHERE id=?", (user_id,))
        db.commit()


# ── Simulation run log ────────────────────────────────────────────────────────

def log_simulation(user_id: str, scenario: str, days: int,
                   fill_rate: float, total_cost: float):
    with _conn() as db:
        db.execute(
            "INSERT INTO sim_runs (user_id, scenario, days, fill_rate, total_cost) "
            "VALUES (?,?,?,?,?)",
            (user_id, scenario, days, fill_rate, total_cost),
        )
        db.commit()


def recent_simulations(limit: int = 30):
    with _conn() as db:
        rows = db.execute("""
            SELECT s.id, u.name AS user_name, u.email, u.role,
                   s.scenario, s.days, s.fill_rate, s.total_cost, s.ran_at
            FROM sim_runs s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.ran_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def stats():
    with _conn() as db:
        total_users   = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        faculty_count = db.execute("SELECT COUNT(*) FROM users WHERE role='faculty'").fetchone()[0]
        student_count = db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
        total_runs    = db.execute("SELECT COUNT(*) FROM sim_runs").fetchone()[0]
        avg_fill      = db.execute("SELECT AVG(fill_rate) FROM sim_runs").fetchone()[0] or 0
        return {
            "total_users":   total_users,
            "faculty_count": faculty_count,
            "student_count": student_count,
            "total_runs":    total_runs,
            "avg_fill_rate": round(avg_fill, 2),
        }
