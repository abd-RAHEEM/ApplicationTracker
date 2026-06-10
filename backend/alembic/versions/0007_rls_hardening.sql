-- ============================================================================
-- SQL: Hardening database row-level security (RLS) policies
-- Resolves permissive public RLS, missing RLS, and performance warnings
-- ============================================================================

-- ─── 1. HARDEN EXISTING RLS TABLES (Restrict Service Role policies) ──────────

-- Table: public.users
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on users" ON public.users;
CREATE POLICY "Service role full access on users"
  ON public.users FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Users can view own profile" ON public.users;
CREATE POLICY "Users can view own profile"
  ON public.users FOR SELECT TO authenticated USING ((select auth.uid()) = id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.users;
CREATE POLICY "Users can update own profile"
  ON public.users FOR UPDATE TO authenticated USING ((select auth.uid()) = id) WITH CHECK ((select auth.uid()) = id);


-- Table: public.applications
ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on applications" ON public.applications;
CREATE POLICY "Service role full access on applications"
  ON public.applications FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Users can view own applications" ON public.applications;
CREATE POLICY "Users can view own applications"
  ON public.applications FOR SELECT TO authenticated USING ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can insert own applications" ON public.applications;
CREATE POLICY "Users can insert own applications"
  ON public.applications FOR INSERT TO authenticated WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can update own applications" ON public.applications;
CREATE POLICY "Users can update own applications"
  ON public.applications FOR UPDATE TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can delete own applications" ON public.applications;
CREATE POLICY "Users can delete own applications"
  ON public.applications FOR DELETE TO authenticated USING ((select auth.uid()) = user_id);


-- Table: public.gmail_connections
ALTER TABLE public.gmail_connections ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on gmail_connections" ON public.gmail_connections;
CREATE POLICY "Service role full access on gmail_connections"
  ON public.gmail_connections FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Users can view own gmail_connections" ON public.gmail_connections;
CREATE POLICY "Users can view own gmail_connections"
  ON public.gmail_connections FOR SELECT TO authenticated USING ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can insert own gmail_connections" ON public.gmail_connections;
CREATE POLICY "Users can insert own gmail_connections"
  ON public.gmail_connections FOR INSERT TO authenticated WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can update own gmail_connections" ON public.gmail_connections;
CREATE POLICY "Users can update own gmail_connections"
  ON public.gmail_connections FOR UPDATE TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can delete own gmail_connections" ON public.gmail_connections;
CREATE POLICY "Users can delete own gmail_connections"
  ON public.gmail_connections FOR DELETE TO authenticated USING ((select auth.uid()) = user_id);


-- Table: public.emails
ALTER TABLE public.emails ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on emails" ON public.emails;
CREATE POLICY "Service role full access on emails"
  ON public.emails FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Users can view own emails" ON public.emails;
CREATE POLICY "Users can view own emails"
  ON public.emails FOR SELECT TO authenticated USING ((select auth.uid()) = user_id);


-- ─── 2. ENABLE RLS & CREATE POLICIES FOR UNPROTECTED TABLES ─────────────────

-- Table: public.application_analytics
ALTER TABLE public.application_analytics ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on application_analytics" ON public.application_analytics;
CREATE POLICY "Service role full access on application_analytics"
  ON public.application_analytics FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Users can view own analytics" ON public.application_analytics;
CREATE POLICY "Users can view own analytics"
  ON public.application_analytics FOR SELECT TO authenticated USING ((select auth.uid()) = user_id);


-- Table: public.deleted_applications
ALTER TABLE public.deleted_applications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on deleted_applications" ON public.deleted_applications;
CREATE POLICY "Service role full access on deleted_applications"
  ON public.deleted_applications FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Users can view own deleted_applications" ON public.deleted_applications;
CREATE POLICY "Users can view own deleted_applications"
  ON public.deleted_applications FOR SELECT TO authenticated USING ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can update own deleted_applications" ON public.deleted_applications;
CREATE POLICY "Users can update own deleted_applications"
  ON public.deleted_applications FOR UPDATE TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can delete own deleted_applications" ON public.deleted_applications;
CREATE POLICY "Users can delete own deleted_applications"
  ON public.deleted_applications FOR DELETE TO authenticated USING ((select auth.uid()) = user_id);


-- Table: public.sync_logs
ALTER TABLE public.sync_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on sync_logs" ON public.sync_logs;
CREATE POLICY "Service role full access on sync_logs"
  ON public.sync_logs FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Users can view own sync_logs" ON public.sync_logs;
CREATE POLICY "Users can view own sync_logs"
  ON public.sync_logs FOR SELECT TO authenticated USING ((select auth.uid()) = user_id);


-- Table: public.user_sessions
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on user_sessions" ON public.user_sessions;
CREATE POLICY "Service role full access on user_sessions"
  ON public.user_sessions FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Users can view own user_sessions" ON public.user_sessions;
CREATE POLICY "Users can view own user_sessions"
  ON public.user_sessions FOR SELECT TO authenticated USING ((select auth.uid()) = user_id);


-- Table: public.password_reset_tokens
ALTER TABLE public.password_reset_tokens ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on password_reset_tokens" ON public.password_reset_tokens;
CREATE POLICY "Service role full access on password_reset_tokens"
  ON public.password_reset_tokens FOR ALL TO service_role USING (true) WITH CHECK (true);


-- Table: public.alembic_version
ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access on alembic_version" ON public.alembic_version;
CREATE POLICY "Service role full access on alembic_version"
  ON public.alembic_version FOR ALL TO service_role USING (true) WITH CHECK (true);


-- ─── 3. OPTIMIZE RLS PERFORMANCE (Auth RLS InitPlan Optimization) ─────────────

-- Table: public.application_status_history
DROP POLICY IF EXISTS "Users can view own status history" ON public.application_status_history;
CREATE POLICY "Users can view own status history"
  ON public.application_status_history FOR SELECT TO authenticated USING ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can insert own status history" ON public.application_status_history;
CREATE POLICY "Users can insert own status history"
  ON public.application_status_history FOR INSERT TO authenticated WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can update own status history" ON public.application_status_history;
CREATE POLICY "Users can update own status history"
  ON public.application_status_history FOR UPDATE TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can delete own status history" ON public.application_status_history;
CREATE POLICY "Users can delete own status history"
  ON public.application_status_history FOR DELETE TO authenticated USING ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Service role bypass" ON public.application_status_history;
DROP POLICY IF EXISTS "Service role full access on status history" ON public.application_status_history;
CREATE POLICY "Service role full access on status history"
  ON public.application_status_history FOR ALL TO service_role USING (true) WITH CHECK (true);
