-- Upgrade installations that used the earlier separate candidate_account draft.
BEGIN;
ALTER TABLE public.thi_sinh ADD COLUMN IF NOT EXISTS password text;
DO $$ BEGIN
  IF to_regclass('public.candidate_account') IS NOT NULL THEN
    UPDATE public.thi_sinh AS student
      SET password = account.password_hash
      FROM public.candidate_account AS account
      WHERE student.cccd = account.cccd AND student.password IS NULL;
  END IF;
END $$;
-- Preserve the old table for review/backup. Application code no longer uses it.
COMMENT ON COLUMN public.thi_sinh.password IS 'Salted PBKDF2 hash, never plaintext';
COMMIT;
