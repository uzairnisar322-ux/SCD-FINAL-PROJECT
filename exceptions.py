"""
exceptions.py
Centralized custom exception classes and error handlers for the QuizCraft application.
"""
from flask import render_template, jsonify, flash, redirect, url_for

class QuizCraftError(Exception):
    """Base exception class for all QuizCraft application errors."""
    def __init__(self, message="An internal application error occurred", status_code=500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class DatabaseConnectionError(QuizCraftError):
    """Raised when database connection fails or gets locked."""
    def __init__(self, message="Database connection error"):
        super().__init__(message, status_code=500)

class DuplicateUserError(QuizCraftError):
    """Raised during registration if the username is already taken."""
    def __init__(self, message="Username is already taken"):
        super().__init__(message, status_code=400)

class InvalidCredentialsError(QuizCraftError):
    """Raised during login for incorrect credentials."""
    def __init__(self, message="Invalid username or password"):
        super().__init__(message, status_code=401)

class QuizSessionError(QuizCraftError):
    """Base exception for active quiz session failures."""
    def __init__(self, message="Invalid quiz session context", status_code=400):
        super().__init__(message, status_code)

class QuizTimerExpiredError(QuizSessionError):
    """Raised when answer submission exceeds timer boundaries."""
    def __init__(self, message="Time limit expired for this question"):
        super().__init__(message, status_code=400)

class DuplicateVoteError(QuizCraftError):
    """Raised when a user attempts to upvote a topic request multiple times."""
    def __init__(self, message="You have already upvoted this topic suggestion"):
        super().__init__(message, status_code=400)

class DuplicateTopicRequestError(QuizCraftError):
    """Raised when a user suggests a category that they have already requested."""
    def __init__(self, message="You have already submitted a topic request with this title"):
        super().__init__(message, status_code=400)

def register_error_handlers(app):
    """Registers global exception handlers on the Flask app context."""
    
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f"404 Error: Page not found at {error}")
        if '/api/' in request_path_helper():
            return jsonify({'error': 'Resource not found'}), 404
        return render_template('base.html', error_title="404 - Page Not Found", 
                               error_message="The page you are looking for does not exist or has been moved."), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"500 Internal Error: {error}")
        if '/api/' in request_path_helper():
            return jsonify({'error': 'An internal server error occurred'}), 500
        return render_template('base.html', error_title="500 - Server Error", 
                               error_message="Something went wrong on our servers. Please try again later."), 500

    @app.errorhandler(QuizCraftError)
    def handle_quizcraft_error(error):
        app.logger.error(f"QuizCraft Error: {error.message} (Code: {error.status_code})")
        if '/api/' in request_path_helper():
            return jsonify({'error': error.message}), error.status_code
        flash(error.message, "error")
        return redirect(url_for('dashboard'))

def request_path_helper():
    """Safe import helper for Flask request context to avoid circular imports."""
    from flask import request
    try:
        return request.path
    except RuntimeError:
        return ''
