-- ==============================================================================
-- DATABASE SCHEMA DUMP (Generated via Supabase CLI Management API)
-- ==============================================================================

-- ── Table: alembic_version ──────────────────────────────────────────────────
CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL,
    CONSTRAINT alembic_version_pkey PRIMARY KEY (version_num)
);

ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;
CREATE POLICY Service role full access on alembic_version ON public.alembic_version TO service_role USING (true) WITH CHECK (true);
CREATE UNIQUE INDEX alembic_version_pkc ON public.alembic_version USING btree (version_num);

-- ── Table: application_analytics ──────────────────────────────────────────────────
CREATE TABLE public.application_analytics (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    computed_at timestamp with time zone NOT NULL DEFAULT now(),
    total_applications integer NOT NULL DEFAULT 0,
    applied_count integer NOT NULL DEFAULT 0,
    assessment_count integer NOT NULL DEFAULT 0,
    interview_count integer NOT NULL DEFAULT 0,
    offer_count integer NOT NULL DEFAULT 0,
    rejected_count integer NOT NULL DEFAULT 0,
    pending_count integer NOT NULL DEFAULT 0,
    interview_rate double precision NULL,
    offer_rate double precision NULL,
    rejection_rate double precision NULL,
    monthly_data jsonb NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    response_rate double precision NULL,
    CONSTRAINT application_analytics_pkey PRIMARY KEY (id)
);

ALTER TABLE public.application_analytics ENABLE ROW LEVEL SECURITY;
CREATE POLICY Service role full access on application_analytics ON public.application_analytics TO service_role USING (true) WITH CHECK (true);
CREATE POLICY Users can view own analytics ON public.application_analytics FOR SELECT TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
ALTER TABLE ONLY public.application_analytics ADD CONSTRAINT fk_application_analytics_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
CREATE UNIQUE INDEX uq_analytics_user_id ON public.application_analytics USING btree (user_id);

-- ── Table: application_status_history ──────────────────────────────────────────────────
CREATE TABLE public.application_status_history (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    application_id uuid NOT NULL,
    user_id uuid NOT NULL,
    status character varying(50) NOT NULL,
    source character varying(50) NOT NULL DEFAULT 'email_import'::character varying,
    detected_at timestamp with time zone NOT NULL,
    source_email_id character varying(255) NULL,
    notes text NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    confidence_scores jsonb NULL,
    CONSTRAINT application_status_history_pkey PRIMARY KEY (id)
);

ALTER TABLE public.application_status_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY Service role full access on status history ON public.application_status_history TO service_role USING (true) WITH CHECK (true);
CREATE POLICY Users can delete own status history ON public.application_status_history FOR DELETE TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY Users can insert own status history ON public.application_status_history FOR INSERT TO authenticated WITH CHECK ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY Users can update own status history ON public.application_status_history FOR UPDATE TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id)) WITH CHECK ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY Users can view own status history ON public.application_status_history FOR SELECT TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
ALTER TABLE ONLY public.application_status_history ADD CONSTRAINT fk_application_status_history_application_id FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.application_status_history ADD CONSTRAINT fk_application_status_history_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX idx_history_app_id ON public.application_status_history USING btree (application_id);
CREATE INDEX idx_history_detected_at ON public.application_status_history USING btree (application_id, detected_at);
CREATE INDEX idx_history_user_id ON public.application_status_history USING btree (user_id);

-- ── Table: applications ──────────────────────────────────────────────────
CREATE TABLE public.applications (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    company_name character varying(255) NOT NULL,
    role_title character varying(255) NOT NULL,
    current_status USER-DEFINED NOT NULL DEFAULT 'applied'::application_status,
    source_email_id character varying(255) NULL,
    gmail_thread_id character varying(255) NULL,
    applied_at timestamp with time zone NULL,
    last_activity_at timestamp with time zone NOT NULL DEFAULT now(),
    is_deleted boolean NOT NULL DEFAULT false,
    deleted_at timestamp with time zone NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    confidence_scores jsonb NULL,
    CONSTRAINT applications_pkey PRIMARY KEY (id)
);

ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;
CREATE POLICY Service role full access on applications ON public.applications TO service_role USING (true) WITH CHECK (true);
CREATE POLICY Users can delete own applications ON public.applications FOR DELETE TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY Users can insert own applications ON public.applications FOR INSERT TO authenticated WITH CHECK ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY Users can update own applications ON public.applications FOR UPDATE TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id)) WITH CHECK ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY Users can view own applications ON public.applications FOR SELECT TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
ALTER TABLE ONLY public.applications ADD CONSTRAINT fk_applications_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX idx_apps_last_activity ON public.applications USING btree (user_id, last_activity_at);
CREATE INDEX idx_apps_thread_id ON public.applications USING btree (gmail_thread_id);
CREATE INDEX idx_apps_user_deleted ON public.applications USING btree (user_id, is_deleted);
CREATE INDEX idx_apps_user_id ON public.applications USING btree (user_id);
CREATE INDEX idx_apps_user_status ON public.applications USING btree (user_id, current_status);

