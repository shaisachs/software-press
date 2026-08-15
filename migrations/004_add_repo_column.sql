-- Add the target repository (org/repo) for a job.
ALTER TABLE jobs ADD COLUMN repo TEXT;
