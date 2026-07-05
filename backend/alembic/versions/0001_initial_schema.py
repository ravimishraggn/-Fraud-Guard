"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("plan", sa.String(50), server_default="starter"),
        sa.Column("doc_limit_monthly", sa.Integer(), server_default=sa.text("100")),
        sa.Column("docs_used_this_month", sa.Integer(), server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("settings", JSONB(), server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), server_default="operator"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("original_filename", sa.String(500)),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("file_size_bytes", sa.BigInteger()),
        sa.Column("storage_path", sa.Text()),
        sa.Column("status", sa.String(50), server_default="UPLOADED", index=True),
        sa.Column("doc_type", sa.String(100)),
        sa.Column("doc_type_confidence", sa.Float()),
        sa.Column("overall_risk_score", sa.Integer(), server_default=sa.text("0")),
        sa.Column("risk_level", sa.String(20), server_default="unknown"),
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("review_decision", sa.String(50)),
        sa.Column("review_note", sa.Text()),
        sa.Column("processing_started_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("processing_completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("processing_ms", sa.Integer()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column("metadata", JSONB(), server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "extracted_fields",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("raw_value", sa.Text()),
        sa.Column("normalised_value", sa.Text()),
        sa.Column("confidence", sa.Float()),
        sa.Column("source", sa.String(50)),
        sa.Column("page_number", sa.Integer(), server_default=sa.text("1")),
        sa.Column("bbox_x", sa.Float()),
        sa.Column("bbox_y", sa.Float()),
        sa.Column("bbox_w", sa.Float()),
        sa.Column("bbox_h", sa.Float()),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("corrected_value", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_extracted_fields_name", "extracted_fields", ["field_name"])

    op.create_table(
        "fraud_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("flag_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("confidence", sa.Float()),
        sa.Column("is_false_positive", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("false_positive_reason", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "vendors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("gstin", sa.String(20)),
        sa.Column("pan", sa.String(15)),
        sa.Column("bank_account", sa.String(50), index=True),
        sa.Column("bank_ifsc", sa.String(20)),
        sa.Column("is_whitelisted", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("risk_score", sa.Integer(), server_default=sa.text("0")),
        sa.Column("total_invoices", sa.Integer(), server_default=sa.text("0")),
        sa.Column("total_amount_paise", sa.BigInteger(), server_default=sa.text("0")),
        sa.Column("flagged_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("first_seen", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_vendors_tenant_name"),
    )

    op.create_table(
        "fraud_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("rule_name", sa.String(255), nullable=False),
        sa.Column("rule_type", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("config", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True)),
        sa.Column("document_id", UUID(as_uuid=True)),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_data", JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("ip_address", INET()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # Make audit_logs immutable at the database level
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_logs_immutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER audit_logs_no_update
            BEFORE UPDATE OR DELETE ON audit_logs
            FOR EACH ROW EXECUTE FUNCTION audit_logs_immutable();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_update ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS audit_logs_immutable")
    for table in (
        "audit_logs",
        "fraud_rules",
        "vendors",
        "fraud_flags",
        "extracted_fields",
        "documents",
        "users",
        "tenants",
    ):
        op.drop_table(table)
