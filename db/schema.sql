-- =============================================================================
-- Orbyte GreenReady — Supabase schema (UI spec §9.2)
--
-- Run once in Supabase → SQL Editor, then run db/seed.sql for the demo data.
-- Safe to re-run: every statement is "if not exists" / "or replace", and the
-- tables the WhatsApp + Gmail pipeline already writes to keep their columns:
--   sme_profiles, ingested_documents, activity_audit_log, marketplace_listings
--
-- The FastAPI backend connects with the service-role key, which bypasses RLS
-- and enforces the rules in code. The RLS policies below protect direct
-- browser access (anon/authenticated keys) through Supabase Auth.
-- =============================================================================

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------- helpers
create or replace function public.set_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end $$;

-- =============================================================== companies
-- sme_profiles is used by db/db_manager.py (get_or_create_sme / update_sme_profile).
create table if not exists public.sme_profiles (
  id                     uuid primary key default gen_random_uuid(),
  whatsapp_number        text unique,
  email_address          text unique,
  company_name           text,
  ssm_number             text unique,
  industry               text,
  state                  text,
  wallet_balance_credits integer not null default 0,
  created_at             timestamptz not null default now()
);

alter table public.sme_profiles
  add column if not exists company_type      text,
  add column if not exists company_status    text default 'Active',          -- C01
  add column if not exists incorporated_on   date,                           -- C02
  add column if not exists msic_code         text,
  add column if not exists nature_of_business text,
  add column if not exists size_class        text,                           -- C03 Micro / Small / Medium
  add column if not exists sector_group      text,                           -- C04
  add column if not exists region            text,                           -- C06
  add column if not exists address           text,
  add column if not exists directors         text[] default '{}',
  add column if not exists contact_person    text,
  add column if not exists contact_phone     text,
  add column if not exists contact_email     text,
  add column if not exists lighting_type     text,                           -- onboarding Q1
  add column if not exists aircon_type       text,                           -- onboarding Q2
  add column if not exists aircon_units      integer default 0,
  add column if not exists roof_access       text,                           -- onboarding Q3
  add column if not exists daytime_operation boolean,                        -- onboarding Q4
  add column if not exists pdpa_version      text,
  add column if not exists pdpa_consented_at timestamptz,
  add column if not exists data_retention_months integer default 24,
  add column if not exists updated_at        timestamptz not null default now();

drop trigger if exists trg_sme_profiles_updated on public.sme_profiles;
create trigger trg_sme_profiles_updated before update on public.sme_profiles
  for each row execute function public.set_updated_at();

-- ================================================================ partners
create table if not exists public.partners (
  id               text primary key,                  -- e.g. P-BH, P-SHS
  partner_type     text not null check (partner_type in ('investor', 'supplier')),
  name             text not null,
  unit             text,
  ssm_no           text,
  seda_no          text,                              -- suppliers (V15)
  seda_valid_until date,
  categories       text[] not null default '{}',      -- solar / led / aircon (M01)
  service_area     text[] not null default '{}',      -- states (M01)
  contact_name     text,
  contact_title    text,
  contact_phone    text,
  contact_email    text,
  address          text,
  created_at       timestamptz not null default now()
);

create table if not exists public.partner_criteria (     -- investor "My criteria" (M02)
  partner_id        text primary key references public.partners(id) on delete cascade,
  upgrade           text,
  state             text,
  sector            text,
  capex_band        text,
  min_age_years     integer,
  min_saving_myr    integer,
  max_payback_years numeric(4,1),
  updated_at        timestamptz not null default now()
);

-- =================================================================== users
-- One row per person. auth_user_id links to Supabase Auth when real login is on.
create table if not exists public.app_users (
  id           uuid primary key default gen_random_uuid(),
  auth_user_id uuid unique references auth.users(id) on delete set null,
  email        text not null unique,
  full_name    text not null,
  role         text not null check (role in ('sme_owner', 'sme_staff', 'investor', 'supplier', 'ops')),
  sme_id       uuid references public.sme_profiles(id) on delete cascade,
  partner_id   text references public.partners(id) on delete cascade,
  created_at   timestamptz not null default now(),
  constraint app_users_scope check (
    (role in ('sme_owner', 'sme_staff') and sme_id is not null)
    or (role in ('investor', 'supplier') and partner_id is not null)
    or role = 'ops'
  )
);

