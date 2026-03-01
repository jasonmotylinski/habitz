# Database Migrations for Habitz

## Overview

Habitz uses **Flask-Migrate** (Alembic) for database schema versioning and migrations. This allows controlled evolution of the database schema across deployments.

## Initial Setup (One-time)

When deploying for the first time or setting up a new environment:

```bash
# Initialize migrations directory (if it doesn't exist)
flask db init

# Create initial migration from current models
flask db migrate -m "Initial schema"

# Apply migration to database
flask db upgrade
```

## Creating New Migrations

After modifying any model files (adding/removing/changing columns):

```bash
# Create migration file based on model changes
flask db migrate -m "Add new field to DailyMood"

# Review the generated migration file in migrations/versions/
# Edit if necessary (usually auto-generated is correct)

# Apply the migration
flask db upgrade
```

## Deployment Process

The deployment script (`scripts/prod/deploy.sh`) automatically:

1. Initializes migrations directory if it doesn't exist
2. Runs pending migrations with `flask db upgrade`
3. Aborts deployment if migrations fail

```bash
$ ./scripts/prod/deploy.sh
==> Running database migrations...
    Initializing migrations...
==> Applying migrations...
✓ Database migrations applied.
```

## Models That Need Migrations

The following recent additions need their first migrations created:

- **DailyNote** (landing/models.py) - Daily notes/reflections
- **DailyMood** (landing/models.py) - Daily mood tracking (1-5 scale)

### Creating migrations for new models

```bash
# Create migration for DailyNote and DailyMood
flask db migrate -m "Add daily notes and mood tracking"

# Review generated file (should include table creation for daily_note and daily_mood)
cat migrations/versions/*.py

# Apply
flask db upgrade
```

## Checking Migration Status

```bash
# See current database version
flask db current

# See all available migrations
flask db history

# See what would happen on next upgrade
flask db upgrade --sql
```

## Rollback (Emergency)

If a deployment goes wrong:

```bash
# Downgrade one version
flask db downgrade

# Downgrade to specific version
flask db downgrade <revision>
```

## Best Practices

1. **Always test migrations locally first**
   ```bash
   # Create test database with migrations
   export DATABASE_URL=sqlite:///test.db
   flask db upgrade
   flask db downgrade
   flask db upgrade
   ```

2. **Keep migrations small and focused**
   - One logical change per migration
   - Makes rollbacks easier

3. **Review generated migrations**
   - Auto-generated migrations are usually correct
   - But always review before committing

4. **Commit migrations with code changes**
   ```bash
   git add migrations/versions/*.py landing/models.py
   git commit -m "Add daily mood field to users"
   ```

5. **Never edit migration files after deployment**
   - Creates consistency issues
   - Create a new migration if you need to change schema

## Troubleshooting

### Migration File Not Found

```
sqlalchemy.exc.MigrationError: Can't locate revision identified by ''
```

**Solution:** Initialize migrations directory
```bash
flask db init
flask db migrate -m "Initial"
```

### Database Locked

```
sqlalchemy.exc.OperationalError: database is locked
```

**Solution:** 
- Check no other processes are using the database
- Close other terminals/sessions
- Restart database service if needed

### Table Already Exists

```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.DuplicateTable)
```

**Solution:** This happens if `db.create_all()` and migrations both run
- The app already creates tables in `landing/__init__.py`
- In production, rely on migrations only
- Consider removing `db.create_all()` and using migrations exclusively

## Future: Complete Migration Setup

For full production readiness:

1. Remove `db.create_all()` from `landing/__init__.py`
2. Rely exclusively on Flask-Migrate
3. Create initial migration snapshot of current schema
4. Set up migration testing in CI/CD

## References

- [Flask-Migrate Documentation](https://flask-migrate.readthedocs.io/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
