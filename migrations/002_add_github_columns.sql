-- Add columns for GitHub issues and pull requests.
ALTER TABLE jobs ADD COLUMN issue_number INTEGER;
ALTER TABLE jobs ADD COLUMN pr_number INTEGER;