-- =================================================================== bills
-- ingested_documents is used by db/db_manager.py and gmail_reader/persistence.py.
create table if not exists public.ingested_documents (
  id             uuid primary key default gen_random_uuid(),
  sme_id         uuid not null references public.sme_profiles(id) on delete cascade,
  source_channel text not null,                       -- WHATSAPP / GMAIL / ECLAIM / UPLOAD
  document_type  text not null default 'UNKNOWN',     -- TNB_BILL / VENDOR_QUOTE / SPAM / UNKNOWN
  storage_path   text not null,
  status         text not null default 'PROCESSING',  -- PROCESSING / COMPLETED / FAILED / NEEDS_HUMAN
  extracted_json jsonb,
  created_at     timestamptz not null default now()
);

alter table public.ingested_documents
  add column if not exists billing_month    date,
  add column if not exists reading_type     text,            -- actual / estimated (V11)
  add column if not exists total_due_myr    numeric(12,2),
  add column if not exists usage_kwh        numeric(12,2),
  add column if not exists checks_passed    integer,
  add column if not exists checks_total     integer,
  add column if not exists charged_myr      numeric(8,2) default 0,   -- Free or RM2.00
  add column if not exists eclaim_claim_id  text,                     -- set when it came from Orbyte eClaim
  add column if not exists submitted_by     uuid references public.app_users(id),
  add column if not exists updated_at       timestamptz not null default now();

create index if not exists idx_ingested_documents_sme on public.ingested_documents (sme_id, created_at desc);
drop trigger if exists trg_ingested_documents_updated on public.ingested_documents;
create trigger trg_ingested_documents_updated before update on public.ingested_documents
  for each row execute function public.set_updated_at();

create table if not exists public.bill_fields (          -- B01–B23 with AI confidence (V12)
  id              bigint generated always as identity primary key,
  document_id     uuid not null references public.ingested_documents(id) on delete cascade,
  field_key       text not null,
  value           text,
  confidence      numeric(5,2),                         -- 0–100; < 85 needs review
  corrected_value text,
  corrected_by    uuid references public.app_users(id),
  corrected_at    timestamptz,
  unique (document_id, field_key)
);

create table if not exists public.bill_checks (          -- V01–V09 (8 rows on screen)
  id          bigint generated always as identity primary key,
  document_id uuid not null references public.ingested_documents(id) on delete cascade,
  rule_id     text not null,
  label       text not null,
  expected    numeric(14,4),
  found       numeric(14,4),
  passed      boolean not null,
  unique (document_id, rule_id)
);

create table if not exists public.bill_insights (        -- B01–B08 insight cards
  id          bigint generated always as identity primary key,
  document_id uuid not null references public.ingested_documents(id) on delete cascade,
  rule_id     text not null,
  label       text not null,
  value       jsonb not null,
  unique (document_id, rule_id)
);

-- ================================================================ upgrades
create table if not exists public.upgrade_options (      -- U01–U09 results
  id               uuid primary key default gen_random_uuid(),
  sme_id           uuid not null references public.sme_profiles(id) on delete cascade,
  document_id      uuid references public.ingested_documents(id) on delete set null,
  upgrade_type     text not null check (upgrade_type in ('solar', 'led', 'aircon')),
  size_label       text not null,                       -- "23.1 kWp", "40 tubes"
  capex_myr        numeric(12,2) not null,
  saving_myr_year  numeric(12,2) not null,
  payback_years    numeric(6,2),
  co2e_t_year      numeric(8,3) not null,
  basis            text not null default 'estimate' check (basis in ('estimate', 'exact')),
  basis_rules      text,                                -- e.g. "U03–U04"
  created_at       timestamptz not null default now()
);
create index if not exists idx_upgrade_options_sme on public.upgrade_options (sme_id);

create table if not exists public.preparation_packs (
  id                uuid primary key default gen_random_uuid(),
  sme_id            uuid not null references public.sme_profiles(id) on delete cascade,
  upgrade_types     text[] not null,
  charged_myr       numeric(8,2) not null default 79,
  pdf_path          text,
  status            text not null default 'draft' check (status in ('draft', 'approved', 'cancelled')),
  approved_by       uuid references public.app_users(id),
  approved_at       timestamptz,
  access_expires_at timestamptz,                         -- 90 days of partner access
  created_at        timestamptz not null default now()
);

-- ================================================================ listings
-- marketplace_listings is used by workflow/nodes.py (node_publish_to_marketplace).
-- Partners can read this table, so it only holds bands and rounded figures.
create sequence if not exists public.listing_code_seq start 872;

create table if not exists public.marketplace_listings (
  id                   uuid primary key default gen_random_uuid(),
  sme_id               uuid not null references public.sme_profiles(id) on delete cascade,
  masked_title         text,
  baseline_kwh         numeric(12,2),
  target_capex_myr     numeric(12,2),
  annual_tco2e_avoided numeric(8,3),
  listing_status       text default 'ACTIVE',
  created_at           timestamptz not null default now()
);

