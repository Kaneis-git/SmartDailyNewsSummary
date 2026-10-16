from alembic import context

connection = context.config.attributes.get("connection")
if connection is None:
    raise RuntimeError("Use python manage.py init-db for safe upgrades")
context.configure(
    connection=connection,
    target_metadata=None,
    render_as_batch=True,
    transaction_per_migration=True,
)
with context.begin_transaction():
    context.run_migrations()
