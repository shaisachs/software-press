CREATE TABLE jobs (
    id UUID PRIMARY KEY,
    prompt TEXT NOT NULL,

    status TEXT NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    artifact_path TEXT,
    error TEXT
);