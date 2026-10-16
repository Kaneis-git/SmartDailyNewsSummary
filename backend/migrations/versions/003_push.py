from alembic import op

revision = "003_push"
down_revision = "002_users"
branch_labels = None
depends_on = None
STATEMENTS = [
    "\nCREATE TABLE devices (\n\tid VARCHAR(36) NOT NULL, \n\tuser_id INTEGER NOT NULL, \n\tsession_id VARCHAR(36) NOT NULL, \n\tinstallation_id VARCHAR(36) NOT NULL, \n\tprovider VARCHAR(20) NOT NULL, \n\tregistration_id TEXT NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\tenabled BOOLEAN NOT NULL, \n\tupdated_at DATETIME NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (user_id, installation_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tFOREIGN KEY(session_id) REFERENCES auth_sessions (id) ON DELETE CASCADE\n)\n\n",
    "CREATE INDEX ix_devices_token_hash ON devices (token_hash)",
    "CREATE INDEX ix_devices_user_id ON devices (user_id)",
    "\nCREATE TABLE notification_deliveries (\n\tid VARCHAR(36) NOT NULL, \n\tdevice_id VARCHAR(36) NOT NULL, \n\tuser_id INTEGER NOT NULL, \n\treport_id INTEGER NOT NULL, \n\treport_date DATE NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tattempts INTEGER NOT NULL, \n\tnext_attempt_at DATETIME NOT NULL, \n\tcreated_at DATETIME NOT NULL, \n\tfinished_at DATETIME, \n\treceipt VARCHAR(200), \n\tmessage TEXT NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (device_id, report_date), \n\tFOREIGN KEY(device_id) REFERENCES devices (id) ON DELETE CASCADE, \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tFOREIGN KEY(report_id) REFERENCES daily_reports (id)\n)\n\n",
    "CREATE INDEX ix_notification_deliveries_device_id ON notification_deliveries (device_id)",
    "CREATE INDEX ix_notification_deliveries_status ON notification_deliveries (status)",
    "CREATE INDEX ix_notification_deliveries_user_id ON notification_deliveries (user_id)",
]


def upgrade():
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade():
    raise RuntimeError("请从升级前备份恢复，不自动删除表")
