# QuizCraft: Software System Documentation & Architecture Reference Manual

---

## 📑 Document Metadata
* **Project Name**: QuizCraft
* **System Type**: Web-based Gamified Learning Management System
* **Implementation Platform**: Python 3 / Flask / SQLite3 / Vanilla JS (ES6)
* **Author Roles**: Software Development Team
* **Status**: Complete & Verified

---

## 1. Executive Summary
QuizCraft is a modern, lightweight, high-performance web application designed to gamify educational assessments. It provides students with an interactive, time-restricted testing console that awards points based on both accuracy and response speed. Additionally, the application integrates a collaborative **Topic Request System** that enables community-driven category suggestions, incorporating a secure, persistent, database-backed upvote system.

---

## 2. System Scope & Requirements Analysis

### 2.1 Functional Requirements
* **FR-01: User Authentication & Role Assignment**: The system must provide secure registration and login portals, assigning either `'user'` (Student) or `'admin'` (Administrator) roles.
* **FR-02: Interactive Assessment Console**: Students must be able to take quizzes in pre-defined categories. Questions are rendered dynamically on the client side without triggering page reloads.
* **FR-03: Dynamic Gamified Scoring**: The system must compute scores dynamically based on correct responses and a time-decaying speed bonus.
* **FR-04: Leaderboard System**: The system must maintain and render a public Top 10 leaderboard sorting highest score ratios and timestamps.
* **FR-05: Collaborative Suggestion Board**: Logged-in users must be able to propose new quiz categories. The community can upvote pending suggestions exactly once per user.
* **FR-06: Suggestion Lifecycle Management**: Administrators must be able to review, approve (which automatically generates a new quiz category), or reject (stating a rejection reason note) community proposals.
* **FR-07: Content Management Console**: Administrators must have access to administrative tools to add, modify, or delete questions and categories.

### 2.2 Non-Functional Requirements
* **NFR-01: Secure State Management**: Authentication status, roles, and correct quiz answer keys must be protected against client-side inspection or manipulation.
* **NFR-02: High Interface Responsiveness**: Client-side screen updates and timer calculations must execute smoothly, rendering within a glassmorphic visual layout.
* **NFR-03: Thread Safety & Query Timeout**: Database operations must manage simultaneous connection calls without causing locking conflicts (utilizing explicit database busy timeouts).
* **NFR-04: Robust Input Validation**: All system input fields must undergo strict sanitization and validation processes on both the client and server.

---

## 3. System Architecture Design

QuizCraft implements an adaptation of the traditional **Model-View-Controller (MVC)** architectural pattern:

```text
               +----------------------------------------+
               |        Presentation Layer (View)       |
               |  - Glassmorphic HTML5 Templates        |
               |  - static/style.css (Design System)    |
               |  - static/quiz.js (Asynchronous DOM)   |
               +-------------------+--------------------+
                                   | HTTP / REST (JSON)
                                   v
               +-------------------+--------------------+
               |         Controller Layer (Flask)       |
               |  - app.py (Routes & Authorization)     |
               |  - quiz_engine.py (Scoring Rules)      |
               +-------------------+--------------------+
                                   | Methods Calls
                                   v
               +-------------------+--------------------+
               |         Data Access Layer (Model)      |
               |  - database.py (SQL Connections)       |
               +-------------------+--------------------+
                                   | SQL Queries
                                   v
               +-------------------+--------------------+
               |             Storage Layer              |
               |  - quiz.db (SQLite3 Relational File)   |
               +----------------------------------------+
```

---

## 4. Relational Database Data Dictionary

The relational database is constructed in **SQLite3** and implements explicit cascading operations (`ON DELETE CASCADE`) to preserve referential integrity.

### 4.1 Table: `users`
Tracks user credentials and administrative access levels.
* **Database Path**: `quiz.db`
* **Schema Definition**:
| Column Name | Data Type | Key Type | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | INTEGER | PK | AUTOINCREMENT | Unique system identifier for each user. |
| `username` | TEXT | - | UNIQUE, NOT NULL | Public username used to authenticate. |
| `password_hash`| TEXT | - | NOT NULL | PBKDF2 hashed password string. |
| `role` | TEXT | - | NOT NULL, DEFAULT 'user' | Access control level (`'user'` or `'admin'`). |

### 4.2 Table: `categories`
Houses the active quiz categories.
* **Schema Definition**:
| Column Name | Data Type | Key Type | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | INTEGER | PK | AUTOINCREMENT | Unique category identifier. |
| `name` | TEXT | - | UNIQUE, NOT NULL | The public name of the category. |

