"""Foundation schema: person, person_identity, user_account, session, audit_log.

Two rules are enforced here, in the database, because they cannot be trusted
to application code:

C-12 — identity is severable. person_identity is the only table erasure
touches; everything else references the meaningless person_id.

C-03 — the audit log is append-only. A trigger raises on UPDATE and DELETE
regardless of role, and the copernus_app role additionally never receives
those grants. Belt and braces: the trigger survives a connection using the
wrong role; the grant survives someone dropping the trigger.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "person",
        sa.Column("person_id", sa.Uuid, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_table(
        "person_identity",
        sa.Column(
            "person_id",
            sa.Uuid,
            sa.ForeignKey("person.person_id", name="fk_person_identity_person"),
            primary_key=True,
        ),
        sa.Column("full_name", sa.Text, nullable=False),
        sa.Column("role_title", sa.Text),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_table(
        "user_account",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("role", sa.Text, nullable=False, server_default="participant"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "person_id",
            sa.Uuid,
            sa.ForeignKey("person.person_id", name="fk_user_account_person"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_table(
        "session",
        sa.Column("token_hash", sa.Text, primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid,
            sa.ForeignKey("user_account.id", name="fk_session_user_account"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("event", sa.Text, nullable=False),
        sa.Column("user_id", sa.Text),
        sa.Column("correlation_id", sa.Text),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )

    # C-03: append-only, enforced twice.
    op.execute(
        """
        CREATE FUNCTION audit_log_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only (C-03)';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_log_no_rewrite
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_log_append_only();
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'copernus_app') THEN
                CREATE ROLE copernus_app LOGIN PASSWORD 'copernus_app';
            END IF;
        END
        $$;
        """
    )
    op.execute("GRANT CONNECT ON DATABASE copernus TO copernus_app")
    op.execute("GRANT USAGE ON SCHEMA public TO copernus_app")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON person, person_identity, "
        'user_account, "session" TO copernus_app'
    )
    op.execute("GRANT SELECT, INSERT ON audit_log TO copernus_app")


def downgrade() -> None:
    op.execute("REVOKE ALL ON audit_log FROM copernus_app")
    op.execute(
        'REVOKE ALL ON person, person_identity, user_account, "session" FROM copernus_app'
    )
    op.execute("DROP TRIGGER audit_log_no_rewrite ON audit_log")
    op.execute("DROP FUNCTION audit_log_append_only()")
    for table in ("audit_log", "session", "user_account", "person_identity", "person"):
        op.drop_table(table)
