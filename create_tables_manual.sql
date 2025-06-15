-- California Legal Forms Database Schema
-- Modified for open source embeddings (384 dimensions)
-- Run this in your Supabase SQL Editor

-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop tables if they exist (to allow rerunning the script)
DROP TABLE IF EXISTS crawled_pages;
DROP TABLE IF EXISTS sources;

-- Create the sources table
CREATE TABLE sources (
    source_id TEXT PRIMARY KEY,
    summary TEXT,
    total_word_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create the crawled_pages table for legal forms
CREATE TABLE crawled_pages (
    id BIGSERIAL PRIMARY KEY,
    url VARCHAR NOT NULL,
    chunk_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_id TEXT NOT NULL,
    embedding VECTOR(384),  -- Open source embeddings are 384 dimensions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    
    -- Add a unique constraint to prevent duplicate chunks for the same URL
    UNIQUE(url, chunk_number),
    
    -- Add foreign key constraint to sources table
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- Create an index for better vector similarity search performance
CREATE INDEX ON crawled_pages USING ivfflat (embedding vector_cosine_ops);

-- Create an index on metadata for faster filtering
CREATE INDEX idx_crawled_pages_metadata ON crawled_pages USING gin (metadata);

-- Create an index on source_id for faster filtering
CREATE INDEX idx_crawled_pages_source_id ON crawled_pages (source_id);

-- Create a function to search for legal forms
CREATE OR REPLACE FUNCTION match_crawled_pages (
  query_embedding VECTOR(384),
  match_count INT DEFAULT 10,
  filter JSONB DEFAULT '{}'::jsonb,
  source_filter TEXT DEFAULT NULL
) RETURNS TABLE (
  id BIGINT,
  url VARCHAR,
  chunk_number INTEGER,
  content TEXT,
  metadata JSONB,
  source_id TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
#variable_conflict use_column
BEGIN
  RETURN QUERY
  SELECT
    id,
    url,
    chunk_number,
    content,
    metadata,
    source_id,
    1 - (crawled_pages.embedding <=> query_embedding) AS similarity
  FROM crawled_pages
  WHERE metadata @> filter
    AND (source_filter IS NULL OR source_id = source_filter)
  ORDER BY crawled_pages.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Enable RLS on the crawled_pages table
ALTER TABLE crawled_pages ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows anyone to read crawled_pages
CREATE POLICY "Allow public read access to crawled_pages"
  ON crawled_pages
  FOR SELECT
  TO public
  USING (true);

-- Enable RLS on the sources table
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows anyone to read sources
CREATE POLICY "Allow public read access to sources"
  ON sources
  FOR SELECT
  TO public
  USING (true);

-- Insert the default source for California legal forms
INSERT INTO sources (source_id, summary, total_word_count) 
VALUES ('california_courts_comprehensive', 'California Courts comprehensive legal forms database with 26 popular topics', 0)
ON CONFLICT (source_id) DO NOTHING;

-- Verify the setup
SELECT 'Setup completed successfully!' as status;
SELECT 'Tables created:' as info;
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('sources', 'crawled_pages');
SELECT 'Default source inserted:' as info;
SELECT source_id, summary FROM sources WHERE source_id = 'california_courts_comprehensive'; 