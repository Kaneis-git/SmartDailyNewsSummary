-- v0.3.0 SQLite reference only. Use backend/migrations for upgrades.

PRAGMA foreign_keys=ON;

CREATE TABLE auth_rates (
	"key" VARCHAR(64) NOT NULL, 
	window INTEGER NOT NULL, 
	count INTEGER NOT NULL, 
	PRIMARY KEY ("key")
);

CREATE TABLE daily_reports (
	id INTEGER NOT NULL, 
	report_date DATE NOT NULL, 
	window_start DATETIME NOT NULL, 
	window_end DATETIME NOT NULL, 
	generated_at DATETIME NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	coverage JSON NOT NULL, 
	source_results JSON NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (report_date)
);

CREATE TABLE job_runs (
	id VARCHAR(36) NOT NULL, 
	report_date DATE NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	active_slot INTEGER, 
	created_at DATETIME NOT NULL, 
	started_at DATETIME, 
	finished_at DATETIME, 
	message TEXT NOT NULL, 
	source_results JSON NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (active_slot)
);

CREATE INDEX ix_job_runs_report_date ON job_runs (report_date);

CREATE TABLE runtime_state (
	"key" VARCHAR(80) NOT NULL, 
	value TEXT NOT NULL, 
	PRIMARY KEY ("key")
);

CREATE TABLE sources (
	id VARCHAR(80) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	feed_url TEXT NOT NULL, 
	region_hint VARCHAR(20) NOT NULL, 
	category_hint VARCHAR(20) NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE users (
	id INTEGER NOT NULL, 
	username VARCHAR(32) NOT NULL, 
	display_name VARCHAR(60) NOT NULL, 
	password_hash TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username)
);

CREATE TABLE auth_sessions (
	id VARCHAR(36) NOT NULL, 
	user_id INTEGER NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	platform VARCHAR(16) NOT NULL, 
	created_at DATETIME NOT NULL, 
	expires_at DATETIME NOT NULL, 
	revoked BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (token_hash)
);

CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id);

CREATE TABLE news (
	id INTEGER NOT NULL, 
	source_id VARCHAR(80) NOT NULL, 
	title TEXT NOT NULL, 
	url TEXT NOT NULL, 
	url_hash VARCHAR(64) NOT NULL, 
	text_excerpt TEXT NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	published_at DATETIME NOT NULL, 
	fetched_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_id) REFERENCES sources (id), 
	UNIQUE (url_hash)
);

CREATE INDEX ix_news_published_at ON news (published_at);

CREATE TABLE user_tags (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(24) NOT NULL, 
	name_key VARCHAR(24) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id, name_key), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_user_tags_user_id ON user_tags (user_id);

CREATE TABLE bookmarks (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	news_id INTEGER NOT NULL, 
	snapshot JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id, news_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(news_id) REFERENCES news (id)
);

CREATE INDEX ix_bookmarks_news_id ON bookmarks (news_id);

CREATE INDEX ix_bookmarks_user_id ON bookmarks (user_id);

CREATE TABLE devices (
	id VARCHAR(36) NOT NULL, 
	user_id INTEGER NOT NULL, 
	session_id VARCHAR(36) NOT NULL, 
	installation_id VARCHAR(36) NOT NULL, 
	provider VARCHAR(20) NOT NULL, 
	registration_id TEXT NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id, installation_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(session_id) REFERENCES auth_sessions (id) ON DELETE CASCADE
);

CREATE INDEX ix_devices_token_hash ON devices (token_hash);

CREATE INDEX ix_devices_user_id ON devices (user_id);

CREATE TABLE news_analyses (
	id INTEGER NOT NULL, 
	news_id INTEGER NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	model VARCHAR(200) NOT NULL, 
	prompt_version VARCHAR(80) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	payload JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (news_id, content_hash, model, prompt_version), 
	FOREIGN KEY(news_id) REFERENCES news (id)
);

CREATE INDEX ix_news_analyses_news_id ON news_analyses (news_id);

CREATE TABLE bookmark_tags (
	bookmark_id INTEGER NOT NULL, 
	tag_id INTEGER NOT NULL, 
	PRIMARY KEY (bookmark_id, tag_id), 
	FOREIGN KEY(bookmark_id) REFERENCES bookmarks (id) ON DELETE CASCADE, 
	FOREIGN KEY(tag_id) REFERENCES user_tags (id) ON DELETE CASCADE
);

CREATE TABLE notification_deliveries (
	id VARCHAR(36) NOT NULL, 
	device_id VARCHAR(36) NOT NULL, 
	user_id INTEGER NOT NULL, 
	report_id INTEGER NOT NULL, 
	report_date DATE NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	attempts INTEGER NOT NULL, 
	next_attempt_at DATETIME NOT NULL, 
	created_at DATETIME NOT NULL, 
	finished_at DATETIME, 
	receipt VARCHAR(200), 
	message TEXT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (device_id, report_date), 
	FOREIGN KEY(device_id) REFERENCES devices (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(report_id) REFERENCES daily_reports (id)
);

CREATE INDEX ix_notification_deliveries_device_id ON notification_deliveries (device_id);

CREATE INDEX ix_notification_deliveries_status ON notification_deliveries (status);

CREATE INDEX ix_notification_deliveries_user_id ON notification_deliveries (user_id);

CREATE TABLE report_items (
	id INTEGER NOT NULL, 
	report_id INTEGER NOT NULL, 
	news_id INTEGER NOT NULL, 
	analysis_id INTEGER NOT NULL, 
	position INTEGER NOT NULL, 
	region VARCHAR(20) NOT NULL, 
	category VARCHAR(20) NOT NULL, 
	snapshot JSON NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (report_id, news_id), 
	FOREIGN KEY(report_id) REFERENCES daily_reports (id), 
	FOREIGN KEY(news_id) REFERENCES news (id), 
	FOREIGN KEY(analysis_id) REFERENCES news_analyses (id)
);

CREATE INDEX ix_report_items_report_id ON report_items (report_id);
