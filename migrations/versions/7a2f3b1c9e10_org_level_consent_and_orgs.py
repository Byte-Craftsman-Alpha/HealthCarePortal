"""phase 1: organizations + org-level consent

Revision ID: 7a2f3b1c9e10
Revises: c125e8449d3d
Create Date: 2026-01-16

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7a2f3b1c9e10"
down_revision = "c125e8449d3d"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Clean up partial runs (SQLite): if a previous attempt died mid-upgrade
    if inspector.has_table("_consents_new"):
        op.drop_table("_consents_new")

    # Clean up leftover Alembic batch temp tables (SQLite)
    for tmp in [
        "_alembic_tmp_doctors",
        "_alembic_tmp_appointments",
        "_alembic_tmp_audit_events",
        "_alembic_tmp_consents",
    ]:
        if inspector.has_table(tmp):
            op.drop_table(tmp)

    # 1) organizations table
    if not inspector.has_table("organizations"):
        op.create_table(
            "organizations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("org_type", sa.String(length=32), nullable=False, server_default=sa.text("'hospital'")),
            sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("name", name="uq_organizations_name"),
        )
        with op.batch_alter_table("organizations", schema=None) as batch_op:
            batch_op.create_index(batch_op.f("ix_organizations_name"), ["name"], unique=True)
            batch_op.create_index(batch_op.f("ix_organizations_org_type"), ["org_type"], unique=False)

    # 2) add organization_id columns to doctors/appointments/audit_events if missing
    doctor_cols = {c["name"] for c in inspector.get_columns("doctors")}
    with op.batch_alter_table("doctors", schema=None) as batch_op:
        if "organization_id" not in doctor_cols:
            batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
            batch_op.create_index(batch_op.f("ix_doctors_organization_id"), ["organization_id"], unique=False)
            batch_op.create_foreign_key(
                "fk_doctors_organization_id_organizations",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="SET NULL",
            )

    appt_cols = {c["name"] for c in inspector.get_columns("appointments")}
    with op.batch_alter_table("appointments", schema=None) as batch_op:
        if "organization_id" not in appt_cols:
            batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
            batch_op.create_index(batch_op.f("ix_appointments_organization_id"), ["organization_id"], unique=False)
            batch_op.create_foreign_key(
                "fk_appointments_organization_id_organizations",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if inspector.has_table("audit_events"):
        ae_cols = {c["name"] for c in inspector.get_columns("audit_events")}
        with op.batch_alter_table("audit_events", schema=None) as batch_op:
            if "organization_id" not in ae_cols:
                batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
                batch_op.create_index(batch_op.f("ix_audit_events_organization_id"), ["organization_id"], unique=False)
                batch_op.create_foreign_key(
                    "fk_audit_events_organization_id_organizations",
                    "organizations",
                    ["organization_id"],
                    ["id"],
                    ondelete="SET NULL",
                )

    # 3) backfill organizations + doctor.organization_id from doctor.hospital_id
    # Create one org per distinct hospital_id; fall back to 'Independent Practice'
    op.execute(
        "INSERT OR IGNORE INTO organizations (name, org_type, verified) "
        "SELECT COALESCE(NULLIF(TRIM(hospital_id), ''), 'Independent Practice') AS name, 'hospital', 1 "
        "FROM doctors GROUP BY COALESCE(NULLIF(TRIM(hospital_id), ''), 'Independent Practice')"
    )

    op.execute(
        "UPDATE doctors SET organization_id = ("
        "  SELECT o.id FROM organizations o "
        "  WHERE o.name = COALESCE(NULLIF(TRIM(doctors.hospital_id), ''), 'Independent Practice')"
        ") "
        "WHERE organization_id IS NULL"
    )

    # 4) Migrate consents from doctor-based to org-based.
    # We rebuild the table in-place for SQLite reliability.
    consent_cols = {c["name"] for c in inspector.get_columns("consents")}

    has_doctor_id = "doctor_id" in consent_cols
    has_org_id = "organization_id" in consent_cols

    if has_doctor_id and not has_org_id:
        with op.batch_alter_table("consents", schema=None) as batch_op:
            batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
            batch_op.create_index(batch_op.f("ix_consents_organization_id"), ["organization_id"], unique=False)
            batch_op.create_foreign_key(
                "fk_consents_organization_id_organizations",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="CASCADE",
            )

        # Backfill organization_id via doctor->organization
        op.execute(
            "UPDATE consents SET organization_id = ("
            "  SELECT d.organization_id FROM doctors d WHERE d.user_id = consents.doctor_id"
            ") "
            "WHERE organization_id IS NULL"
        )

        # Create new table schema and copy data (dedupe by patient_id+organization_id)
        op.create_table(
            "_consents_new",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("patient_id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("granted_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("can_view_history", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("can_add_record", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.user_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("patient_id", "organization_id", name="uq_consent_patient_org"),
        )
        with op.batch_alter_table("_consents_new", schema=None) as batch_op:
            # SQLite index names are global; avoid clashing with existing ix_consents_* on old table
            batch_op.create_index("ix__consents_new_patient_id", ["patient_id"], unique=False)
            batch_op.create_index("ix__consents_new_organization_id", ["organization_id"], unique=False)

        # Most recent granted_at wins; scopes: take max (true if any)
        op.execute(
            "INSERT INTO _consents_new (patient_id, organization_id, granted_at, revoked_at, can_view_history, can_add_record) "
            "SELECT c.patient_id, c.organization_id, MAX(c.granted_at), "
            "       CASE WHEN SUM(CASE WHEN c.revoked_at IS NULL THEN 1 ELSE 0 END) > 0 THEN NULL ELSE MAX(c.revoked_at) END, "
            "       MAX(CASE WHEN c.can_view_history THEN 1 ELSE 0 END), "
            "       MAX(CASE WHEN c.can_add_record THEN 1 ELSE 0 END) "
            "FROM consents c "
            "WHERE c.organization_id IS NOT NULL "
            "GROUP BY c.patient_id, c.organization_id"
        )

        op.drop_table("consents")
        op.rename_table("_consents_new", "consents")

    # 5) backfill appointments.organization_id and audit_events.organization_id
    op.execute(
        "UPDATE appointments SET organization_id = ("
        "  SELECT d.organization_id FROM doctors d WHERE d.user_id = appointments.doctor_id"
        ") "
        "WHERE organization_id IS NULL"
    )

    if inspector.has_table("audit_events"):
        op.execute(
            "UPDATE audit_events SET organization_id = ("
            "  SELECT d.organization_id FROM doctors d WHERE d.user_id = audit_events.doctor_id"
            ") "
            "WHERE organization_id IS NULL"
        )


def downgrade():
    # Non-trivial downgrade (data migration). Keep schema as-is.
    pass
