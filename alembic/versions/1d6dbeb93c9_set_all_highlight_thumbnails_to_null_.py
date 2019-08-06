"""Set all highlight thumbnails to null, since I fucked things up earlier

Revision ID: 1d6dbeb93c9
Revises: 155eda5d09d
Create Date: 2015-12-20 03:10:35.571829

"""

# revision identifiers, used by Alembic.
revision = "1d6dbeb93c9"
down_revision = "155eda5d09d"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    conn = op.get_bind()
    conn.execute("UPDATE `tb_stream_chunk_highlight` SET `thumbnail`=null;")


def downgrade():
    pass
