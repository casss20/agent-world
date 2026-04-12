# 🔐 Security Implementation Guide
## Apply Security to Governance v2 in 10 Minutes

---

## Step 1: Install Dependencies (1 min)

```bash
cd ~/.openclaw/workspace/agent-world/backend

# Add to requirements.txt
echo "PyJWT==2.8.0" >> requirements.txt

# Install
pip install PyJWT
```

---

## Step 2: Copy Security Files (1 min)

```bash
# Copy the security middleware
cp security_middleware.py ~/.openclaw/workspace/agent-world/backend/

# Copy the secure routes (or merge into existing routes.py)
cp governance_v2/routes_secure.py ~/.openclaw/workspace/agent-world/backend/governance_v2/
```

---

## Step 3: Update main.py (2 min)

Add the security middleware to your FastAPI app:

```python
# main.py - Add these lines

from security_middleware import SecurityMiddleware

# After creating FastAPI app
app = FastAPI(title="Agent World", version="1.0")

# Add security middleware FIRST
app.add_middleware(SecurityMiddleware)

# Then add CORS (security middleware should be before CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Step 4: Update Routes (3 min)

Replace your current routes with secure versions:

```python
# In governance_v2/__init__.py or where you include routers

# OLD:
from .routes import router as governance_v2_router

# NEW (secure):
from .routes_secure import router as governance_v2_router
```

Or merge the security decorators into your existing routes:

```python
# In your existing routes.py, add these imports:
from security_middleware import (
    Role, get_current_user, require_admin,
    require_governor, require_operator
)

# Then add to each endpoint:
@router.post("/execute")
async def execute_action(
    request: ExecuteActionRequest,
    user: TokenPayload = Depends(require_governor()),  # ADD THIS
    governance=Depends(get_governance_system)
):
    ...
```

---

## Step 5: Generate Secret Key (1 min)

```bash
# Generate a secure random key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Copy the output and update security_middleware.py:
# JWT_SECRET = "your-generated-key-here"
```

---

## Step 6: Test Security (2 min)

```bash
# 1. Restart server
pkill -f uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 2. Test public endpoint (should work)
curl http://localhost:8000/governance/v2/health
# Expected: {"status":"healthy",...}

# 3. Test protected endpoint without auth (should fail)
curl http://localhost:8000/governance/v2/agents
# Expected: {"detail":"Authentication required"} - 401

# 4. Get token (login)
curl -X POST http://localhost:8000/governance/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin","role":"admin"}'
# Expected: {"access_token":"eyJ...","token_type":"bearer"}

# 5. Use token to access protected endpoint
TOKEN="eyJ..."  # Copy from above
curl http://localhost:8000/governance/v2/agents \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"count":0,"agents":[]}
```

---

## Security Checklist

After implementation, verify:

- [ ] `/health` works without auth
- [ ] `/agents` requires auth
- [ ] `/execute` requires governor+ role
- [ ] `/killswitches/trigger` requires admin role
- [ ] Invalid token returns 401
- [ ] Insufficient role returns 403
- [ ] Rate limiting active (check headers: `X-RateLimit-Remaining`)
- [ ] Audit logs capturing events

---

## Production Hardening

Before production deployment:

1. **Change JWT_SECRET** to a cryptographically secure random key
2. **Enable HTTPS** - Never use HTTP in production
3. **Restrict CORS** - Change `allow_origins=["*"]` to specific domains
4. **Add mTLS** for service-to-service calls
5. **Use Redis** for rate limiting (instead of in-memory)
6. **Write audit logs to persistent storage** (database/S3)
7. **Add request signing** for sensitive endpoints
8. **Implement token revocation** for logout

---

## Role Testing Matrix

Test each role can access appropriate endpoints:

| Endpoint | Viewer | Operator | Governor | Admin |
|----------|--------|----------|----------|-------|
| GET /health | ✅ | ✅ | ✅ | ✅ |
| GET /agents | ✅ | ✅ | ✅ | ✅ |
| POST /agents/register | ❌ | ✅ | ✅ | ✅ |
| POST /token | ❌ | ❌ | ✅ | ✅ |
| POST /execute | ❌ | ❌ | ✅ | ✅ |
| POST /killswitches/trigger | ❌ | ❌ | ❌ | ✅ |

---

## Troubleshooting

**Issue:** `ModuleNotFoundError: No module named 'jwt'`
```bash
pip install PyJWT
```

**Issue:** `AttributeError: 'Depends' object has no attribute 'sub'`
```python
# Wrong:
user: TokenPayload = Depends(get_current_user)

# Right:
async def endpoint(user: TokenPayload = Depends(get_current_user)):
```

**Issue:** Token validation fails
```python
# Check JWT_SECRET matches between creation and validation
# Check token hasn't expired (default: 24 hours)
```

---

## Files Created

1. `security_middleware.py` - Core security components
2. `governance_v2/routes_secure.py` - Secure route implementations
3. `SECURITY_SETUP.md` - This guide

---

**Status:** Ready to apply. Estimated time: 10 minutes.