alter table public.marketplace_listings
  add column if not exists listing_code         text unique default ('GR-L-' || lpad(nextval('public.listing_code_seq')::text, 4, '0')),
  add column if not exists pack_id              uuid references public.preparation_packs(id) on delete set null,
  add column if not exists status               text not null default 'live',   -- live / unlisted / expired (M07)
  add column if not exists sector               text,
  add column if not exists state                text,
  add column if not exists size_class           text,
  add column if not exists age_band             text,
  add column if not exists upgrade_types        text[] not null default '{}',
  add column if not exists upgrade_labels       text[] not null default '{}',
  add column if not exists usage_band           text,
  add column if not exists bill_band            text,
  add column if not exists capex_band           text,
  add column if not exists saving_approx_myr    integer,
  add column if not exists payback_approx_years numeric(4,1),
  add column if not exists co2e_approx_t        integer,
  add column if not exists suggested_solar_kwp  numeric(6,1),
  add column if not exists daytime_operation    boolean,
  add column if not exists lighting             text,
  add column if not exists quote_attached       boolean not null default false,
  add column if not exists evidence             jsonb not null default '{}'::jsonb,
  add column if not exists views_investors      integer not null default 0,
  add column if not exists views_suppliers      integer not null default 0,
  add column if not exists approved_by          uuid references public.app_users(id),
  add column if not exists listed_at            timestamptz not null default now(),
  add column if not exists expires_at           timestamptz not null default (now() + interval '90 days'),
  add column if not exists updated_at           timestamptz not null default now();

do $$ begin
  alter table public.marketplace_listings
    add constraint marketplace_listings_status_check check (status in ('live', 'unlisted', 'expired'));
exception when duplicate_object then null; end $$;

create index if not exists idx_listings_board on public.marketplace_listings (status, listed_at desc);
drop trigger if exists trg_listings_updated on public.marketplace_listings;
create trigger trg_listings_updated before update on public.marketplace_listings
  for each row execute function public.set_updated_at();

-- ================================================================ requests
create table if not exists public.connection_requests (
  id             uuid primary key default gen_random_uuid(),
  listing_id     uuid not null references public.marketplace_listings(id) on delete cascade,
  partner_id     text not null references public.partners(id) on delete cascade,
  partner_type   text not null check (partner_type in ('investor', 'supplier')),
  message        text not null default '',
  status         text not null default 'requested' check (status in ('requested', 'accepted', 'declined', 'expired')),
  decline_reason text,
  decided_by     uuid references public.app_users(id),     -- must be the SME owner (C05)
  decided_at     timestamptz,
  created_at     timestamptz not null default now()
);
-- One open or accepted request per partner per listing.
create unique index if not exists uq_open_request
  on public.connection_requests (listing_id, partner_id) where status in ('requested', 'accepted');
create index if not exists idx_requests_partner on public.connection_requests (partner_id, created_at desc);

create table if not exists public.partner_documents (     -- EOI, proposal, firm quotation, signed copy
  id            uuid primary key default gen_random_uuid(),
  request_id    uuid not null references public.connection_requests(id) on delete cascade,
  listing_id    uuid not null references public.marketplace_listings(id) on delete cascade,
  partner_id    text not null references public.partners(id) on delete cascade,
  doc_type      text not null check (doc_type in ('eoi', 'proposal', 'quotation', 'signed')),
  reference     text not null unique,                    -- GR-EOI-2026-0142, SHS-P-26-0318
  status        text not null default 'sent' check (status in ('sent', 'accepted', 'declined', 'signed')),
  content       jsonb not null,                          -- facts GreenReady pre-filled
  field_values  jsonb not null default '{}'::jsonb,      -- the partner's bracketed fields
  pdf_path      text,
  esign_ref     text,                                    -- Orbyte eSign / Documenso envelope
  sent_at       timestamptz not null default now(),
  responded_at  timestamptz
);

-- ============================================================ money (mock)
create table if not exists public.wallet_ledger (         -- Orbyte credit wallet entries
  id          bigint generated always as identity primary key,
  sme_id      uuid not null references public.sme_profiles(id) on delete cascade,
  amount_myr  numeric(10,2) not null,                    -- + credit / top-up, − charge
  entry_type  text not null check (entry_type in ('CREDIT', 'DEBIT', 'TOPUP')),
  reason      text not null,
  reference   text,                                      -- document / pack id
  created_at  timestamptz not null default now()
);
create index if not exists idx_wallet_ledger_sme on public.wallet_ledger (sme_id, created_at desc);

