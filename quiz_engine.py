"""
quiz_engine.py
Contains core logical operations for the Quiz App: score calculation, answer validation, and timer checks.
This represents the refactored version of the scoring and validation system.
"""

# Configurable constants to avoid magic numbers
DEFAULT_BASE_SCORE = 10
DEFAULT_SPEED_BONUS_MAX = 10
TIME_LIMIT_PER_QUESTION = 15.0  # seconds

def validate_answer(submitted_option: str, correct_option: str) -> bool:
    """
    Validates if the user's submitted choice matches the correct option.
    
    Includes input cleansing (trimming spaces, case normalization) and defensive checks.
    """
    if not submitted_option or not correct_option:
        return False
        
    clean_submitted = str(submitted_option).strip().upper()
    clean_correct = str(correct_option).strip().upper()
    
    # Validation constraints: Must be single letters A, B, C, or D
    valid_options = {'A', 'B', 'C', 'D'}
    if clean_submitted not in valid_options or clean_correct not in valid_options:
        return False
        
    return clean_submitted == clean_correct

def calculate_score(is_correct: bool, time_taken: float, max_time: float = TIME_LIMIT_PER_QUESTION) -> int:
    """
    Calculates the score awarded for a question.
    
    Rules:
    - If incorrect, score is 0.
    - If correct, base score is awarded.
    - If correct and answered fast, a speed bonus is added:
      bonus = max_bonus * (time_remaining / max_time)
    - If time taken exceeds maximum time, score is 0.
    """
    # Guard clause for invalid inputs
    if not is_correct or time_taken < 0:
        return 0
        
    # Check if timer expired
    if is_timer_expired(time_taken, max_time):
        return 0
        
    # Calculate bonus score proportional to remaining time
    time_remaining = max(0.0, max_time - time_taken)
    ratio_remaining = time_remaining / max_time
    speed_bonus = int(DEFAULT_SPEED_BONUS_MAX * ratio_remaining)
    
    return DEFAULT_BASE_SCORE + speed_bonus

def is_timer_expired(time_taken: float, max_time: float = TIME_LIMIT_PER_QUESTION) -> bool:
    """
    Determines if the response exceeded the allowable time limit.
    """
    try:
        # Cast inputs defensively to floats
        t_taken = float(time_taken)
        t_max = float(max_time)
    except (ValueError, TypeError):
        # Defensively treat malformed parameters as expired
        return True
        
    return t_taken > t_max
