# migrate_user_profiles.py
from app.database import engine
from sqlalchemy import MetaData, text

metadata = MetaData()
metadata.reflect(bind=engine)

users_table = metadata.tables.get("users")

if users_table is not None:
    existing_cols = set(users_table.columns.keys())
    dialect = engine.dialect.name

    # Add 'bio' column if missing
    if "bio" not in existing_cols:
        # Default to empty string; nullable to match typical profile bio behavior
        if dialect in ("sqlite", "postgresql", "mysql", "mariadb"):
            ddl = "ALTER TABLE users ADD COLUMN bio TEXT DEFAULT ''"
        else:
            # Fallback without DEFAULT if dialect unknown
            ddl = "ALTER TABLE users ADD COLUMN bio TEXT"
        with engine.begin() as conn:
            conn.execute(text(ddl))

        # Refresh metadata after schema change
        metadata.clear()
        metadata.reflect(bind=engine)
        users_table = metadata.tables.get("users")
        existing_cols = set(users_table.columns.keys())

    # Align with models: add 'avatar' (not 'profile_pic') if missing
    if "avatar" not in existing_cols:
        if dialect in ("sqlite", "postgresql", "mysql", "mariadb"):
            ddl = "ALTER TABLE users ADD COLUMN avatar VARCHAR(255) DEFAULT '/static/default-profile.png'"
        else:
            ddl = "ALTER TABLE users ADD COLUMN avatar VARCHAR(255)"
        with engine.begin() as conn:
            conn.execute(text(ddl))

print("✅ User table updated with bio and avatar fields.")
