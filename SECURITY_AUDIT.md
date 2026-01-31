# Security Audit Report

**Date:** 2026-01-30  
**Auditor:** Self-review  
**Version:** 0.2.0

---

## 🔴 CRITICAL (Must fix before publish)

### 1. API Keys Exposed in `/agents` Endpoint
**File:** `agentgraph/api/server.py` lines 253, 272  
**Issue:** The `list_agents` and `create_agent` responses include the `api_key` field, exposing all API keys to anyone who can call the endpoint.  
**Impact:** Complete authentication bypass - attacker can impersonate any agent.  
**Fix:** Remove `api_key` from list responses; only return on create.

### 2. CORS Allow All Origins
**File:** `agentgraph/api/server.py` line 87  
**Issue:** `allow_origins=["*"]` allows any website to make authenticated requests.  
**Impact:** Cross-site request forgery, data exfiltration from browsers.  
**Fix:** Configure specific allowed origins or make configurable.

### 3. WebSocket Endpoint Has No Authentication
**File:** `agentgraph/api/server.py` line 192  
**Issue:** `/ws` endpoint accepts any connection without auth. All events are broadcast.  
**Impact:** Information disclosure - anyone can see all agent activity.  
**Fix:** Add authentication to WebSocket connections.

### 4. No Rate Limiting
**Issue:** API has no rate limiting on any endpoint.  
**Impact:** Brute force attacks on API keys, DoS attacks, resource exhaustion.  
**Fix:** Add rate limiting middleware (e.g., slowapi).

---

## 🟠 HIGH (Should fix)

### 5. No Limit Parameter Caps
**File:** `agentgraph/api/server.py`, multiple endpoints  
**Issue:** `limit` parameters accept any integer value (e.g., limit=999999999).  
**Impact:** Resource exhaustion, slow queries, memory issues.  
**Fix:** Cap limits at reasonable maximums (e.g., 1000).

### 6. Deprecated datetime.utcnow()
**File:** Multiple files  
**Issue:** `datetime.utcnow()` is deprecated in Python 3.12+.  
**Impact:** Future compatibility issues, potential timezone bugs.  
**Fix:** Use `datetime.now(datetime.UTC)`.

### 7. Search LIKE Injection
**File:** `agentgraph/storage/database.py`  
**Issue:** Search queries don't escape `%` and `_` wildcard characters.  
**Impact:** Unintended pattern matching, potential information disclosure.  
**Fix:** Escape special LIKE characters in search input.

---

## 🟡 MEDIUM

### 8. No Input Length Validation
**Issue:** Fields like `name`, `description`, `metadata` have no length limits.  
**Impact:** Storage exhaustion, potential DoS.  
**Fix:** Add Pydantic validators with max lengths.

### 9. No Connection Pooling
**File:** `agentgraph/storage/database.py`  
**Issue:** Creates new SQLite connection for each request.  
**Impact:** Performance degradation under load.  
**Fix:** Use connection pooling or single persistent connection.

### 10. Global Mutable State
**File:** `agentgraph/api/server.py`  
**Issue:** `db` and `manager` are global singletons.  
**Impact:** Testing difficulties, potential race conditions.  
**Fix:** Use dependency injection.

---

## 🟢 LOW

### 11. Secrets in Plain Memory
**Issue:** API keys stored as plain strings in memory.  
**Impact:** Memory dumps could expose secrets.  
**Mitigation:** Use secure string handling in production.

### 12. No Audit Logging
**Issue:** No logging of authentication attempts, failures, sensitive operations.  
**Impact:** Difficult to detect and investigate security incidents.  
**Fix:** Add structured security logging.

### 13. No HTTPS Enforcement
**Issue:** Server accepts HTTP connections.  
**Impact:** Credentials and data transmitted in plaintext.  
**Mitigation:** Document that HTTPS should be used in production (handled by reverse proxy).

---

## Code Quality Issues

### 1. SQL Queries
✅ **GOOD:** Uses parameterized queries (protected against SQL injection)

### 2. Error Handling
⚠️ **NEEDS WORK:** Some bare exception handlers, inconsistent error responses

### 3. Type Hints
✅ **GOOD:** Generally good type annotation coverage

### 4. Testing
✅ **GOOD:** 34 tests passing, but no security-focused tests

---

## Recommendations

### Before Publishing:
1. Fix CRITICAL issues #1-4
2. Add limit caps
3. Fix deprecated datetime usage

### Post-Launch:
1. Add security logging
2. Implement connection pooling
3. Add security-focused tests
4. Consider adding OWASP security headers

---

## Verification Commands

```bash
# Check for exposed API keys
grep -r "api_key" agentgraph/ --include="*.py"

# Check for SQL injection (should use ? params)
grep -rn "f\".*SELECT\|f'.*SELECT" agentgraph/

# Check CORS config
grep -n "allow_origins" agentgraph/

# Run security-focused tests (TODO: create these)
pytest tests/test_security.py -v
```
