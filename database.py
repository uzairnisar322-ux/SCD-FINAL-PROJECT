import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'quiz.db')

def get_db_connection():
    """Establishes and returns a database connection with dictionary-like row factory and active busy timeout."""
    try:
        # 30.0s timeout ensures concurrent requests queue up instead of locking out
        conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        # Enable foreign key support for cascade deletes
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        raise

def init_db():
    """Initializes the database schema and seeds initial data."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Users Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            )
        ''')
        
        # 2. Categories Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        
        # 3. Questions Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
            )
        ''')
        
        # 4. Scores Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                max_score INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
            )
        ''')
        
        # 5. Topic Requests Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS topic_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                votes INTEGER NOT NULL DEFAULT 1,
                admin_note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # 6. Topic Votes Table (Enforces single vote per user even across sessions)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS topic_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic_request_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (topic_request_id) REFERENCES topic_requests (id) ON DELETE CASCADE,
                UNIQUE(user_id, topic_request_id)
            )
        ''')
        
        conn.commit()
        
        # Seed default data if empty
        seed_data(conn)
    finally:
        if conn:
            conn.close()

def seed_data(conn):
    cursor = conn.cursor()
    
    # Check if admin already exists, if not seed admin/admin123 and user/user123
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                       ('admin', generate_password_hash('admin123'), 'admin'))
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                       ('user', generate_password_hash('user123'), 'user'))
        print("Seeded default users (admin/admin123, user/user123).")

    # Seed categories
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO categories (name) VALUES (?)", ('Software Engineering',))
        cursor.execute("INSERT INTO categories (name) VALUES (?)", ('Web Development',))
        cursor.execute("INSERT INTO categories (name) VALUES (?)", ('General Trivia',))
        conn.commit()
        
        # Get category IDs
        cursor.execute("SELECT id, name FROM categories")
        categories = {row['name']: row['id'] for row in cursor.fetchall()}
        
        # Seed questions
        se_id = categories['Software Engineering']
        web_id = categories['Web Development']
        trivia_id = categories['General Trivia']
        
        # Software Engineering Questions
        se_questions = [
            (se_id, "Which of the following is NOT one of Lehman's Laws of Software Evolution?", 
             "Continuing Change", "Increasing Complexity", "Self-Regulation", "Immediate Perfection", "D"),
            (se_id, "In Scrum, who is responsible for maximizing the value of the product?", 
             "Scrum Master", "Product Owner", "Development Team", "Project Manager", "B"),
            (se_id, "What does the 'Refactoring' step in Test-Driven Development (TDD) aim to achieve?", 
             "Add new features", "Fix broken tests", "Improve code internal structure without changing behavior", "Write documentation", "C"),
            (se_id, "Which branch type in Git is traditionally used for integrating new features before release?", 
             "main", "develop", "feature", "hotfix", "B")
        ]
        
        # Web Development Questions
        web_questions = [
            (web_id, "What does HTML stand for?", 
             "Hyper Text Preprocessor", "Hyper Text Markup Language", "Hyper Text Multiple Language", "Hyper Tool Multi Language", "B"),
            (web_id, "Which CSS property controls the text size?", 
             "font-style", "text-size", "font-size", "spacing", "C"),
            (web_id, "Which HTTP method is typically used to update an existing resource?", 
             "GET", "POST", "PUT", "DELETE", "C")
        ]
        
        # General Trivia Questions
        trivia_questions = [
            (trivia_id, "Which planet is known as the Red Planet?", 
             "Earth", "Mars", "Jupiter", "Saturn", "B"),
            (trivia_id, "What is the capital city of France?", 
             "Berlin", "Madrid", "Paris", "Rome", "C"),
            (trivia_id, "Who wrote the play 'Romeo and Juliet'?", 
             "William Shakespeare", "Charles Dickens", "Leo Tolstoy", "Mark Twain", "A")
        ]
        
        all_questions = se_questions + web_questions + trivia_questions
        cursor.executemany('''
            INSERT INTO questions (category_id, question_text, option_a, option_b, option_c, option_d, correct_option)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', all_questions)
        conn.commit()
        print("Seeded default quiz questions.")

# --- Authentication Operations ---

def register_user(username, password):
    """Registers a new user. Returns user_id if successful, or None if username exists."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        password_hash = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                       (username, password_hash, 'user'))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # Username already exists
        return None
    except sqlite3.Error as e:
        print(f"SQLite registration error: {e}")
        return None
    finally:
        if conn:
            conn.close()

