from alembic import context
from app.models import Base

connection = context.config.attributes.get("connection")
if connection is None:
    raise RuntimeError("Run migrations through python -m app.bootstrap")
context.configure(connection=connection, target_metadata=Base.metadata)
with context.begin_transaction():
    context.run_migrations()
