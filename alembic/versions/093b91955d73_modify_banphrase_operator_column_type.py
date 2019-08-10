"""modify banphrase operator column type

Revision ID: 093b91955d73
Revises: 514603f2ff1f
Create Date: 2018-10-07 20:57:11.687549

"""

# revision identifiers, used by Alembic.
revision = "093b91955d73"
down_revision = "514603f2ff1f"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    conn = op.get_bind()
    conn.execute(
        sa.text("""ALTER TABLE `tb_banphrase` MODIFY COLUMN `operator` VARCHAR(32) NOT NULL DEFAULT 'contains';""")
    )


def downgrade():
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """ALTER TABLE `tb_banphrase` MODIFY COLUMN `operator` ENUM ('contains', 'startswith', 'endswith', 'exact') NOT NULL DEFAULT 'contains';"""
        )
    )
