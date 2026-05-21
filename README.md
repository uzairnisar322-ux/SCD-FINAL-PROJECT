# QuizCraft - Software Engineering Quiz Application

QuizCraft is a complete, interactive quiz application built as a Software Engineering course final project. It utilizes a Python Flask and SQLite stack for the backend, combined with a sleek, neon-violet glassmorphic frontend interface.

## Project Structure
- [app.py](file:///d:/4RD%20SEMESTER/final%20project/app.py): Core Flask application containing views, APIs, and security configurations.
- [database.py](file:///d:/4RD%20SEMESTER/final%20project/database.py): SQLite database schema setup, user registry, and CRUD scripts.
- [quiz_engine.py](file:///d:/4RD%20SEMESTER/final%20project/quiz_engine.py): Isolated and refactored core logical systems (scoring algorithms, countdown boundaries, and answer filters).
- [run_tests.py](file:///d:/4RD%20SEMESTER/final%20project/run_tests.py): Automated test runner triggering unittest modules.
- `tests/`: Automated unit tests covering edge cases.
- `templates/`: Jinja2 templates (dashboard, quiz layout, login gates, leaderboards, admin CRUD controls).
- `static/`: Frontend visual assets (glassmorphic style system and AJAX controllers).
- [docs/SE_REPORT.md](file:///d:/4RD%20SEMESTER/final%20project/docs/SE_REPORT.md): Comprehensive Software Engineering course report covering sprints, version control branch structures, Lehman's laws, and peer reviews.

## Getting Started

### 1. Installation
Install the required packages using pip:
```bash
pip install flask
```

### 2. Database Seeding
Initialize the tables and seed mock questions and accounts:
```bash
python database.py
```

### 3. Run Application
Run the Flask server:
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000/`.

### 4. Running Unit Tests
Execute the test runner script to run the automated checks:
```bash
python run_tests.py
```
---
Crafted for Software Engineering Process Standards, 2026.
