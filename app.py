from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import os
import time
import database
import quiz_engine

app = Flask(__name__)
# Secure secret key for sessions
app.secret_key = os.urandom(24)

# Ensure database is initialized before serving requests
with app.app_context():
    database.init_db()

# Decorator to restrict access to logged-in users
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to restrict access to admins only
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "error")
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash("Access denied. Admin privileges required.", "error")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Exception handling for user input registration
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            if not username or not password:
                flash("Username and password are required.", "error")
                return render_template('login.html', active_tab='register')
                
            if len(password) < 6:
                flash("Password must be at least 6 characters long.", "error")
                return render_template('login.html', active_tab='register')
                
            user_id = database.register_user(username, password)
            if user_id:
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for('login'))
            else:
                flash("Username already taken. Please choose another.", "error")
        except Exception as e:
            app.logger.error(f"Error during registration: {e}")
            flash("An unexpected error occurred during registration. Please try again.", "error")
            
    return render_template('login.html', active_tab='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Exception handling for login details
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            if not username or not password:
                flash("Please enter both username and password.", "error")
                return render_template('login.html', active_tab='login')
                
            user = database.authenticate_user(username, password)
            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                flash(f"Welcome back, {user['username']}!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid username or password.", "error")
        except Exception as e:
            app.logger.error(f"Error during login: {e}")
            flash("An unexpected error occurred. Please try again.", "error")
            
    return render_template('login.html', active_tab='login')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        categories = database.get_categories()
        user_scores = database.get_user_scores(session['user_id'])
        return render_template('dashboard.html', categories=categories, user_scores=user_scores)
    except Exception as e:
        app.logger.error(f"Dashboard load error: {e}")
        flash("Could not load categories or score history. Please try again.", "error")
        return render_template('dashboard.html', categories=[], user_scores=[])

@app.route('/leaderboard')
@login_required
def leaderboard():
    try:
        leaderboard_data = database.get_leaderboard()
        return render_template('leaderboard.html', leaderboard=leaderboard_data)
    except Exception as e:
        app.logger.error(f"Leaderboard load error: {e}")
        flash("Could not retrieve leaderboard data.", "error")
        return render_template('leaderboard.html', leaderboard=[])

# --- Quiz Interactive Flow Routes ---

@app.route('/quiz/<int:category_id>')
@login_required
def quiz_view(category_id):
    try:
        categories = database.get_categories()
        category_name = "Quiz"
        for cat in categories:
            if cat['id'] == category_id:
                category_name = cat['name']
                break
        return render_template('quiz.html', category_id=category_id, category_name=category_name)
    except Exception as e:
        app.logger.error(f"Quiz view failed: {e}")
        flash("Failed to start the quiz. Try again.", "error")
        return redirect(url_for('dashboard'))

# API endpoint: Start quiz session
@app.route('/api/quiz/start', methods=['POST'])
@login_required
def api_start_quiz():
    try:
        data = request.get_json() or {}
        category_id = int(data.get('category_id', 0))
        
        questions = database.get_questions_by_category(category_id)
        if not questions:
            return jsonify({'error': 'No questions available for this category.'}), 404
            
        # Structure question objects securely (do NOT send correct options to client)
        secure_questions = []
        for q in questions:
            secure_questions.append({
                'id': q['id'],
                'question_text': q['question_text'],
                'option_a': q['option_a'],
                'option_b': q['option_b'],
                'option_c': q['option_c'],
                'option_d': q['option_d']
            })
            
        # Store state in session
        session['quiz_state'] = {
            'category_id': category_id,
            'questions': secure_questions,
            'correct_answers': {str(q['id']): q['correct_option'] for q in questions},
            'current_index': 0,
            'cumulative_score': 0,
            'max_score': len(questions) * (quiz_engine.DEFAULT_BASE_SCORE + quiz_engine.DEFAULT_SPEED_BONUS_MAX),
            'start_timestamp': time.time()
        }
        
        return jsonify({
            'total_questions': len(secure_questions),
            'first_question': secure_questions[0],
            'time_limit': quiz_engine.TIME_LIMIT_PER_QUESTION
        })
    except Exception as e:
        app.logger.error(f"API Start Quiz Error: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500

# API endpoint: Submit question answer
@app.route('/api/quiz/submit', methods=['POST'])
@login_required
def api_submit_answer():
    try:
        data = request.get_json() or {}
        question_id = str(data.get('question_id'))
        submitted_option = data.get('answer') # 'A', 'B', 'C', or 'D'
        
        quiz_state = session.get('quiz_state')
        if not quiz_state:
            return jsonify({'error': 'No active quiz session found.'}), 400
            
        # Verify server timing to prevent client-side cheat injections
        current_time = time.time()
        time_elapsed = current_time - quiz_state['start_timestamp']
        
        correct_answers = quiz_state['correct_answers']
        correct_option = correct_answers.get(question_id)
        if not correct_option:
            return jsonify({'error': 'Invalid question ID.'}), 400
            
        # Validate using refactored quiz engine
        is_correct = quiz_engine.validate_answer(submitted_option, correct_option)
        
        # Calculate score using refactored engine
        score_awarded = quiz_engine.calculate_score(is_correct, time_elapsed)
        
        # Update state
        quiz_state['cumulative_score'] += score_awarded
        quiz_state['current_index'] += 1
        
        # Check if quiz completed
        completed = quiz_state['current_index'] >= len(quiz_state['questions'])
        
        if completed:
            # Save score to database
            database.save_score(
                user_id=session['user_id'],
                category_id=quiz_state['category_id'],
                score=quiz_state['cumulative_score'],
                max_score=quiz_state['max_score']
            )
            # Remove state
            session.pop('quiz_state', None)
            
            return jsonify({
                'correct': is_correct,
                'correct_option': correct_option,
                'score_awarded': score_awarded,
                'completed': True,
                'final_score': quiz_state['cumulative_score'],
                'max_score': quiz_state['max_score']
            })
        else:
            # Prepare next question
            next_index = quiz_state['current_index']
            next_question = quiz_state['questions'][next_index]
            quiz_state['start_timestamp'] = time.time() # Reset timestamp for next question
            session['quiz_state'] = quiz_state # save updated session state
            
            return jsonify({
                'correct': is_correct,
                'correct_option': correct_option,
                'score_awarded': score_awarded,
                'completed': False,
                'next_question': next_question
            })
            
    except Exception as e:
        app.logger.error(f"API Submit Answer Error: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500

# --- Admin Routes ---

@app.route('/admin')
@admin_required
def admin_panel():
    conn = None
    try:
        categories = database.get_categories()
        # Collect questions with category names for displays
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT q.id, q.question_text, q.option_a, q.option_b, q.option_c, q.option_d, q.correct_option, c.name as category_name, q.category_id
            FROM questions q
            JOIN categories c ON q.category_id = c.id
            ORDER BY c.name, q.id
        ''')
        questions = [dict(row) for row in cursor.fetchall()]
        return render_template('admin.html', categories=categories, questions=questions)
    except Exception as e:
        app.logger.error(f"Admin panel load failed: {e}")
        flash("Could not load admin resources.", "error")
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

@app.route('/admin/question/add', methods=['POST'])
@admin_required
def admin_add_question():
    try:
        category_id = int(request.form.get('category_id', 0))
        question_text = request.form.get('question_text', '').strip()
        option_a = request.form.get('option_a', '').strip()
        option_b = request.form.get('option_b', '').strip()
        option_c = request.form.get('option_c', '').strip()
        option_d = request.form.get('option_d', '').strip()
        correct_option = request.form.get('correct_option', '').strip().upper()
        
        if not (category_id and question_text and option_a and option_b and option_c and option_d and correct_option):
            flash("All question fields are required.", "error")
            return redirect(url_for('admin_panel'))
            
        new_id = database.add_question(category_id, question_text, option_a, option_b, option_c, option_d, correct_option)
        if new_id:
            flash("Question added successfully!", "success")
        else:
            flash("Database error: Could not add question.", "error")
    except Exception as e:
        app.logger.error(f"Admin add question failed: {e}")
        flash("An error occurred while creating question.", "error")
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/question/edit/<int:question_id>', methods=['POST'])
@admin_required
def admin_edit_question(question_id):
    try:
        category_id = int(request.form.get('category_id', 0))
        question_text = request.form.get('question_text', '').strip()
        option_a = request.form.get('option_a', '').strip()
        option_b = request.form.get('option_b', '').strip()
        option_c = request.form.get('option_c', '').strip()
        option_d = request.form.get('option_d', '').strip()
        correct_option = request.form.get('correct_option', '').strip().upper()
        
        if not (category_id and question_text and option_a and option_b and option_c and option_d and correct_option):
            flash("All fields are required.", "error")
            return redirect(url_for('admin_panel'))
            
        success = database.update_question(question_id, category_id, question_text, option_a, option_b, option_c, option_d, correct_option)
        if success:
            flash("Question updated successfully!", "success")
        else:
            flash("Could not update question. Verify question ID exists.", "error")
    except Exception as e:
        app.logger.error(f"Admin edit question failed: {e}")
        flash("An error occurred while updating question.", "error")
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/question/delete/<int:question_id>', methods=['POST'])
@admin_required
def admin_delete_question(question_id):
    try:
        success = database.delete_question(question_id)
        if success:
            flash("Question deleted successfully.", "success")
        else:
            flash("Could not delete question.", "error")
    except Exception as e:
        app.logger.error(f"Admin delete question failed: {e}")
        flash("An error occurred while deleting question.", "error")
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/category/add', methods=['POST'])
@admin_required
def admin_add_category():
    try:
        category_name = request.form.get('category_name', '').strip()
        if not category_name:
            flash("Category name cannot be empty.", "error")
            return redirect(url_for('admin_panel'))
            
        new_id = database.add_category(category_name)
        if new_id:
            flash(f"Category '{category_name}' added successfully!", "success")
        else:
            flash("Category already exists or database error occurred.", "error")
    except Exception as e:
        app.logger.error(f"Admin add category failed: {e}")
        flash("An error occurred while creating category.", "error")
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/category/delete/<int:category_id>', methods=['POST'])
@admin_required
def admin_delete_category(category_id):
    try:
        success = database.delete_category(category_id)
        if success:
            flash("Category and all its questions deleted successfully.", "success")
        else:
            flash("Could not delete category.", "error")
    except Exception as e:
        app.logger.error(f"Admin delete category failed: {e}")
        flash("An error occurred while deleting category.", "error")
        
    return redirect(url_for('admin_panel'))

# --- Topic Request Routes ---

@app.route('/request-topic', methods=['GET', 'POST'])
@login_required
def request_topic():
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            
            if not title or not description:
                flash("Both topic title and description are required.", "error")
                return render_template('request_topic.html')
                
            # Submit to database
            request_id = database.create_topic_request(session['user_id'], title, description)
            if request_id:
                flash(f"Topic request '{title}' submitted successfully!", "success")
                return redirect(url_for('my_requests'))
            else:
                flash("You have already submitted a topic request with this title.", "error")
                return render_template('request_topic.html')
        except Exception as e:
            app.logger.error(f"Error submitting topic request: {e}")
            flash("An unexpected error occurred. Please try again.", "error")
            
    return render_template('request_topic.html')

@app.route('/my-requests')
@login_required
def my_requests():
    try:
        user_requests = database.get_my_topic_requests(session['user_id'])
        pending_requests = database.get_all_pending_topic_requests(session['user_id'])
        return render_template('my_requests.html', 
                               user_requests=user_requests, 
                               pending_requests=pending_requests)
    except Exception as e:
        app.logger.error(f"Error fetching topic requests: {e}")
        flash("Could not retrieve topic requests. Please try again.", "error")
        return render_template('my_requests.html', user_requests=[], pending_requests=[])

@app.route('/vote-request/<int:request_id>', methods=['POST'])
@login_required
def vote_topic_request(request_id):
    try:
        success = database.upvote_topic_request(session['user_id'], request_id)
        if success:
            flash("Vote registered successfully!", "success")
        else:
            flash("You have already upvoted this topic request, or it is no longer active.", "error")
    except Exception as e:
        app.logger.error(f"Error upvoting request {request_id}: {e}")
        flash("An error occurred while upvoting.", "error")
        
    return redirect(url_for('my_requests'))

@app.route('/admin/requests')
@admin_required
def admin_requests():
    try:
        pending_requests = database.get_all_pending_topic_requests()
        return render_template('admin_requests.html', pending_requests=pending_requests)
    except Exception as e:
        app.logger.error(f"Error loading admin requests: {e}")
        flash("Could not load pending requests.", "error")
        return redirect(url_for('admin_panel'))

@app.route('/admin/requests/<int:request_id>/approve', methods=['POST'])
@admin_required
def admin_approve_request(request_id):
    try:
        success = database.approve_topic_request(request_id)
        if success:
            flash("Topic request approved and new category created successfully!", "success")
        else:
            flash("Failed to approve topic request. Verify it is still pending.", "error")
    except Exception as e:
        app.logger.error(f"Error approving request {request_id}: {e}")
        flash("An error occurred during request approval.", "error")
        
    return redirect(url_for('admin_requests'))

@app.route('/admin/requests/<int:request_id>/reject', methods=['POST'])
@admin_required
def admin_reject_request(request_id):
    try:
        admin_note = request.form.get('admin_note', '').strip()
        if not admin_note:
            flash("Rejection reason note cannot be empty.", "error")
            return redirect(url_for('admin_requests'))
            
        success = database.reject_topic_request(request_id, admin_note)
        if success:
            flash("Topic request rejected with note.", "success")
        else:
            flash("Failed to reject topic request.", "error")
    except Exception as e:
        app.logger.error(f"Error rejecting request {request_id}: {e}")
        flash("An error occurred during request rejection.", "error")
        
    return redirect(url_for('admin_requests'))

if __name__ == '__main__':
    # Running locally on port 8080
    print("=" * 50)
    print("QuizCraft Server Starting...")
    print("Open this link in your browser:")
    print("  http://localhost:8080")
    print("=" * 50)
    app.run(debug=False, host='0.0.0.0', port=8080)
