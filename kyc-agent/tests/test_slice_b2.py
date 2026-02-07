"""Test Slice B2: Usage Tracker"""
import sys
import os

sys.path.insert(0, r"C:\Users\tehreem.rizwan\Desktop\pet-p\hackathon\kyc-agent")
os.chdir(r"C:\Users\tehreem.rizwan\Desktop\pet-p\hackathon\kyc-agent")

print("=" * 60)
print("SLICE B2: USAGE TRACKER - TEST")
print("=" * 60)

# Test 1: Import module
print("TEST 1: Import usage_tracker module")
from backend.usage_tracker import (
    UsageTracker,
    UsageLevel,
    UsageStats,
    FieldRetryInfo,
    get_tracker,
    record_api_call,
    can_make_api_call,
    get_usage_status,
    can_retry_document,
    record_document_attempt
)
print("   PASSED - Module imported successfully")

# Test 2: UsageLevel enum
print("TEST 2: UsageLevel enum values")
assert UsageLevel.GREEN.value == "green"
assert UsageLevel.YELLOW.value == "yellow"
assert UsageLevel.RED.value == "red"
assert UsageLevel.BLOCKED.value == "blocked"
print("   PASSED")

# Test 3: UsageTracker initialization
print("TEST 3: UsageTracker initialization")
tracker = UsageTracker()
assert tracker.total_calls == 0
assert tracker.can_make_call == True
assert tracker.usage_level == UsageLevel.GREEN
print(f"  Initial calls: {tracker.total_calls}, Level: {tracker.usage_level.value}")
print("   PASSED")

# Test 4: Record API calls
print("TEST 4: Record API calls")
success, msg = tracker.record_call()
assert success == True
assert tracker.total_calls == 1
print(f"  After 1 call: {tracker.total_calls}")

# Add more calls
for i in range(9):
    tracker.record_call()
assert tracker.total_calls == 10
assert tracker.usage_level == UsageLevel.GREEN
print(f"  After 10 calls: Level = {tracker.usage_level.value} ")

# Test 5: Warning threshold (50 calls)
print("TEST 5: Warning threshold at 50 calls")
for i in range(40):  # Now at 50
    tracker.record_call()
assert tracker.total_calls == 50
assert tracker.usage_level == UsageLevel.YELLOW
print(f"  At 50 calls: Level = {tracker.usage_level.value} ")

# Test 6: Critical threshold (80 calls)
print("TEST 6: Critical threshold at 80 calls")
for i in range(30):  # Now at 80
    tracker.record_call()
assert tracker.total_calls == 80
assert tracker.usage_level == UsageLevel.RED
print(f"  At 80 calls: Level = {tracker.usage_level.value} ")

# Test 7: Blocked at 100 calls
print("TEST 7: Blocked at 100 calls")
for i in range(20):  # Now at 100
    tracker.record_call()
assert tracker.total_calls == 100
assert tracker.usage_level == UsageLevel.BLOCKED
assert tracker.can_make_call == False
print(f"  At 100 calls: Level = {tracker.usage_level.value} ")

# Test 8: Blocked call rejected
print("TEST 8: Blocked call rejected")
success, msg = tracker.record_call()
assert success == False
assert "limit" in msg.lower()
print(f"  Blocked message: {msg} ")

# Test 9: Field retry tracking
print("TEST 9: Field retry tracking")
tracker2 = UsageTracker()

# First attempt
can_retry, remaining = tracker2.can_retry_field("cnic", "front")
assert can_retry == True
assert remaining == 2
print(f"  Before attempts: can_retry={can_retry}, remaining={remaining}")

# Record first attempt
success, msg = tracker2.record_field_attempt("cnic", "front")
assert success == True
print(f"  After 1st attempt: {msg}")

# Second attempt
success, msg = tracker2.record_field_attempt("cnic", "front")
assert success == True
assert "last attempt" in msg.lower()
print(f"  After 2nd attempt: {msg}")

# Third attempt should fail
can_retry, remaining = tracker2.can_retry_field("cnic", "front")
assert can_retry == False
assert remaining == 0
print(f"  After max attempts: can_retry={can_retry}, remaining={remaining} ")

success, msg = tracker2.record_field_attempt("cnic", "front")
assert success == False
assert "maximum" in msg.lower()
print(f"  Blocked retry message: {msg} ")

# Test 10: Status messages
print("TEST 10: Status messages")
tracker3 = UsageTracker()
level, msg, color = tracker3.get_status_message()
assert level == "ok"
assert "#28a745" in color  # Green
print(f"  Green status: {msg[:40]}...")

for i in range(55):
    tracker3.record_call()
level, msg, color = tracker3.get_status_message()
assert level == "warning"
assert "#ffc107" in color  # Yellow
print(f"  Yellow status: {msg[:40]}...")

for i in range(30):
    tracker3.record_call()
level, msg, color = tracker3.get_status_message()
assert level == "critical"
assert "#dc3545" in color  # Red
print(f"  Red status: {msg[:40]}... ")

# Test 11: Serialization
print("TEST 11: Serialization (to_dict/from_dict)")
tracker4 = UsageTracker()
for i in range(25):
    tracker4.record_call()
tracker4.record_field_attempt("passport", "front")

data = tracker4.to_dict()
assert data["total_calls"] == 25
assert "passport_front" in data["field_retries"]
print(f"  Serialized: {data['total_calls']} calls, {len(data['field_retries'])} fields")

tracker5 = UsageTracker()
tracker5.from_dict(data)
assert tracker5.total_calls == 25
can_retry, remaining = tracker5.can_retry_field("passport", "front")
assert remaining == 1  # One attempt was recorded
print(f"  Restored: {tracker5.total_calls} calls, passport remaining={remaining} ")

# Test 12: Reset functionality
print("TEST 12: Reset functionality")
tracker4.reset_field("passport", "front")
can_retry, remaining = tracker4.can_retry_field("passport", "front")
assert remaining == 2  # Reset to full
print(f"  After field reset: remaining={remaining}")

tracker4.reset_all()
assert tracker4.total_calls == 0
print(f"  After full reset: calls={tracker4.total_calls} ")

print("=" * 60)
print("SLICE B2 COMPLETE - All tests passed!")
print("=" * 60)
