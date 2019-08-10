"""Changed the youtube_id in tb_pleblist_song to be case sensitive, and made it an index.

Revision ID: 204b3e5a69e
Revises: 2e647f0995
Create Date: 2015-12-07 02:38:44.655666

"""

# revision identifiers, used by Alembic.
revision = "204b3e5a69e"
down_revision = "2e647f0995"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade():
    op.alter_column(
        "tb_pleblist_song",
        "youtube_id",
        existing_type=mysql.VARCHAR(length=64, collation="utf8mb4_bin"),
        nullable=False,
    )
    op.create_index(op.f("ix_tb_pleblist_song_youtube_id"), "tb_pleblist_song", ["youtube_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_tb_pleblist_song_youtube_id"), table_name="tb_pleblist_song")
    op.alter_column(
        "tb_pleblist_song",
        "youtube_id",
        existing_type=mysql.VARCHAR(length=64, collation="utf8mb4_general_ci"),
        nullable=False,
    )
