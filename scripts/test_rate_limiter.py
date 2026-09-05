import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
from src.audio_generator import GeminiRateLimiter

def test_gemini_rate_limiter():
    print("🧪 Testing GeminiRateLimiter...")
    
    # Test 1: Min interval spacing with small interval
    limiter = GeminiRateLimiter(max_rpm=10, min_interval_sec=0.2)
    start = time.time()
    limiter.wait_if_needed()
    limiter.wait_if_needed()
    elapsed = time.time() - start
    assert elapsed >= 0.19, f"Elapsed time {elapsed} was less than min_interval 0.2s"
    print(f"✅ Test 1 (Minimum Interval Spacing): Passed (elapsed: {elapsed:.2f}s)")

    # Test 2: Max RPM limit in rolling window
    test_rpm = 3
    limiter2 = GeminiRateLimiter(max_rpm=test_rpm, min_interval_sec=0.05)
    # Fill up the 3 quota slots
    t0 = time.time()
    limiter2.wait_if_needed()
    limiter2.wait_if_needed()
    limiter2.wait_if_needed()
    
    # Check that 3 timestamps are registered
    assert len(limiter2.timestamps) == 3, f"Expected 3 timestamps, got {len(limiter2.timestamps)}"
    print("✅ Test 2 (Rolling Window Capacity): Passed")

    print("\n🎉 All GeminiRateLimiter unit tests passed successfully!")

if __name__ == "__main__":
    test_gemini_rate_limiter()
