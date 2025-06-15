-- Setup Supabase schema for California Legal Forms with Open Source Embeddings
-- This script creates tables compatible with sentence-transformers (384 dimensions)

-- Enable the pgvector extension
create extension if not exists vector;

-- Drop tables if they exist (to allow rerunning the script)
drop table if exists documents;
drop table if exists crawled_pages;
drop table if exists code_examples;
drop table if exists sources;

-- Create the sources table
create table sources (
    source_id text primary key,
    summary text,
    total_word_count integer default 0,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create the documents table (for our comprehensive crawler)
create table documents (
    id bigserial primary key,
    url varchar not null,
    chunk_number integer not null,
    content text not null,
    metadata jsonb not null default '{}'::jsonb,
    embedding vector(384),  -- sentence-transformers/all-MiniLM-L6-v2 embeddings are 384 dimensions
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    
    -- Add a unique constraint to prevent duplicate chunks for the same URL
    unique(url, chunk_number)
);

-- Create the crawled_pages table (for MCP server compatibility)
create table crawled_pages (
    id bigserial primary key,
    url varchar not null,
    chunk_number integer not null,
    content text not null,
    metadata jsonb not null default '{}'::jsonb,
    source_id text not null,
    embedding vector(384),  -- Changed to 384 for open source embeddings
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    
    -- Add a unique constraint to prevent duplicate chunks for the same URL
    unique(url, chunk_number),
    
    -- Add foreign key constraint to sources table
    foreign key (source_id) references sources(source_id)
);

-- Create indexes for better vector similarity search performance
create index on documents using ivfflat (embedding vector_cosine_ops);
create index on crawled_pages using ivfflat (embedding vector_cosine_ops);

-- Create indexes on metadata for faster filtering
create index idx_documents_metadata on documents using gin (metadata);
create index idx_crawled_pages_metadata on crawled_pages using gin (metadata);

-- Create indexes on source_id for faster filtering
CREATE INDEX idx_crawled_pages_source_id ON crawled_pages (source_id);

-- Create a function to search documents (for our comprehensive crawler)
create or replace function match_documents (
  query_embedding vector(384),
  match_count int default 10,
  filter jsonb DEFAULT '{}'::jsonb
) returns table (
  id bigint,
  url varchar,
  chunk_number integer,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
#variable_conflict use_column
begin
  return query
  select
    id,
    url,
    chunk_number,
    content,
    metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where metadata @> filter
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Create a function to search for crawled pages (for MCP server compatibility)
create or replace function match_crawled_pages (
  query_embedding vector(384),
  match_count int default 10,
  filter jsonb DEFAULT '{}'::jsonb,
  source_filter text DEFAULT NULL
) returns table (
  id bigint,
  url varchar,
  chunk_number integer,
  content text,
  metadata jsonb,
  source_id text,
  similarity float
)
language plpgsql
as $$
#variable_conflict use_column
begin
  return query
  select
    id,
    url,
    chunk_number,
    content,
    metadata,
    source_id,
    1 - (crawled_pages.embedding <=> query_embedding) as similarity
  from crawled_pages
  where metadata @> filter
    AND (source_filter IS NULL OR source_id = source_filter)
  order by crawled_pages.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Enable RLS on all tables
alter table documents enable row level security;
alter table crawled_pages enable row level security;
alter table sources enable row level security;

-- Create policies that allow public read access
create policy "Allow public read access to documents"
  on documents
  for select
  to public
  using (true);

create policy "Allow public read access to crawled_pages"
  on crawled_pages
  for select
  to public
  using (true);

create policy "Allow public read access to sources"
  on sources
  for select
  to public
  using (true);

-- Create policies for insert access (needed for our crawler)
create policy "Allow public insert access to documents"
  on documents
  for insert
  to public
  with check (true);

create policy "Allow public insert access to crawled_pages"
  on crawled_pages
  for insert
  to public
  with check (true);

create policy "Allow public insert access to sources"
  on sources
  for insert
  to public
  with check (true);

-- Create policies for update access
create policy "Allow public update access to sources"
  on sources
  for update
  to public
  using (true);

-- Insert a test record to verify everything works
INSERT INTO sources (source_id, summary, total_word_count) 
VALUES ('test', 'Test source for California Legal Forms', 0)
ON CONFLICT (source_id) DO NOTHING; 