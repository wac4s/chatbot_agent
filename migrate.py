# add parent directory to path
import sys
import os

# Add parent directory to sys.path to find app/
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.models import Base
from app.database import engine

print("Running migrations...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("Migration complete.")

# migrate.py

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))


# manual migration
from app.models import Base
from app.database import engine

# WARNING: This will DELETE all tables and recreate them
print("Dropping and recreating all tables...")

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

print("Migration complete.")

# Notifications System
from app.models import Notification
Base.metadata.create_all(bind=engine)
