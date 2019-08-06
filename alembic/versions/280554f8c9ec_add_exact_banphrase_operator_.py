"""empty message

Revision ID: 280554f8c9ec
Revises: 8feba263d722
Create Date: 2017-04-10 06:44:41.325600

"""

# revision identifiers, used by Alembic.
revision = "280554f8c9ec"
down_revision = "8feba263d722"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """ALTER TABLE `tb_banphrase` MODIFY COLUMN `operator` ENUM ('contains', 'startswith', 'endswith', 'exact') NOT NULL DEFAULT 'contains';"""
        )
    )


def downgrade():
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """ALTER TABLE `tb_banphrase` MODIFY COLUMN `operator` ENUM ('contains', 'startswith', 'endswith') NOT NULL DEFAULT 'contains';"""
        )
    )
