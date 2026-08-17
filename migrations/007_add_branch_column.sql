-- Add the optional requested repo branch for a job. When omitted, the agent
-- assumes the repo's default branch.
ALTER TABLE jobs ADD COLUMN branch TEXT;