### 4.3 Table: `questions`
Contains the static repository of multiple-choice questions.
* **Schema Definition**:
| Column Name | Data Type | Key Type | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | INTEGER | PK | AUTOINCREMENT | Unique question identifier. |
| `category_id` | INTEGER | FK | REFERENCES categories(id) ON DELETE CASCADE | Associates the question with a category. |
| `question_text`| TEXT | - | NOT NULL | The text prompt of the question. |
| `option_a` | TEXT | - | NOT NULL | Text for Option A. |
| `option_b` | TEXT | - | NOT NULL | Text for Option B. |
| `option_c` | TEXT | - | NOT NULL | Text for Option C. |
| `option_d` | TEXT | - | NOT NULL | Text for Option D. |
| `correct_option`| TEXT | - | NOT NULL | The correct uppercase option letter (`'A'`, `'B'`, `'C'`, `'D'`). |

### 4.4 Table: `scores`
Persistently logs completed student performances.
* **Schema Definition**:
| Column Name | Data Type | Key Type | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | INTEGER | PK | AUTOINCREMENT | Unique score entry identifier. |
| `user_id` | INTEGER | FK | REFERENCES users(id) ON DELETE CASCADE | Identifies the student. |
| `category_id` | INTEGER | FK | REFERENCES categories(id) ON DELETE CASCADE | Identifies the evaluated category. |
| `score` | INTEGER | - | NOT NULL | The total computed points accumulated. |
| `max_score` | INTEGER | - | NOT NULL | The maximum possible points for the quiz. |
| `timestamp` | DATETIME | - | DEFAULT CURRENT_TIMESTAMP | Date and time of quiz completion. |

### 4.5 Table: `topic_requests`
Stores student proposals for new quiz category modules.
* **Schema Definition**:
| Column Name | Data Type | Key Type | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | INTEGER | PK | AUTOINCREMENT | Unique request entry identifier. |
| `user_id` | INTEGER | FK | REFERENCES users(id) ON DELETE CASCADE | Identifies the suggesting user. |
| `title` | TEXT | - | NOT NULL | Proposed title of the category. |
| `description` | TEXT | - | NOT NULL | Description explaining the proposed topic. |
| `status` | TEXT | - | DEFAULT 'pending', NOT NULL | Progress tracking state (`'pending'`, `'approved'`, `'rejected'`). |
| `votes` | INTEGER | - | DEFAULT 1, NOT NULL | Current net upvote tally. |
| `admin_note` | TEXT | - | NULLABLE | Reason note supplied by administrator if rejected. |
| `created_at` | DATETIME | - | DEFAULT CURRENT_TIMESTAMP | Date and time the suggestion was submitted. |

### 4.6 Table: `topic_votes`
Tracks which users have upvoted specific topic requests to prevent duplicates.
* **Schema Definition**:
| Column Name | Data Type | Key Type | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | INTEGER | PK | AUTOINCREMENT | Unique vote record identifier. |
| `user_id` | INTEGER | FK | REFERENCES users(id) ON DELETE CASCADE | The identifier of the voter. |
| `topic_request_id`| INTEGER | FK | REFERENCES topic_requests(id) ON DELETE CASCADE | The targeted topic suggestion entry. |
* **Table Constraint**: `UNIQUE(user_id, topic_request_id)` — *Enforces at the database-level that a user can only vote on a given suggestion once.*

---

## 5. Security Architecture & Threat Mitigation

### 5.1 Vulnerability Case Study: The Cookie-Clearing Double-Vote Exploit
* **Vulnerability Description**: Originally, user upvotes on pending topic suggestions were tracked using a browser cookie list (`session['voted_requests']`). Because HTTP sessions are client-centric and cleared on logout, malicious actors were able to repeatedly upvote suggestions by logging out, logging back in, and pushing votes.
* **The Mitigation**: The application was restructured to use a persistent database-backed join table (`topic_votes`) with a composite unique key constraint (`UNIQUE(user_id, topic_request_id)`). 

```text
  [Student upvotes request]
            |
            v
  Check table 'topic_votes':
  SELECT 1 FROM topic_votes 
  WHERE user_id = ? AND topic_request_id = ?
            |
            +------------> (Record Exists?)
            |                   |
            | Yes               | No
            v                   v
      [Block Upvote]     [Insert Record into topic_votes]
      Flash Error        [Update topic_requests: votes = votes + 1]
                         Flash Success
```

This database structure ensures:
1. **Cookie-Proof Security**: The constraint remains active even if the user clears their browser cache, logs out, or switches devices.
2. **Self-Voting Block**: When a new topic is registered, `create_topic_request()` automatically inserts the creator's ID into `topic_votes`. This blocks the author from upvoting their own proposal later.
3. **Optimized Validation**: When querying pending requests, a virtualized check using the SQL `EXISTS` keyword calculates `has_voted` (1 or 0) dynamically for the authenticated user, avoiding redundant database lookups.