def authenticate_user(username, password):
    """Authenticates user. Returns user row dict if valid, else None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash, role FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user and check_password_hash(user['password_hash'], password):
            return dict(user)
        return None
    except sqlite3.Error as e:
        print(f"SQLite login error: {e}")
        return None
    finally:
        if conn:
            conn.close()

# --- Category & Question Operations ---

def get_categories():
    """Retrieves all categories."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM categories ORDER BY name ASC")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error fetching categories: {e}")
        return []
    finally:
        if conn:
            conn.close()

def add_category(name):
    """Adds a new category. Returns category_id if successful, or None if name exists or fails."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (name.strip(),))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # Category already exists
        return None
    except sqlite3.Error as e:
        print(f"Error adding category: {e}")
        return None
    finally:
        if conn:
            conn.close()

def delete_category(category_id):
    """Deletes a category by ID (cascade will delete associated questions/scores)."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error deleting category: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_questions_by_category(category_id):
    """Retrieves all questions in a category."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, category_id, question_text, option_a, option_b, option_c, option_d, correct_option 
            FROM questions 
            WHERE category_id = ?
        ''', (category_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error fetching questions: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_question_by_id(question_id):
    """Retrieves a single question by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, category_id, question_text, option_a, option_b, option_c, option_d, correct_option 
            FROM questions 
            WHERE id = ?
        ''', (question_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Error fetching question {question_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()

def add_question(category_id, question_text, option_a, option_b, option_c, option_d, correct_option):
    """Adds a new question."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO questions (category_id, question_text, option_a, option_b, option_c, option_d, correct_option)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (category_id, question_text, option_a, option_b, option_c, option_d, correct_option))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error adding question: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_question(question_id, category_id, question_text, option_a, option_b, option_c, option_d, correct_option):
    """Updates an existing question."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE questions 
            SET category_id = ?, question_text = ?, option_a = ?, option_b = ?, option_c = ?, option_d = ?, correct_option = ?
            WHERE id = ?
        ''', (category_id, question_text, option_a, option_b, option_c, option_d, correct_option, question_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error updating question: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_question(question_id):
    """Deletes a question by ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error deleting question: {e}")
        return False
    finally:
        if conn:
            conn.close()

# --- Score and Leaderboard Operations ---

def save_score(user_id, category_id, score, max_score):
    """Saves a user's quiz score."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scores (user_id, category_id, score, max_score)
            VALUES (?, ?, ?, ?)
        ''', (user_id, category_id, score, max_score))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error saving score: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_leaderboard():
    """Retrieves top scores with usernames and category names."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.username, c.name as category_name, s.score, s.max_score, s.timestamp
            FROM scores s
            JOIN users u ON s.user_id = u.id
            JOIN categories c ON s.category_id = c.id
            ORDER BY (CAST(s.score AS REAL) / s.max_score) DESC, s.score DESC, s.timestamp DESC
            LIMIT 10
        ''')
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error retrieving leaderboard: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_user_scores(user_id):
    """Retrieves score history for a specific user."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.name as category_name, s.score, s.max_score, s.timestamp
            FROM scores s
            JOIN categories c ON s.category_id = c.id
            WHERE s.user_id = ?
            ORDER BY s.timestamp DESC
        ''', (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error retrieving user scores: {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- Topic Request Operations ---

def create_topic_request(user_id, title, description):
    """Creates a new topic request if it doesn't already exist for this user."""
    conn = None
    try:
        title_stripped = title.strip()
        desc_stripped = description.strip()
        if not title_stripped or not desc_stripped:
            return None
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Case-insensitive duplicate check for the same user and title
        cursor.execute('''
            SELECT id FROM topic_requests 
            WHERE user_id = ? AND LOWER(title) = LOWER(?)
        ''', (user_id, title_stripped))
        if cursor.fetchone():
            return None # Duplicate exists
            
        cursor.execute('''
            INSERT INTO topic_requests (user_id, title, description, status, votes)
            VALUES (?, ?, ?, 'pending', 1)
        ''', (user_id, title_stripped, desc_stripped))
        request_id = cursor.lastrowid
        
        # Creator automatically registers their vote in topic_votes to prevent upvoting their own topic again
        cursor.execute('''
            INSERT INTO topic_votes (user_id, topic_request_id)
            VALUES (?, ?)
        ''', (user_id, request_id))
        
        conn.commit()
        return request_id
    except sqlite3.Error as e:
        print(f"Error creating topic request: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def get_topic_request_by_id(request_id):
    """Retrieves a single topic request by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tr.id, tr.user_id, tr.title, tr.description, tr.status, tr.votes, tr.admin_note, tr.created_at, u.username
            FROM topic_requests tr
            JOIN users u ON tr.user_id = u.id
            WHERE tr.id = ?
        ''', (request_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Error fetching topic request {request_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_my_topic_requests(user_id):
    """Retrieves all topic requests submitted by a specific user."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, title, description, status, votes, admin_note, created_at
            FROM topic_requests
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error fetching user topic requests: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_all_pending_topic_requests(user_id=None):
    """Retrieves all pending topic requests from all users, sorted by votes desc."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if user_id:
            cursor.execute('''
                SELECT tr.id, tr.user_id, tr.title, tr.description, tr.status, tr.votes, tr.admin_note, tr.created_at, u.username,
                       EXISTS(SELECT 1 FROM topic_votes tv WHERE tv.user_id = ? AND tv.topic_request_id = tr.id) as has_voted
                FROM topic_requests tr
                JOIN users u ON tr.user_id = u.id
                WHERE tr.status = 'pending'
                ORDER BY tr.votes DESC, tr.created_at DESC
            ''', (user_id,))
        else:
            cursor.execute('''
                SELECT tr.id, tr.user_id, tr.title, tr.description, tr.status, tr.votes, tr.admin_note, tr.created_at, u.username,
                       0 as has_voted
                FROM topic_requests tr
                JOIN users u ON tr.user_id = u.id
                WHERE tr.status = 'pending'
                ORDER BY tr.votes DESC, tr.created_at DESC
            ''')
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error fetching pending topic requests: {e}")
        return []
    finally:
        if conn:
            conn.close()

def upvote_topic_request(user_id, request_id):
    """Increments the vote count of a topic request by 1 and registers the voter in topic_votes."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if already voted
        cursor.execute("SELECT 1 FROM topic_votes WHERE user_id = ? AND topic_request_id = ?", (user_id, request_id))
        if cursor.fetchone():
            return False # Duplicate vote check failed
            
        # 1. Insert vote record
        cursor.execute("INSERT INTO topic_votes (user_id, topic_request_id) VALUES (?, ?)", (user_id, request_id))
        
        # 2. Increment vote count
        cursor.execute('''
            UPDATE topic_requests
            SET votes = votes + 1
            WHERE id = ? AND status = 'pending'
        ''', (request_id,))
        
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error upvoting topic request {request_id} for user {user_id}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def approve_topic_request(request_id):
    """Approves a topic request and automatically creates the corresponding category."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Fetch the request to verify and get the title
        cursor.execute("SELECT title, status FROM topic_requests WHERE id = ?", (request_id,))
        request_row = cursor.fetchone()
        if not request_row or request_row['status'] != 'pending':
            return False
            
        category_name = request_row['title']
        
        # 2. Update status of the request
        cursor.execute('''
            UPDATE topic_requests
            SET status = 'approved'
            WHERE id = ?
        ''', (request_id,))
        
        # 3. Create the category. If it already exists, database.add_category handles IntegrityError,
        # but here we can insert directly or ignore if exists.
        cursor.execute('''
            INSERT OR IGNORE INTO categories (name) VALUES (?)
        ''', (category_name,))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error approving topic request {request_id}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def reject_topic_request(request_id, admin_note):
    """Rejects a topic request and records an administrative reason note."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE topic_requests
            SET status = 'rejected', admin_note = ?
            WHERE id = ? AND status = 'pending'
        ''', (admin_note.strip(), request_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error rejecting topic request {request_id}: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # When run directly, initialize database.
    init_db()
    print("Database initialized successfully.")
