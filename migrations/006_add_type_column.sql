-- Add an explicit job type (adHoc / issueResolver / issueArchitect) and
-- backfill existing rows based on what they carry.
ALTER TABLE jobs ADD COLUMN type TEXT;

UPDATE jobs SET type = 'issueResolver'
WHERE type IS NULL AND issue_number IS NOT NULL;

UPDATE jobs SET type = 'adHoc'
WHERE type IS NULL AND prompt IS NOT NULL;

UPDATE jobs SET type = 'adHoc'
WHERE type IS NULL;

ALTER TABLE jobs ALTER COLUMN type SET NOT NULL;
