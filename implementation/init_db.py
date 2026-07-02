from __future__ import annotations

import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).with_name("sqlite_lab.db")


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    gpa REAL NOT NULL CHECK (gpa >= 0 AND gpa <= 4.0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0)
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    semester TEXT NOT NULL,
    score REAL NOT NULL CHECK (score >= 0 AND score <= 100),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE (student_id, course_id, semester)
);
"""


SEED_SQL = """
INSERT INTO students (name, cohort, email, gpa) VALUES
    ('Tran Gia Huy', 'A1', 'huy.tran@example.edu', 3.72),
    ('Nguyen Minh Anh', 'A1', 'anh.nguyen@example.edu', 3.91),
    ('Le Bao Chau', 'A2', 'chau.le@example.edu', 3.43),
    ('Pham Quang Minh', 'B1', 'minh.pham@example.edu', 3.28),
    ('Do Ha Linh', 'B1', 'linh.do@example.edu', 3.84),
    ('Hoang Nam', 'A2', 'nam.hoang@example.edu', 3.11);

INSERT INTO courses (code, title, credits) VALUES
    ('CS101', 'Introduction to Programming', 3),
    ('DATA201', 'Database Systems', 3),
    ('AI301', 'Applied Machine Learning', 4),
    ('STAT210', 'Statistics for Data Science', 3);

INSERT INTO enrollments (student_id, course_id, semester, score) VALUES
    (1, 1, '2026S', 91.5),
    (1, 2, '2026S', 88.0),
    (2, 1, '2026S', 95.0),
    (2, 3, '2026S', 92.0),
    (3, 2, '2026S', 81.5),
    (3, 4, '2026S', 84.0),
    (4, 1, '2026S', 76.0),
    (4, 4, '2026S', 79.5),
    (5, 2, '2026S', 90.5),
    (5, 3, '2026S', 94.0),
    (6, 1, '2026S', 72.5),
    (6, 4, '2026S', 78.0);
"""


def create_database(db_path: str | Path | None = None, reset: bool = True) -> Path:
    """Create a reproducible SQLite database and return its path."""
    path = Path(db_path) if db_path is not None else DATABASE_PATH
    database_exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        if reset:
            conn.executescript(
                """
                DROP TABLE IF EXISTS enrollments;
                DROP TABLE IF EXISTS courses;
                DROP TABLE IF EXISTS students;
                """
            )
        conn.executescript(SCHEMA_SQL)
        if reset or not database_exists:
            conn.executescript(SEED_SQL)
        conn.commit()

    return path


if __name__ == "__main__":
    db_path = create_database()
    print(f"Created database at {db_path}")
