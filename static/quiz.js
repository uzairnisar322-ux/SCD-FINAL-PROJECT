/**
 * quiz.js
 * Manages the interactive client-side quiz session, AJAX API requests,
 * dynamic progress bar updates, ticking countdown timer, and correct/incorrect answer styling.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Select page DOM elements
    const quizArea = document.getElementById('quiz-area');
    const categoryId = quizArea ? quizArea.dataset.categoryId : null;
    
    if (!categoryId) return; // Not on the quiz page

    let currentQuestion = null;
    let timerInterval = null;
    let timeRemaining = 15.0;
    const maxTime = 15.0;
    let totalQuestionsCount = 0;
    let currentQuestionIndex = 0;
    
    // Start the Quiz Session via API
    startQuiz(categoryId);

    async function startQuiz(catId) {
        try {
            const response = await fetch('/api/quiz/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ category_id: parseInt(catId) })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Failed to start quiz.');
            }

            const data = await response.json();
            totalQuestionsCount = data.total_questions;
            currentQuestionIndex = 0;
            
            // Load the first question
            loadQuestion(data.first_question);
        } catch (error) {
            console.error('Quiz initialization error:', error);
            renderErrorState(error.message);
        }
    }

    function loadQuestion(question) {
        currentQuestion = question;
        currentQuestionIndex++;
        
        // Reset timer
        timeRemaining = maxTime;
        updateTimerDisplay();
        startTimer();

        // Update progress bar
        const progressPercent = ((currentQuestionIndex - 1) / totalQuestionsCount) * 100;
        document.getElementById('progress-bar').style.width = `${progressPercent}%`;
        document.getElementById('question-num').textContent = currentQuestionIndex;
        document.getElementById('total-questions').textContent = totalQuestionsCount;

        // Render question options
        renderQuestionCard(question);
    }

    function renderQuestionCard(q) {
        // Clear previous question and add transition classes
        quizArea.innerHTML = `
            <div class="question-container animate-fade-in">
                <div class="question-text" id="q-text"></div>
                <div class="options-grid" id="options-container"></div>
            </div>
        `;
        
        // Use textContent defensively to prevent XSS
        document.getElementById('q-text').textContent = q.question_text;
        
        const optionsContainer = document.getElementById('options-container');
        const options = [
            { key: 'A', text: q.option_a },
            { key: 'B', text: q.option_b },
            { key: 'C', text: q.option_c },
            { key: 'D', text: q.option_d }
        ];

        options.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'option-button';
            btn.dataset.option = opt.key;
            btn.innerHTML = `
                <span class="option-letter">${opt.key}</span>
                <span class="option-text"></span>
            `;
            // Safe assignment
            btn.querySelector('.option-text').textContent = opt.text;
            
            // Click listener
            btn.addEventListener('click', () => submitAnswer(opt.key));
            optionsContainer.appendChild(btn);
        });
    }

    function startTimer() {
        clearInterval(timerInterval);
        
        const timerBox = document.getElementById('timer-box');
        timerBox.classList.remove('urgent');

        timerInterval = setInterval(() => {
            timeRemaining -= 0.1;
            if (timeRemaining <= 0) {
                timeRemaining = 0;
                clearInterval(timerInterval);
                // Time's up! Auto-submit
                submitAnswer(null);
            }
            
            // Urgent timing warnings (less than 5 seconds left)
            if (timeRemaining <= 5.0) {
                timerBox.classList.add('urgent');
            }
            
            updateTimerDisplay();
        }, 100);
    }

    function updateTimerDisplay() {
        const timerText = document.getElementById('timer-text');
        if (timerText) {
            timerText.textContent = timeRemaining.toFixed(1) + 's';
        }
    }

    async function submitAnswer(selectedOption) {
        // Stop timer immediately
        clearInterval(timerInterval);
        
        // Disable all option buttons to prevent multiple clicks
        const buttons = document.querySelectorAll('.option-button');
        buttons.forEach(btn => btn.disabled = true);

        try {
            const response = await fetch('/api/quiz/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question_id: currentQuestion.id,
                    answer: selectedOption
                })
            });

            if (!response.ok) {
                throw new Error('Failed to submit answer.');
            }

            const result = await response.json();
            
            // Highlight answers based on response
            buttons.forEach(btn => {
                const optKey = btn.dataset.option;
                if (optKey === result.correct_option) {
                    btn.classList.add('correct');
                } else if (optKey === selectedOption && !result.correct) {
                    btn.classList.add('incorrect');
                }
            });

            // Delay transitioning to next state to let user see feedback
            setTimeout(() => {
                if (result.completed) {
                    // Update progress bar to full on completion
                    document.getElementById('progress-bar').style.width = '100%';
                    renderResults(result.final_score, result.max_score);
                } else {
                    loadQuestion(result.next_question);
                }
            }, 1500);

        } catch (error) {
            console.error('Answer submission error:', error);
            renderErrorState('An error occurred while submitting your answer. Reconnecting...');
        }
    }

    function renderResults(score, maxScore) {
        clearInterval(timerInterval);
        
        // Hide the header progression area
        const header = document.querySelector('.quiz-header');
        if (header) header.style.display = 'none';
        
        const progressContainer = document.querySelector('.progress-container');
        if (progressContainer) progressContainer.style.display = 'none';

        // Calculate performance rating
        const percentage = (score / maxScore) * 100;
        let rating = "Good Job!";
        let icon = "🏆";
        if (percentage >= 85) {
            rating = "Exceptional performance! You are an expert!";
            icon = "🧙‍♂️✨";
        } else if (percentage >= 50) {
            rating = "Nice work! You passed.";
            icon = "🎯";
        } else {
            rating = "Keep practicing! Try again to boost your score.";
            icon = "📚";
        }

        quizArea.innerHTML = `
            <div class="result-card animate-fade-in">
                <div class="category-icon" style="font-size: 4rem;">${icon}</div>
                <h2>Quiz Completed!</h2>
                <p>Check out your score below:</p>
                <div class="result-score">${score} <span style="font-size: 1.5rem; color: var(--text-muted);">/ ${maxScore} pts</span></div>
                <div class="result-feedback">${rating}</div>
                <div style="display: flex; gap: 1rem; justify-content: center;">
                    <a href="/dashboard" class="btn btn-secondary">Dashboard</a>
                    <a href="/quiz/${categoryId}" class="btn btn-primary">Try Again</a>
                </div>
            </div>
        `;
    }

    function renderErrorState(message) {
        quizArea.innerHTML = `
            <div class="glass-card text-center" style="border-color: var(--danger);">
                <div class="category-icon" style="font-size: 3rem; color: var(--danger); text-shadow: 0 0 10px rgba(239,68,68,0.5);">⚠️</div>
                <h3 style="color: var(--danger);">Connection Error</h3>
                <p>${message}</p>
                <a href="/dashboard" class="btn btn-primary btn-sm">Return to Dashboard</a>
            </div>
        `;
    }
});
