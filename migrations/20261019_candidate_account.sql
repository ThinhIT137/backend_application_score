-- Candidate credentials live directly on thi_sinh. Existing rows can remain without a login.
BEGIN;
ALTER TABLE public.thi_sinh ADD COLUMN IF NOT EXISTS password text;
COMMIT;