-- ── Table: deleted_applications ──────────────────────────────────────────────────
CREATE TABLE public.deleted_applications (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    application_id uuid NOT NULL,
    user_id uuid NOT NULL,
    deleted_at timestamp with time zone NOT NULL DEFAULT now(),
    purge_after timestamp with time zone NOT NULL,
    deleted_by character varying(50) NOT NULL DEFAULT 'user'::character varying,
    restored_at timestamp with time zone NULL,
    is_purged boolean NOT NULL DEFAULT false,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT deleted_applications_pkey PRIMARY KEY (id)
);

ALTER TABLE public.deleted_applications ENABLE ROW LEVEL SECURITY;
CREATE POLICY Service role full access on deleted_applications ON public.deleted_applications TO service_role USING (true) WITH CHECK (true);
CREATE POLICY Users can delete own deleted_applications ON public.deleted_applications FOR DELETE TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY Users can update own deleted_applications ON public.deleted_applications FOR UPDATE TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id)) WITH CHECK ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY Users can view own deleted_applications ON public.deleted_applications FOR SELECT TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
ALTER TABLE ONLY public.deleted_applications ADD CONSTRAINT fk_deleted_applications_application_id FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.deleted_applications ADD CONSTRAINT fk_deleted_applications_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX idx_bin_purge_after ON public.deleted_applications USING btree (purge_after) WHERE (is_purged = false);
CREATE INDEX idx_bin_user_id ON public.deleted_applications USING btree (user_id);
CREATE UNIQUE INDEX uq_deleted_application_id ON public.deleted_applications USING btree (application_id);

-- ── Table: emails ──────────────────────────────────────────────────
CREATE TABLE public.emails (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    application_id uuid NULL,
    gmail_msg_id character varying(255) NOT NULL,
    gmail_thread_id character varying(255) NULL,
    subject text NULL,
    sender character varying(500) NULL,
    gmail_internal_date timestamp with time zone NOT NULL,
    snippet text NULL,
    gmail_label_ids ARRAY NULL,
    is_processed boolean NOT NULL DEFAULT false,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    recipient text NULL,
    date timestamp with time zone NULL,
    is_parsed boolean NOT NULL DEFAULT false,
    parsed_at timestamp with time zone NULL,
    parse_attempts integer NOT NULL DEFAULT 0,
    last_parse_error text NULL,
    CONSTRAINT emails_pkey PRIMARY KEY (id)
);

ALTER TABLE public.emails ENABLE ROW LEVEL SECURITY;
CREATE POLICY Service role full access on emails ON public.emails TO service_role USING (true) WITH CHECK (true);
CREATE POLICY Users can view own emails ON public.emails FOR SELECT TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
ALTER TABLE ONLY public.emails ADD CONSTRAINT fk_emails_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.emails ADD CONSTRAINT fk_emails_application_id FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE;
CREATE INDEX idx_emails_app_id ON public.emails USING btree (application_id);
CREATE INDEX idx_emails_internal_date ON public.emails USING btree (user_id, gmail_internal_date);
CREATE INDEX idx_emails_thread_id ON public.emails USING btree (gmail_thread_id);
CREATE INDEX idx_emails_unprocessed ON public.emails USING btree (user_id, is_processed) WHERE (is_processed = false);
CREATE INDEX idx_emails_user_id ON public.emails USING btree (user_id);
CREATE UNIQUE INDEX uq_emails_user_msg ON public.emails USING btree (user_id, gmail_msg_id);

-- ── Table: gmail_connections ──────────────────────────────────────────────────
CREATE TABLE public.gmail_connections (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    gmail_email character varying(255) NOT NULL,
    encrypted_refresh_token text NOT NULL,
    token_expiry timestamp with time zone NULL,
    scopes ARRAY NOT NULL DEFAULT '{}'::text[],
    connected_at timestamp with time zone NOT NULL,
    last_successful_sync_at timestamp with time zone NULL,
    initial_import_done boolean NOT NULL DEFAULT false,
    initial_import_from timestamp with time zone NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    initial_import_range character varying(255) NULL,
    CONSTRAINT gmail_connections_pkey PRIMARY KEY (id)
);

