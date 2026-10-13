"""account_management_and_sessions

Revision ID: a1b2c3d4e5f6
Revises: 569959669ccc
Create Date: 2026-10-13 17:42:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '569959669ccc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_verified_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('token_version', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('failed_login_count', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('locked_until', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('last_login_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('deletion_requested_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('pending_totp_secret', sa.Text(), nullable=True))

    # Mark existing active users as verified using their creation timestamp
    op.execute("UPDATE users SET email_verified_at = created_at WHERE email_verified_at IS NULL")

    # 2. Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('family_id', sa.String(length=36), nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=False),
        sa.Column('idle_expires_at', sa.DateTime(), nullable=False),
        sa.Column('absolute_expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_reason', sa.String(length=50), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('device_label', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.create_index('ix_sessions_user_id', ['user_id'], unique=False)
        batch_op.create_index('ix_sessions_family_id', ['family_id'], unique=False)
        batch_op.create_index('ix_sessions_refresh_token_hash', ['refresh_token_hash'], unique=True)

    # 3. Create verification_codes table
    op.create_table(
        'verification_codes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('purpose', sa.String(length=40), nullable=False),
        sa.Column('code_hash', sa.String(length=64), nullable=False),
        sa.Column('new_email', sa.String(length=255), nullable=True),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('consumed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('verification_codes', schema=None) as batch_op:
        batch_op.create_index('ix_verification_codes_user_id', ['user_id'], unique=False)
        batch_op.create_index('ix_verification_codes_purpose', ['purpose'], unique=False)

    # 4. Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('event', sa.String(length=80), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.create_index('ix_audit_logs_user_id', ['user_id'], unique=False)
        batch_op.create_index('ix_audit_logs_event', ['event'], unique=False)
        batch_op.create_index('ix_audit_logs_created_at', ['created_at'], unique=False)

    # 5. Create rate_limit_buckets table
    op.create_table(
        'rate_limit_buckets',
        sa.Column('key', sa.String(length=200), nullable=False),
        sa.Column('window_start', sa.Float(), nullable=False),
        sa.Column('count', sa.Integer(), server_default='1', nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )


def downgrade() -> None:
    op.drop_table('rate_limit_buckets')
    op.drop_table('audit_logs')
    op.drop_table('verification_codes')
    op.drop_table('sessions')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('pending_totp_secret')
        batch_op.drop_column('deletion_requested_at')
        batch_op.drop_column('last_login_at')
        batch_op.drop_column('locked_until')
        batch_op.drop_column('failed_login_count')
        batch_op.drop_column('token_version')
        batch_op.drop_column('email_verified_at')
