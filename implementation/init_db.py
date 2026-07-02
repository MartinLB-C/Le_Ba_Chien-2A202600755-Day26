import sqlite3
from pathlib import Path
from typing import Union

SCHEMA_SQL = """
DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    score REAL NOT NULL
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    grade TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (course_id) REFERENCES courses(id)
);
"""

SEED_SQL = """
INSERT INTO students (name, cohort, score) VALUES
    ('Nguyen Van An', 'A1', 88.5),
    ('Tran Thi Mai', 'A1', 92.0),
    ('Le Ba Chien', 'A2', 95.5),
    ('Pham Minh Duc', 'A2', 78.0),
    ('Hoang Thuy Linh', 'B1', 85.0),
    ('Vuong Quang Huy', 'B1', 90.0);

INSERT INTO courses (title, credits) VALUES
    ('Database Systems', 4),
    ('Artificial Intelligence', 4),
    ('Web Development', 3),
    ('Data Structures & Algorithms', 4);

INSERT INTO enrollments (student_id, course_id, grade) VALUES
    (1, 1, 'A'),
    (1, 2, 'B+'),
    (2, 1, 'A+'),
    (3, 1, 'A+'),
    (3, 2, 'A'),
    (4, 3, 'B'),
    (5, 3, 'A-'),
    (6, 4, 'A');
"""


def create_database(db_path: Union[str, Path, None] = None) -> Path:
    """
    Creates and initializes the SQLite database with schema and seed data.
    """
    if db_path is None:
        db_path = Path(__file__).parent / "school.db"
    else:
        db_path = Path(db_path)

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.executescript(SCHEMA_SQL)
        cursor.executescript(SEED_SQL)
        conn.commit()
    finally:
        conn.close()

    return db_path


if __name__ == "__main__":
    path = create_database()
    print(f"Database successfully created and seeded at: {path}")
