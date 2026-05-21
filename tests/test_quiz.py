import sys
import os
import unittest

# Ensure project root is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
from quiz_engine import validate_answer, calculate_score, is_timer_expired

class TestQuizEngine(unittest.TestCase):

    # =====================================================================
    # 1. Answer Validation Tests
    # =====================================================================

    def test_validate_answer_exact_match(self):
        self.assertTrue(validate_answer("A", "A"))
        self.assertTrue(validate_answer("B", "B"))

    def test_validate_answer_case_insensitive(self):
        self.assertTrue(validate_answer("a", "A"))
        self.assertTrue(validate_answer("b", "B"))
        self.assertTrue(validate_answer("C", "c"))

    def test_validate_answer_whitespace(self):
        self.assertTrue(validate_answer("  A  ", "A"))
        self.assertTrue(validate_answer("B", "  b  "))

    def test_validate_answer_invalid_options(self):
        self.assertFalse(validate_answer("E", "E"))  # not A, B, C, D
        self.assertFalse(validate_answer("A", "X"))
        self.assertFalse(validate_answer("", "A"))
        self.assertFalse(validate_answer("A", None))

    # =====================================================================
    # 2. Score Calculation Tests
    # =====================================================================

    def test_calculate_score_incorrect(self):
        # Incorrect answers always get 0
        self.assertEqual(calculate_score(is_correct=False, time_taken=2.0), 0)

    def test_calculate_score_maximum_speed_bonus(self):
        # Answered instantly (0 seconds) should give maximum speed bonus (10) + base (10) = 20
        self.assertEqual(calculate_score(is_correct=True, time_taken=0.0), 20)

    def test_calculate_score_half_speed_bonus(self):
        # Answered at half-time limit (7.5 seconds of 15 seconds)
        # bonus = 10 * (7.5 / 15) = 5. Total = 10 (base) + 5 = 15
        self.assertEqual(calculate_score(is_correct=True, time_taken=7.5), 15)

    def test_calculate_score_no_speed_bonus(self):
        # Answered at exactly the limit (15.0 seconds)
        # bonus = 10 * (0 / 15) = 0. Total = 10 (base)
        self.assertEqual(calculate_score(is_correct=True, time_taken=15.0), 10)

    def test_calculate_score_timeout(self):
        # Answered after limit (16.0 seconds) -> score = 0
        self.assertEqual(calculate_score(is_correct=True, time_taken=16.0), 0)

    def test_calculate_score_negative_time(self):
        # Negative time is invalid, score should be 0
        self.assertEqual(calculate_score(is_correct=True, time_taken=-2.0), 0)

    # =====================================================================
    # 3. Timer Expiration Tests
    # =====================================================================

    def test_timer_not_expired(self):
        self.assertFalse(is_timer_expired(time_taken=10.0, max_time=15.0))

    def test_timer_exactly_limit(self):
        # Boundary condition
        self.assertFalse(is_timer_expired(time_taken=15.0, max_time=15.0))

    def test_timer_expired(self):
        self.assertTrue(is_timer_expired(time_taken=15.1, max_time=15.0))

    def test_timer_invalid_inputs(self):
        # Defensively handles string inputs or invalid parameters
        self.assertTrue(is_timer_expired("not-a-number", 15.0))
        self.assertTrue(is_timer_expired(10.0, "not-a-number"))
        self.assertTrue(is_timer_expired(None, 15.0))

# =====================================================================
# 4. Topic Request System Tests
# =====================================================================

TEST_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test_quiz.db')

class TestTopicRequestSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Swap database path to a test database
        cls.original_db_path = database.DATABASE_PATH
        database.DATABASE_PATH = TEST_DB_PATH
        # Force re-initialization of test database
        database.init_db()
        
        # Create a test user
        cls.user_id = database.register_user("test_requester", "password123")
        cls.admin_id = database.register_user("test_admin", "password123")
        # Change role of test_admin to admin
        conn = database.get_db_connection()
        try:
            conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (cls.admin_id,))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def tearDownClass(cls):
        # Restore original database path
        database.DATABASE_PATH = cls.original_db_path
        # Clean up test database file
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception as e:
                print(f"Error removing test database file: {e}")

    def test_topic_request_creation_and_duplicate_prevention(self):
        # Test creating a valid request
        req_id = database.create_topic_request(self.user_id, "Python Decorators", "Learn about decorators in Python")
        self.assertIsNotNone(req_id)
        
        # Verify it was inserted with votes=1, status=pending
        req = database.get_topic_request_by_id(req_id)
        self.assertIsNotNone(req)
        self.assertEqual(req['title'], "Python Decorators")
        self.assertEqual(req['status'], "pending")
        self.assertEqual(req['votes'], 1)
        self.assertEqual(req['username'], "test_requester")
        
        # Test duplicate prevention (same user, same title)
        dup_id = database.create_topic_request(self.user_id, "Python Decorators", "Another description")
        self.assertIsNone(dup_id)
        
        # Test case-insensitivity on duplicate check
        dup_case_id = database.create_topic_request(self.user_id, "python decorators", "Yet another description")
        self.assertIsNone(dup_case_id)

    def test_topic_request_vote_increment(self):
        # Create a request by self.user_id (this automatically inserts their vote in topic_votes and sets votes to 1)
        req_id = database.create_topic_request(self.user_id, "Machine Learning Basics", "Intro to neural networks")
        self.assertIsNotNone(req_id)
        
        # Verify the creator cannot upvote their own request again (returns False due to UNIQUE constraint)
        self.assertFalse(database.upvote_topic_request(self.user_id, req_id))
        
        # Check initial votes is 1
        req = database.get_topic_request_by_id(req_id)
        self.assertEqual(req['votes'], 1)
        
        # Upvote using a different user (self.admin_id) - should succeed
        success = database.upvote_topic_request(self.admin_id, req_id)
        self.assertTrue(success)
        
        # Verify vote count incremented to 2
        req = database.get_topic_request_by_id(req_id)
        self.assertEqual(req['votes'], 2)
        
        # Upvote again with self.admin_id - should fail (duplicate prevention)
        success2 = database.upvote_topic_request(self.admin_id, req_id)
        self.assertFalse(success2)
        
        # Verify vote count is still 2
        req = database.get_topic_request_by_id(req_id)
        self.assertEqual(req['votes'], 2)
        
        # Test get_all_pending_topic_requests with user_id returns has_voted correctly
        pending_for_admin = database.get_all_pending_topic_requests(self.admin_id)
        # Find our request
        found_req = next((r for r in pending_for_admin if r['id'] == req_id), None)
        self.assertIsNotNone(found_req)
        self.assertEqual(found_req['has_voted'], 1)
        
        # Create a new user who hasn't voted yet
        new_voter_id = database.register_user("new_voter", "password123")
        self.assertIsNotNone(new_voter_id)
        
        pending_for_new = database.get_all_pending_topic_requests(new_voter_id)
        found_req_new = next((r for r in pending_for_new if r['id'] == req_id), None)
        self.assertIsNotNone(found_req_new)
        self.assertEqual(found_req_new['has_voted'], 0)

    def test_topic_request_approval_status_update(self):
        # Create a request to approve
        req_id = database.create_topic_request(self.user_id, "Go Programming", "A course on Golang")
        self.assertIsNotNone(req_id)
        
        # Approve the request
        success = database.approve_topic_request(req_id)
        self.assertTrue(success)
        
        # Verify status updated to approved
        req = database.get_topic_request_by_id(req_id)
        self.assertEqual(req['status'], "approved")
        
        # Verify that category was automatically spawned in categories table
        categories = database.get_categories()
        cat_names = [c['name'] for c in categories]
        self.assertIn("Go Programming", cat_names)

    def test_topic_request_rejection_status_update(self):
        # Create a request to reject
        req_id = database.create_topic_request(self.user_id, "Haskell Basics", "Functional programming concepts")
        self.assertIsNotNone(req_id)
        
        # Reject the request with a note
        success = database.reject_topic_request(req_id, "Already covered in our advanced paradigms module")
        self.assertTrue(success)
        
        # Verify status updated to rejected and admin note saved
        req = database.get_topic_request_by_id(req_id)
        self.assertEqual(req['status'], "rejected")
        self.assertEqual(req['admin_note'], "Already covered in our advanced paradigms module")

if __name__ == '__main__':
    unittest.main()
