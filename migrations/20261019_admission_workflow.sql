BEGIN;
ALTER TABLE public.thi_sinh ADD COLUMN IF NOT EXISTS email text;
ALTER TABLE public.nguyen_vong_sinh_vien ADD COLUMN IF NOT EXISTS nguon_ket_qua text;
ALTER TABLE public.nguyen_vong_sinh_vien ADD COLUMN IF NOT EXISTS chot_ket_qua_at timestamp;
ALTER TABLE public.nguyen_vong_sinh_vien ADD COLUMN IF NOT EXISTS cong_bo_at timestamp;
ALTER TABLE public.nguyen_vong_sinh_vien ADD COLUMN IF NOT EXISTS diem_trace jsonb;
CREATE TABLE IF NOT EXISTS public.admission_notification (
 ma_ho_so text PRIMARY KEY REFERENCES public.nguyen_vong_sinh_vien(ma_ho_so),
 email text, status text NOT NULL DEFAULT 'pending', attempts integer NOT NULL DEFAULT 0,
 error text, sent_at timestamp
);
CREATE TABLE IF NOT EXISTS public.admission_score_import (
 digest text PRIMARY KEY, source text NOT NULL, year integer NOT NULL,
 admin_id text NOT NULL REFERENCES public.admin(ma_admin), row_count integer NOT NULL,
 created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE public.admission_notification ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admission_score_import ENABLE ROW LEVEL SECURITY;
-- Legacy messages are deliberately not backfilled as official admissions.
COMMIT;
