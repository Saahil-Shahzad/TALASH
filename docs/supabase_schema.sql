-- TALASH base schema for Supabase Postgres
-- Run this file in Supabase SQL Editor.

create table if not exists public.candidates (
  id bigserial primary key,
  source_file varchar(255) not null unique,
  full_name varchar(255),
  email varchar(255),
  phone varchar(50),
  location varchar(255),
  skills_csv text,
  raw_text text not null,
  parsed_json text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.analyses (
  id bigserial primary key,
  candidate_id bigint not null references public.candidates(id) on delete cascade,
  analysis_type varchar(100) not null,
  result_json text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_analyses_candidate_id on public.analyses(candidate_id);
