-- Additive migration for the existing Freedom PostgreSQL database.
-- Run explicitly with python -m app.migrate; never imports/replaces store data.
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS fulfillment_method varchar(20) NOT NULL DEFAULT 'delivery';
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS recipient_email varchar(190);
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS pickup_start timestamptz;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS pickup_end timestamptz;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS checkout_key varchar(64);
CREATE UNIQUE INDEX IF NOT EXISTS orders_user_checkout_key ON public.orders(user_id, checkout_key);
ALTER TABLE public.orders DROP CONSTRAINT IF EXISTS orders_status_check;
ALTER TABLE public.orders ADD CONSTRAINT orders_status_check CHECK
  (status IN ('pending','confirmed','packing','shipping','delivered','failed','cancelled','returned','preparing','shipped'));
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='orders_fulfillment_check' AND conrelid='public.orders'::regclass) THEN
    ALTER TABLE public.orders ADD CONSTRAINT orders_fulfillment_check CHECK
      ((fulfillment_method='delivery' AND pickup_start IS NULL AND pickup_end IS NULL) OR
       (fulfillment_method='pickup' AND recipient_email IS NOT NULL AND pickup_start IS NOT NULL AND pickup_end>pickup_start));
  END IF;
END $$;
