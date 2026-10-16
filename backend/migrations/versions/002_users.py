from alembic import op

revision = "002_users"
down_revision = "001_mvp"
branch_labels = None
depends_on = None
STATEMENTS = [
    '\nCREATE TABLE auth_rates (\n\t"key" VARCHAR(64) NOT NULL, \n\twindow INTEGER NOT NULL, \n\tcount INTEGER NOT NULL, \n\tPRIMARY KEY ("key")\n)\n\n',
    "\nCREATE TABLE users (\n\tid INTEGER NOT NULL, \n\tusername VARCHAR(32) NOT NULL, \n\tdisplay_name VARCHAR(60) NOT NULL, \n\tpassword_hash TEXT NOT NULL, \n\tcreated_at DATETIME NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (username)\n)\n\n",
    "\nCREATE TABLE auth_sessions (\n\tid VARCHAR(36) NOT NULL, \n\tuser_id INTEGER NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\tplatform VARCHAR(16) NOT NULL, \n\tcreated_at DATETIME NOT NULL, \n\texpires_at DATETIME NOT NULL, \n\trevoked BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tUNIQUE (token_hash)\n)\n\n",
    "CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id)",
    "\nCREATE TABLE user_tags (\n\tid INTEGER NOT NULL, \n\tuser_id INTEGER NOT NULL, \n\tname VARCHAR(24) NOT NULL, \n\tname_key VARCHAR(24) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (user_id, name_key), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)\n\n",
    "CREATE INDEX ix_user_tags_user_id ON user_tags (user_id)",
    "\nCREATE TABLE bookmarks (\n\tid INTEGER NOT NULL, \n\tuser_id INTEGER NOT NULL, \n\tnews_id INTEGER NOT NULL, \n\tsnapshot JSON NOT NULL, \n\tcreated_at DATETIME NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (user_id, news_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tFOREIGN KEY(news_id) REFERENCES news (id)\n)\n\n",
    "CREATE INDEX ix_bookmarks_user_id ON bookmarks (user_id)",
    "CREATE INDEX ix_bookmarks_news_id ON bookmarks (news_id)",
    "\nCREATE TABLE bookmark_tags (\n\tbookmark_id INTEGER NOT NULL, \n\ttag_id INTEGER NOT NULL, \n\tPRIMARY KEY (bookmark_id, tag_id), \n\tFOREIGN KEY(bookmark_id) REFERENCES bookmarks (id) ON DELETE CASCADE, \n\tFOREIGN KEY(tag_id) REFERENCES user_tags (id) ON DELETE CASCADE\n)\n\n",
]


def upgrade():
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade():
    raise RuntimeError("请从升级前备份恢复，不自动删除表")