### 5.2 Quiz Answer Exposure Mitigation
To prevent students from accessing correct answers via browser developer consoles or packet analysis, QuizCraft separates the quiz loading and answer validation flows:
* When a quiz begins, `/api/quiz/start` queries questions and strips out the `correct_option` fields before transmitting the JSON payload to the client.
* The correct answers are stored in the secure, signed server-side session cache.
* When an answer is submitted, the selection is sent to `/api/quiz/submit` where validation is executed entirely on the server.

---

## 6. Logic Engine & Scoring Formula

The dynamic scoring rules are implemented in `quiz_engine.py`.

### 6.1 Timer Boundary Helper
The system enforces a 15-second time limit per question:
```python
def is_timer_expired(time_taken: float, max_time: float = 15.0) -> bool:
    try:
        return float(time_taken) > float(max_time)
    except (ValueError, TypeError):
        return True
```

### 6.2 Dynamic Score Formula
If the answer is verified as correct, the points awarded are computed dynamically to reward speed:
$$\text{Awarded Points} = \text{Base Score} + \text{Speed Bonus}$$
$$\text{Speed Bonus} = \text{floor} \left( \text{Max Bonus} \times \frac{\text{Max Time} - \text{Time Taken}}{\text{Max Time}} \right)$$

* **Base Score**: 10 points
* **Max Speed Bonus**: 10 points
* **Max Time**: 15.0 seconds
* **Time Taken**: Evaluated on the server by comparing the transaction timestamp against the start timestamp.

```python
def calculate_score(is_correct: bool, time_taken: float, max_time: float = 15.0) -> int:
    if not is_correct or time_taken < 0 or is_timer_expired(time_taken, max_time):
        return 0
    time_remaining = max(0.0, max_time - time_taken)
    ratio_remaining = time_remaining / max_time
    speed_bonus = int(10 * ratio_remaining)
    return 10 + speed_bonus
```

---

## 7. Interactive Interface & Styling System

The application is styled with a custom, high-fidelity **glassmorphic design system** that adapts seamlessly to desktop and mobile environments.

### 7.1 Visual Color Variables
* **Dark Backdrop**: `#09090b` (Deep obsidian black background)
* **Indigo Accent (Primary)**: `#6366f1` (Vibrant purple-blue buttons and focus rings)
* **Pink Secondary (Interactive)**: `#ec4899` (Secondary CTAs and progress tracks)
* **Cyan Highlight (Accent)**: `#06b6d4` (Scores, points, and highlighting metrics)
* **Emerald Success**: `#10b981` (Approved badges, correct answer indicators)
* **Crimson Danger**: `#ef4444` (Rejected badges, incorrect answer indicators)
* **Glass Card Backdrop**: `rgba(24, 24, 27, 0.6)` with a custom blur filter: `backdrop-filter: blur(16px)`

---

## 8. Test Suite & Validation Records

QuizCraft includes automated unit tests inside `tests/test_quiz.py` that isolate logic and database queries using a separate test database (`test_quiz.db`).

### 8.1 Evaluated Verification Scenarios
* **Answer Cleansing Validation**: Tests that whitespace modifications and case variations in inputs are sanitized and evaluated correctly.
* **Scoring Constraints Verification**: Verifies score outputs across multiple parameters (instant answer, mid-timer answers, maximum timeout answers, and negative inputs).
* **Timer Bounds Check**: Verifies that answers sent after the 15.0-second limit are rejected and score 0 points.
* **Suggestion Duplicate Prevention**: Asserts that duplicate topic proposals with the same title from the same user are rejected.
* **Upvote Constraint Enforcement**: Verifies that upvoting increments scores, blocks duplicates, and validates the persistent `has_voted` flags.

---

## 9. Installation & Deployment Instructions

### 9.1 Local Setup
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/uzairnisar322-ux/SCD-FINAL-PROJECT.git
   cd SCD-FINAL-PROJECT
   ```
2. **Install Dependencies**: Ensure Python 3.8+ is installed. Flask and its security tools are standard:
   ```bash
   pip install Flask Werkzeug
   ```
3. **Execute Core Unit Tests**: Run the automated test runner:
   ```bash
   python run_tests.py
   ```
4. **Launch the Server**:
   ```bash
   python app.py
   ```
5. **Access in Web Browser**: Open **[http://localhost:8080](http://localhost:8080)**.

### 9.2 Seed Credentials
* **Student Access**: Username: `user` | Password: `user123`
* **Administrator Access**: Username: `admin` | Password: `admin123`
