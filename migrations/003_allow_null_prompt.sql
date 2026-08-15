-- Allow prompt to be NULL, since issue jobs carry no ad hoc prompt.
ALTER TABLE jobs ALTER COLUMN prompt DROP NOT NULL;
