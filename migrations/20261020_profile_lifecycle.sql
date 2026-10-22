-- Review before applying to a shared database. Does not infer results from free text.
BEGIN;
DO $$ BEGIN
  CREATE TYPE public.trang_thai_ho_so AS ENUM ('cho','hop_le','tu_choi','dang_xu_ly','do','truot');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
ALTER TABLE public.nguyen_vong_sinh_vien ALTER COLUMN trang_thai DROP DEFAULT;
ALTER TABLE public.nguyen_vong_sinh_vien ALTER COLUMN trang_thai TYPE public.trang_thai_ho_so
  USING trang_thai::text::public.trang_thai_ho_so;
ALTER TABLE public.nguyen_vong_sinh_vien ALTER COLUMN trang_thai SET DEFAULT 'cho'::public.trang_thai_ho_so;
-- Preserve explicit decisions from the previous draft if that column exists.
-- Keep its physical column as a backup; application code no longer reads/writes it.
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public'
    AND table_name='nguyen_vong_sinh_vien' AND column_name='ket_qua_xet_tuyen') THEN
    UPDATE public.nguyen_vong_sinh_vien SET trang_thai = CASE ket_qua_xet_tuyen
      WHEN 'trung_tuyen' THEN 'do'::public.trang_thai_ho_so
      ELSE 'truot'::public.trang_thai_ho_so END
    WHERE ket_qua_xet_tuyen IN ('trung_tuyen','khong_trung_tuyen')
      AND chot_ket_qua_at IS NOT NULL AND trang_thai IN ('hop_le','dang_xu_ly');
  END IF;
END $$;
COMMIT;
