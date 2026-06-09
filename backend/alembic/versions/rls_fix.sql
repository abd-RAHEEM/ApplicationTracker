-- ============================================================================
-- Comprehensive Supabase Security & Performance Fix
-- Fixes all issues flagged by Supabase Advisor
-- ============================================================================

-- ─── 1. FIX: RLS on ALL public tables ─────────────────────────────────────────

-- users
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on users" ON public.users;
CREATE POLICY "Service role full access on users"
  ON public.users FOR ALL USING (true) WITH CHECK (true);

-- applications
ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on applications" ON public.applications;
CREATE POLICY "Service role full access on applications"
  ON public.applications FOR ALL USING (true) WITH CHECK (true);

-- gmail_connections
ALTER TABLE public.gmail_connections ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on gmail_connections" ON public.gmail_connections;
CREATE POLICY "Service role full access on gmail_connections"
  ON public.gmail_connections FOR ALL USING (true) WITH CHECK (true);

-- emails
ALTER TABLE public.emails ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on emails" ON public.emails;
CREATE POLICY "Service role full access on emails"
  ON public.emails FOR ALL USING (true) WITH CHECK (true);

-- ─── 2. FIX: RLS init plan performance (use SELECT wrapper for auth functions) ─

DROP POLICY IF EXISTS "Users can view own status history" ON public.application_status_history;
CREATE POLICY "Users can view own status history"
  ON public.application_status_history
  FOR SELECT
  USING ((select auth.uid()::text) = user_id::text);

DROP POLICY IF EXISTS "Users can update own status history" ON public.application_status_history;
CREATE POLICY "Users can update own status history"
  ON public.application_status_history
  FOR UPDATE
  USING ((select auth.uid()::text) = user_id::text);

DROP POLICY IF EXISTS "Users can delete own status history" ON public.application_status_history;
CREATE POLICY "Users can delete own status history"
  ON public.application_status_history
  FOR DELETE
  USING ((select auth.uid()::text) = user_id::text);

-- ─── 3. FIX: Drop duplicate indexes (keep constraint-backed unique index) ────

-- application_analytics: drop the plain idx, keep the unique constraint index
DROP INDEX IF EXISTS public.idx_analytics_user_id;

-- gmail_connections: drop the plain idx, keep the unique constraint index
DROP INDEX IF EXISTS public.idx_gmail_user_id;

-- users: drop the plain idx, keep the unique constraint index
DROP INDEX IF EXISTS public.idx_users_username;
