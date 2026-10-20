CREATE TABLE snapshots (name TEXT PRIMARY KEY, payload TEXT NOT NULL);
--> statement-breakpoint
CREATE TABLE reviews (scope TEXT NOT NULL, review_id TEXT NOT NULL, review_text TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(scope,review_id));
--> statement-breakpoint
CREATE TABLE issue_aggregates (scope TEXT NOT NULL, issue_id TEXT NOT NULL, severity_sum INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(scope,issue_id));
--> statement-breakpoint
CREATE TABLE recommendations (scope TEXT NOT NULL, issue_id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(scope,issue_id));
--> statement-breakpoint
CREATE TABLE call_evidence (request_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
