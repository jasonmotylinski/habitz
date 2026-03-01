# CI/CD Pipeline for Habitz

Automated testing and deployment workflow for the Habitz application.

## Overview

The CI/CD pipeline consists of two main stages:

1. **Test Stage** - Runs all tests (backend + frontend)
2. **Deploy Stage** - Only runs if tests pass, deploys to production

## GitHub Actions Workflow

### File: `.github/workflows/deploy.yml`

**Triggers:** Pushes to main branch

**Jobs:**

#### 1. Test Job

Runs on: Ubuntu Latest  
Python Version: 3.11

**Steps:**
1. Checkout code
2. Set up Python 3.11
3. Install dependencies (`pip install -r requirements.txt`)
4. Run backend tests: `pytest tests/ -v --tb=short`
   - Tests all trackers (habits, calorie, fasting, workout, meal)
   - Shows verbose output and short tracebacks
   - Fails if any test fails
5. Set up Node.js 18
6. Install frontend test dependencies
7. Run frontend tests: `npm test -- --coverage --passWithNoTests`
   - Generates coverage reports
   - Passes even if no tests found
8. Upload coverage to Codecov (optional)

#### 2. Deploy Job

Runs on: Ubuntu Latest  
Depends on: `test` job (won't run if tests fail)  
Runs only if: Branch is `main`

**Steps:**
1. SSH to production server
2. Execute `/var/projects/habitz/scripts/prod/deploy.sh`

## Production Deploy Script

### File: `scripts/prod/deploy.sh`

**Actions (in order):**

1. **Pull latest code**
   ```bash
   git pull origin main
   ```

2. **Install/update dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run backend tests** (REQUIRED)
   ```bash
   pytest tests/ -v --tb=short
   ```
   - **Blocks deployment if tests fail**
   - Validates environment before restart

4. **Run frontend tests** (OPTIONAL)
   ```bash
   npm test
   ```
   - Doesn't block deployment
   - For validation only

5. **Run database migrations** (REQUIRED)
   ```bash
   flask db init        # Only runs if migrations/ dir doesn't exist
   flask db upgrade     # Applies pending migrations
   ```
   - Initializes migration system if needed
   - **Blocks deployment if migrations fail**
   - See `DATABASE_MIGRATIONS.md` for details

6. **Restart service**
   ```bash
   sudo systemctl restart habitz
   ```
   - Only runs if backend tests and migrations pass

## Deployment Flow

```
┌─────────────────┐
│   Push to main  │
└────────┬────────┘
         │
         ▼
┌────────────────────────────────┐
│   GitHub Actions: Test Job     │
│  - Backend tests (pytest)      │
│  - Frontend tests (Jest)       │
│  - Upload coverage             │
└────────┬───────────────────────┘
         │
    ┌────┴─────────────┐
    │ Tests Pass?      │
    └────┬─────────────┘
         │
    ┌────▼─────────────┐
    │      YES         │
    └────┬─────────────┘
         │
         ▼
┌────────────────────────────────┐
│   GitHub Actions: Deploy Job   │
│  - SSH to server               │
│  - Run deploy.sh               │
└────────┬───────────────────────┘
         │
         ▼
┌────────────────────────────────┐
│   Production Server Deploy     │
│  - Pull code                   │
│  - Install deps                │
│  - Run tests (local)           │
│  - Restart gunicorn            │
└────────────────────────────────┘
```

## Local Testing Before Push

Run locally to catch issues early:

```bash
# Backend tests
pytest tests/ -v

# Frontend tests
npm test

# With coverage
pytest tests/ --cov=landing --cov=calorie_tracker --cov=fasting_tracker --cov=workout_tracker --cov=meal_planner
```

## Required Secrets

GitHub Secrets (set in repo settings):

- `DEPLOY_HOST` - Production server hostname
- `DEPLOY_USER` - SSH username
- `DEPLOY_SSH_KEY` - Private SSH key for authentication

## Test Coverage

**Backend (pytest):** 114+ tests
- Habits Tracker: 14 tests
- Calorie Tracker: 20+ tests
- Fasting Tracker: 25+ tests
- Workout Tracker: 30+ tests
- Meal Planner: 25+ tests

**Frontend (Jest):** 20+ tests
- Date navigation
- Progress tracking
- Ring rendering
- API interactions

## Rollback Procedure

If deployment fails:

1. SSH to production server
2. Revert code: `git revert <commit-hash>`
3. Re-run deploy: `./scripts/prod/deploy.sh`
4. Verify service: `sudo systemctl status habitz`

## Monitoring

After deployment, check:

```bash
# Service status
sudo systemctl status habitz

# Logs
sudo journalctl -u habitz -n 50 -f

# Health check
curl http://localhost:8000/health  # if available
```

## Database Migrations

**Important:** The deployment process now includes automatic database migration steps:

1. Check if migrations directory exists
2. Initialize if needed (`flask db init`)
3. Apply pending migrations (`flask db upgrade`)

For detailed migration workflow and troubleshooting, see `DATABASE_MIGRATIONS.md`.

## Future Improvements

- [ ] Add smoke tests post-deployment (healthcheck endpoint)
- [ ] Add performance benchmarks
- [ ] Add security scanning (bandit, safety)
- [ ] Add code quality checks (pylint, black)
- [ ] Add automated rollback on service failure
- [ ] Add Slack notifications for deployments
- [ ] Test migrations in CI/CD pipeline
- [ ] Remove `db.create_all()` and use migrations exclusively
