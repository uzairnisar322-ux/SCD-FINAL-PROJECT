import unittest
import sys

def run_all_tests():
    print("====================================================")
    print("Running Quiz App Core Unit Tests...")
    print("====================================================")
    
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir='tests')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n[SUCCESS] All tests passed successfully!")
        sys.exit(0)
    else:
        print(f"\n[FAILURE] {len(result.failures)} failures and {len(result.errors)} errors encountered.")
        sys.exit(1)

if __name__ == '__main__':
    run_all_tests()