-- security_invoker: the view obeys the caller's RLS instead of the owner's rights.
create or replace view public.wallet_balances with (security_invoker = true) as
  select sme_id, sum(amount_myr)::numeric(10,2) as balance_myr
  from public.wallet_ledger group by sme_id;

create table if not exists public.partner_fees (          -- RM200 per accepted supplier connection
  id          bigint generated always as identity primary key,
  partner_id  text not null references public.partners(id) on delete cascade,
  request_id  uuid not null unique references public.connection_requests(id) on delete cascade,
  listing_id  uuid not null references public.marketplace_listings(id) on delete cascade,
  amount_myr  numeric(10,2) not null default 200,
  invoice_month date not null default date_trunc('month', now())::date,
  created_at  timestamptz not null default now()
);

-- M04: supplier proposals sent this ISO week.
create or replace view public.supplier_requests_this_week with (security_invoker = true) as
  select partner_id, count(*)::int as used
  from public.connection_requests
  where partner_type = 'supplier' and created_at >= date_trunc('week', now())
  group by partner_id;

-- =================================================================== audit
-- activity_audit_log is used by db/db_manager.py (log_audit_event).
create table if not exists public.activity_audit_log (
  id          bigint generated always as identity primary key,
  sme_id      uuid references public.sme_profiles(id) on delete cascade,
  audit_id    text,
  action_type text not null,
  actor_role  text not null default 'SYSTEM',
  metadata    jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);

alter table public.activity_audit_log
  add column if not exists actor_name  text,
  add column if not exists partner_id  text references public.partners(id) on delete set null,
  add column if not exists object_type text,         -- Bill / Pack / Listing / Request / Company
  add column if not exists object_ref  text;         -- e.g. GR-L-0871
create index if not exists idx_audit_sme on public.activity_audit_log (sme_id, created_at desc);

-- ============================================================== parameters
create table if not exists public.parameters (            -- P01–P40, read-only in the demo
  code       text primary key,
  name       text not null,
  value      numeric not null,
  unit       text,
  source     text,
  updated_at timestamptz not null default now()
);

-- Synthetic SSM register for the sign-up lookup (replace with a real SSM provider).
create table if not exists public.ssm_registry_demo (
  ssm_no        text primary key check (ssm_no ~ '^[0-9]{12}$'),
  company_name  text not null,
  company_type  text not null,
  status        text not null,
  incorporated_on date not null,
  msic_code     text not null,
  nature        text not null,
  state         text not null,
  directors     text[] not null,
  employees     integer not null,
  revenue_myr   numeric(14,2) not null
);

-- ================================================================ storage
-- raw_documents: bill files. Public because workflow/nodes.py reads files by
-- public URL; switch to signed URLs before using real customer bills.
insert into storage.buckets (id, name, public)
values ('raw_documents', 'raw_documents', true)
on conflict (id) do nothing;

-- documents: generated Preparation Packs, EOIs, proposals (private).
insert into storage.buckets (id, name, public)
values ('documents', 'documents', false)
on conflict (id) do nothing;

-- ========================================================= row-level security
create or replace function public.current_app_user() returns public.app_users
language sql stable security definer set search_path = public as $$
  select * from public.app_users where auth_user_id = auth.uid() limit 1
$$;

create or replace function public.current_sme_id() returns uuid
language sql stable security definer set search_path = public as $$
  select sme_id from public.app_users where auth_user_id = auth.uid() limit 1
$$;

create or replace function public.current_partner_id() returns text
language sql stable security definer set search_path = public as $$
  select partner_id from public.app_users where auth_user_id = auth.uid() limit 1
$$;

create or replace function public.current_role_name() returns text
language sql stable security definer set search_path = public as $$
  select role from public.app_users where auth_user_id = auth.uid() limit 1
$$;

-- M05: company identity for a partner whose request the owner accepted.
create or replace function public.listing_identity(p_listing uuid)
returns table (company_name text, reg_no text, address text, contact_person text, contact_phone text, contact_email text)
language sql stable security definer set search_path = public as $$
  select s.company_name, s.ssm_number, s.address, s.contact_person, s.contact_phone, s.contact_email
  from public.marketplace_listings l
  join public.sme_profiles s on s.id = l.sme_id
  where l.id = p_listing
    and (
      s.id = public.current_sme_id()
      or exists (
        select 1 from public.connection_requests r
        where r.listing_id = l.id and r.partner_id = public.current_partner_id() and r.status = 'accepted'
      )
    )
$$;