ALTER TABLE public.gmail_connections ENABLE ROW LEVEL SECURITY;
CREATE POLICY Service role full access on gmail_connections ON public.gmail_connections TO service_role USING (true) WITH CHECK (true);
CREATE POLICY Users can delete own gmail_connections ON public.gmail_connections FOR DELETE TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY Users can insert own gmail_connections ON public.gmail_connections FOR INSERT TO authenticated WITH CHECK ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY Users can update own gmail_connections ON public.gmail_connections FOR UPDATE TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id)) WITH CHECK ((( SELECT auth.uid() AS uid) = user_id));
CREATE POLICY Users can view own gmail_connections ON public.gmail_connections FOR SELECT TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
ALTER TABLE ONLY public.gmail_connections ADD CONSTRAINT fk_gmail_connections_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
CREATE UNIQUE INDEX uq_gmail_connections_user_id ON public.gmail_connections USING btree (user_id);

-- ── Table: password_reset_tokens ──────────────────────────────────────────────────
CREATE TABLE public.password_reset_tokens (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    token_hash character varying(255) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    is_used boolean NOT NULL DEFAULT false,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id)
);

ALTER TABLE public.password_reset_tokens ENABLE ROW LEVEL SECURITY;
CREATE POLICY Service role full access on password_reset_tokens ON public.password_reset_tokens TO service_role USING (true) WITH CHECK (true);
ALTER TABLE ONLY public.password_reset_tokens ADD CONSTRAINT fk_password_reset_tokens_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX idx_reset_tokens_expires_at ON public.password_reset_tokens USING btree (expires_at);
CREATE INDEX idx_reset_tokens_user_id ON public.password_reset_tokens USING btree (user_id);
CREATE UNIQUE INDEX uq_reset_token_hash ON public.password_reset_tokens USING btree (token_hash);

-- ── Table: sync_logs ──────────────────────────────────────────────────
CREATE TABLE public.sync_logs (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    sync_type USER-DEFINED NOT NULL,
    status USER-DEFINED NOT NULL DEFAULT 'pending'::sync_status,
    started_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone NULL,
    emails_fetched integer NOT NULL DEFAULT 0,
    emails_parsed integer NOT NULL DEFAULT 0,
    apps_created integer NOT NULL DEFAULT 0,
    apps_updated integer NOT NULL DEFAULT 0,
    error_message text NULL,
    celery_task_id character varying(255) NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT sync_logs_pkey PRIMARY KEY (id)
);

ALTER TABLE public.sync_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY Service role full access on sync_logs ON public.sync_logs TO service_role USING (true) WITH CHECK (true);
CREATE POLICY Users can view own sync_logs ON public.sync_logs FOR SELECT TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
ALTER TABLE ONLY public.sync_logs ADD CONSTRAINT fk_sync_logs_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX idx_sync_started_at ON public.sync_logs USING btree (user_id, started_at);
CREATE INDEX idx_sync_user_id ON public.sync_logs USING btree (user_id);
CREATE INDEX idx_sync_user_status ON public.sync_logs USING btree (user_id, status);

-- ── Table: user_sessions ──────────────────────────────────────────────────
CREATE TABLE public.user_sessions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    refresh_token_hash character varying(255) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    is_revoked boolean NOT NULL DEFAULT false,
    ip_address inet NULL,
    user_agent text NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT user_sessions_pkey PRIMARY KEY (id)
);

ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY Service role full access on user_sessions ON public.user_sessions TO service_role USING (true) WITH CHECK (true);
CREATE POLICY Users can view own user_sessions ON public.user_sessions FOR SELECT TO authenticated USING ((( SELECT auth.uid() AS uid) = user_id));
ALTER TABLE ONLY public.user_sessions ADD CONSTRAINT fk_user_sessions_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX idx_sessions_expires_at ON public.user_sessions USING btree (expires_at);
CREATE INDEX idx_sessions_user_id ON public.user_sessions USING btree (user_id);

-- ── Table: users ──────────────────────────────────────────────────
CREATE TABLE public.users (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    full_name character varying(255) NOT NULL,
    username character varying(100) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    is_email_verified boolean NOT NULL DEFAULT false,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    is_onboarding_completed boolean NOT NULL DEFAULT false,
    CONSTRAINT users_pkey PRIMARY KEY (id)
);

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
CREATE POLICY Service role full access on users ON public.users TO service_role USING (true) WITH CHECK (true);
CREATE POLICY Users can update own profile ON public.users FOR UPDATE TO authenticated USING ((( SELECT auth.uid() AS uid) = id)) WITH CHECK ((( SELECT auth.uid() AS uid) = id));
CREATE POLICY Users can view own profile ON public.users FOR SELECT TO authenticated USING ((( SELECT auth.uid() AS uid) = id));
CREATE INDEX idx_users_created_at ON public.users USING btree (created_at);
CREATE INDEX idx_users_onboarding_incomplete ON public.users USING btree (id) WHERE ((is_onboarding_completed = false) AND (is_active = true));
CREATE UNIQUE INDEX uq_users_username ON public.users USING btree (username);
