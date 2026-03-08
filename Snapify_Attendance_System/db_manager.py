import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attendance.db")

def get_connection():
    """Returns a new connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initializes the database schema and performs any necessary migrations."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Teachers Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            phone TEXT DEFAULT ''
        )
    """)
    
    # 2. Students Table
    cursor.execute("PRAGMA table_info(students)")
    student_cols = [col[1] for col in cursor.fetchall()]
    if student_cols and 'teacher_email' not in student_cols:
        cursor.execute("ALTER TABLE students RENAME TO students_old")
        cursor.execute("CREATE TABLE students (roll_number TEXT, name TEXT, phone TEXT, email TEXT, teacher_email TEXT DEFAULT '', PRIMARY KEY (roll_number, teacher_email))")
        cursor.execute("INSERT OR IGNORE INTO students (roll_number, name, phone, email, teacher_email) SELECT roll_number, name, phone, email, '' FROM students_old")
        cursor.execute("DROP TABLE students_old")
    else:
        cursor.execute("CREATE TABLE IF NOT EXISTS students (roll_number TEXT, name TEXT, phone TEXT, email TEXT, teacher_email TEXT DEFAULT '', PRIMARY KEY (roll_number, teacher_email))")
        
    # 3. Attendance Table
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='attendance'")
    result = cursor.fetchone()
    if result:
        table_sql = result[0]
        if 'roll_number' not in table_sql or 'UNIQUE(roll_number,date,class_name' not in table_sql.replace(' ', ''):
            cursor.execute("PRAGMA table_info(attendance)")
            columns = [col[1] for col in cursor.fetchall()]
            has_class_col = 'class_name' in columns
            has_roll_col = 'roll_number' in columns

            cursor.execute("ALTER TABLE attendance RENAME TO attendance_old")
            cursor.execute("CREATE TABLE attendance (roll_number TEXT DEFAULT '', name TEXT, class_name TEXT DEFAULT '', time TEXT, date DATE, teacher_email TEXT DEFAULT '', UNIQUE(roll_number, date, class_name, teacher_email))")
            if has_roll_col and has_class_col:
                cursor.execute("INSERT OR IGNORE INTO attendance (roll_number, name, class_name, time, date) SELECT COALESCE(roll_number, ''), name, COALESCE(class_name, ''), time, date FROM attendance_old")
            elif has_class_col:
                cursor.execute("INSERT OR IGNORE INTO attendance (roll_number, name, class_name, time, date) SELECT '', name, COALESCE(class_name, ''), time, date FROM attendance_old")
            else:
                cursor.execute("INSERT OR IGNORE INTO attendance (roll_number, name, class_name, time, date) SELECT '', name, '', time, date FROM attendance_old")
            cursor.execute("DROP TABLE attendance_old")
    else:
        cursor.execute("CREATE TABLE IF NOT EXISTS attendance (roll_number TEXT DEFAULT '', name TEXT, class_name TEXT DEFAULT '', time TEXT, date DATE, teacher_email TEXT DEFAULT '', UNIQUE(roll_number, date, class_name, teacher_email))")
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # When run directly, initialize the database.
    init_db()
    print("Database initialized successfully.")