do $$
declare t text;
begin
  foreach t in array array[
    'sme_profiles', 'partners', 'partner_criteria', 'app_users', 'ingested_documents', 'bill_fields',
    'bill_checks', 'bill_insights', 'upgrade_options', 'preparation_packs', 'marketplace_listings',
    'connection_requests', 'partner_documents', 'wallet_ledger', 'partner_fees', 'activity_audit_log',
    'parameters', 'ssm_registry_demo'
  ] loop
    execute format('alter table public.%I enable row level security', t);
  end loop;
end $$;

-- Drop-and-create so the script stays re-runnable.
do $$
declare p record;
begin
  for p in select policyname, tablename from pg_policies where schemaname = 'public' and policyname like 'gr_%' loop
    execute format('drop policy %I on public.%I', p.policyname, p.tablename);
  end loop;
end $$;

-- SMEs: only their own company (spec §9.2 RLS).
create policy gr_sme_own on public.sme_profiles for select to authenticated
  using (id = public.current_sme_id() or public.current_role_name() = 'ops');
create policy gr_sme_owner_update on public.sme_profiles for update to authenticated
  using (id = public.current_sme_id() and public.current_role_name() = 'sme_owner');

create policy gr_users_self on public.app_users for select to authenticated
  using (auth_user_id = auth.uid() or sme_id = public.current_sme_id() or public.current_role_name() = 'ops');

create policy gr_docs_own on public.ingested_documents for select to authenticated
  using (sme_id = public.current_sme_id() or public.current_role_name() = 'ops');
create policy gr_fields_own on public.bill_fields for all to authenticated
  using (exists (select 1 from public.ingested_documents d where d.id = document_id and d.sme_id = public.current_sme_id()));
create policy gr_checks_own on public.bill_checks for select to authenticated
  using (exists (select 1 from public.ingested_documents d where d.id = document_id and d.sme_id = public.current_sme_id()));
create policy gr_insights_own on public.bill_insights for select to authenticated
  using (exists (select 1 from public.ingested_documents d where d.id = document_id and d.sme_id = public.current_sme_id()));
create policy gr_upgrades_own on public.upgrade_options for select to authenticated
  using (sme_id = public.current_sme_id());
create policy gr_packs_own on public.preparation_packs for select to authenticated
  using (sme_id = public.current_sme_id());
create policy gr_wallet_own on public.wallet_ledger for select to authenticated
  using (sme_id = public.current_sme_id());

-- Listings: owner sees its own; partners see live anonymised cards only.
create policy gr_listings_owner on public.marketplace_listings for select to authenticated
  using (sme_id = public.current_sme_id() or public.current_role_name() = 'ops');
create policy gr_listings_partners on public.marketplace_listings for select to authenticated
  using (status = 'live' and public.current_partner_id() is not null);

-- Requests: partner sees and creates its own; SME owner of the listing decides.
create policy gr_requests_partner_read on public.connection_requests for select to authenticated
  using (partner_id = public.current_partner_id());
create policy gr_requests_partner_insert on public.connection_requests for insert to authenticated
  with check (partner_id = public.current_partner_id() and status = 'requested');
create policy gr_requests_sme_read on public.connection_requests for select to authenticated
  using (exists (select 1 from public.marketplace_listings l where l.id = listing_id and l.sme_id = public.current_sme_id()));
create policy gr_requests_owner_decide on public.connection_requests for update to authenticated
  using (
    public.current_role_name() = 'sme_owner'
    and exists (select 1 from public.marketplace_listings l where l.id = listing_id and l.sme_id = public.current_sme_id())
  );

create policy gr_pdocs_partner on public.partner_documents for select to authenticated
  using (partner_id = public.current_partner_id());
create policy gr_pdocs_sme on public.partner_documents for select to authenticated
  using (exists (select 1 from public.marketplace_listings l where l.id = listing_id and l.sme_id = public.current_sme_id()));

create policy gr_partners_read on public.partners for select to authenticated using (true);
create policy gr_criteria_own on public.partner_criteria for all to authenticated
  using (partner_id = public.current_partner_id()) with check (partner_id = public.current_partner_id());
create policy gr_fees_own on public.partner_fees for select to authenticated
  using (partner_id = public.current_partner_id());   -- partner fees are never shown to SMEs

create policy gr_audit_read on public.activity_audit_log for select to authenticated
  using (sme_id = public.current_sme_id() or partner_id = public.current_partner_id() or public.current_role_name() = 'ops');

create policy gr_parameters_read on public.parameters for select to authenticated using (true);
create policy gr_ssm_read on public.ssm_registry_demo for select to anon, authenticated using (true);
