
\restrict IRIskk2FmkoKAlXiynkD5D6RW2Sq5xFX8owhkd3YO0BRiuk50IWKoyAr2RSP178


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE SCHEMA IF NOT EXISTS "aion";


ALTER SCHEMA "aion" OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "aion"."approvals" (
    "request_id" "text" NOT NULL,
    "action" "text" NOT NULL,
    "summary" "text" NOT NULL,
    "destination" "text" NOT NULL,
    "payload_json" "text" NOT NULL,
    "content_hash" "text" NOT NULL,
    "idempotency_key" "text",
    "decision" "text" NOT NULL,
    "created_at" "text" NOT NULL,
    "expires_at" "text" NOT NULL,
    "decided_at" "text",
    "decided_by" "text",
    "reason" "text",
    "approval_token_hash" "text",
    "token_consumed_at" "text",
    "executed_at" "text",
    "injection_flags_json" "text" DEFAULT '[]'::"text" NOT NULL
);


ALTER TABLE "aion"."approvals" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "aion"."audit_events" (
    "id" bigint NOT NULL,
    "timestamp" "text" NOT NULL,
    "module" "text" NOT NULL,
    "action" "text" NOT NULL,
    "success" boolean NOT NULL,
    "detail_json" "text" NOT NULL
);


ALTER TABLE "aion"."audit_events" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "aion"."audit_events_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "aion"."audit_events_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "aion"."audit_events_id_seq" OWNED BY "aion"."audit_events"."id";



CREATE TABLE IF NOT EXISTS "aion"."autonomy_account_interactions" (
    "id" bigint NOT NULL,
    "account" "text" NOT NULL,
    "action" "text" NOT NULL,
    "solicited" boolean DEFAULT false NOT NULL,
    "created_at" "text" NOT NULL
);


ALTER TABLE "aion"."autonomy_account_interactions" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "aion"."autonomy_account_interactions_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "aion"."autonomy_account_interactions_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "aion"."autonomy_account_interactions_id_seq" OWNED BY "aion"."autonomy_account_interactions"."id";



CREATE TABLE IF NOT EXISTS "aion"."autonomy_actions" (
    "id" bigint NOT NULL,
    "timestamp" "text" NOT NULL,
    "action" "text" NOT NULL,
    "destination" "text" NOT NULL,
    "content_hash" "text" NOT NULL,
    "idempotency_key" "text",
    "url" "text",
    "success" boolean NOT NULL,
    "detail_json" "text" NOT NULL,
    "text_norm" "text",
    "account" "text"
);


ALTER TABLE "aion"."autonomy_actions" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "aion"."autonomy_actions_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "aion"."autonomy_actions_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "aion"."autonomy_actions_id_seq" OWNED BY "aion"."autonomy_actions"."id";



CREATE TABLE IF NOT EXISTS "aion"."autonomy_blocks" (
    "id" bigint NOT NULL,
    "timestamp" "text" NOT NULL,
    "action" "text" NOT NULL,
    "reasons_json" "text" NOT NULL,
    "payload_hash" "text",
    "detail_json" "text" NOT NULL
);


ALTER TABLE "aion"."autonomy_blocks" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "aion"."autonomy_blocks_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "aion"."autonomy_blocks_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "aion"."autonomy_blocks_id_seq" OWNED BY "aion"."autonomy_blocks"."id";



CREATE TABLE IF NOT EXISTS "aion"."autonomy_quota_events" (
    "id" bigint NOT NULL,
    "action" "text" NOT NULL,
    "created_at" "text" NOT NULL
);


ALTER TABLE "aion"."autonomy_quota_events" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "aion"."autonomy_quota_events_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "aion"."autonomy_quota_events_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "aion"."autonomy_quota_events_id_seq" OWNED BY "aion"."autonomy_quota_events"."id";



CREATE TABLE IF NOT EXISTS "aion"."autonomy_rate_limits" (
    "id" bigint NOT NULL,
    "timestamp" "text" NOT NULL,
    "action" "text",
    "status_code" integer,
    "retry_after_seconds" double precision,
    "detail_json" "text" NOT NULL
);


ALTER TABLE "aion"."autonomy_rate_limits" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "aion"."autonomy_rate_limits_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "aion"."autonomy_rate_limits_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "aion"."autonomy_rate_limits_id_seq" OWNED BY "aion"."autonomy_rate_limits"."id";



CREATE TABLE IF NOT EXISTS "aion"."conversation_messages" (
    "id" bigint NOT NULL,
    "conversation_id" "uuid" NOT NULL,
    "role" "text" NOT NULL,
    "content" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "fts" "tsvector" GENERATED ALWAYS AS ("to_tsvector"('"english"'::"regconfig", COALESCE("content", ''::"text"))) STORED,
    CONSTRAINT "conversation_messages_role_check" CHECK (("role" = ANY (ARRAY['user'::"text", 'assistant'::"text", 'system'::"text"])))
);


ALTER TABLE "aion"."conversation_messages" OWNER TO "postgres";


ALTER TABLE "aion"."conversation_messages" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "aion"."conversation_messages_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "aion"."conversations" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_session_id" "text" NOT NULL,
    "previous_response_id" "text",
    "model" "text",
    "runtime" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "aion"."conversations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "aion"."daily_reports" (
    "report_date" "text" NOT NULL,
    "created_at" "text" NOT NULL,
    "body_json" "text" NOT NULL
);


ALTER TABLE "aion"."daily_reports" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "aion"."drafts" (
    "draft_id" "text" NOT NULL,
    "day_index" integer NOT NULL,
    "theme" "text" NOT NULL,
    "title" "text" NOT NULL,
    "body" "text" NOT NULL,
    "submolt" "text" NOT NULL,
    "yalitek_connection" "text",
    "approval_request_id" "text",
    "created_at" "text" NOT NULL,
    "content_hash" "text" NOT NULL
);


ALTER TABLE "aion"."drafts" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "aion"."health_alerts" (
    "id" bigint NOT NULL,
    "timestamp" "text" NOT NULL,
    "alert_type" "text" NOT NULL,
    "detail_json" "text" NOT NULL,
    "delivered" boolean DEFAULT false NOT NULL
);


ALTER TABLE "aion"."health_alerts" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "aion"."health_alerts_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "aion"."health_alerts_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "aion"."health_alerts_id_seq" OWNED BY "aion"."health_alerts"."id";



CREATE TABLE IF NOT EXISTS "aion"."lead_alerts" (
    "id" bigint NOT NULL,
    "timestamp" "text" NOT NULL,
    "lead_id" "text" NOT NULL,
    "detail_json" "text" NOT NULL
);


ALTER TABLE "aion"."lead_alerts" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "aion"."lead_alerts_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "aion"."lead_alerts_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "aion"."lead_alerts_id_seq" OWNED BY "aion"."lead_alerts"."id";



CREATE TABLE IF NOT EXISTS "aion"."leads" (
    "lead_id" "text" NOT NULL,
    "source_url" "text" NOT NULL,
    "requester_identity" "text" NOT NULL,
    "stated_problem" "text" NOT NULL,
    "relevant_service" "text" NOT NULL,
    "fit_score" double precision NOT NULL,
    "confidence_score" double precision NOT NULL,
    "suggested_response" "text" NOT NULL,
    "risks" "text" NOT NULL,
    "approval_status" "text" NOT NULL,
    "conversion_outcome" "text" NOT NULL,
    "revenue_attributed" double precision DEFAULT 0 NOT NULL,
    "raw_excerpt" "text" NOT NULL,
    "created_at" "text" NOT NULL,
    "content_hash" "text" NOT NULL
);


ALTER TABLE "aion"."leads" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "aion"."memory_facts" (
    "id" bigint NOT NULL,
    "content" "text" NOT NULL,
    "category" "text",
    "source_conversation_id" "uuid",
    "source_message_id" bigint,
    "status" "text" DEFAULT 'active'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "fts" "tsvector" GENERATED ALWAYS AS (("setweight"("to_tsvector"('"english"'::"regconfig", COALESCE("category", ''::"text")), 'A'::"char") || "setweight"("to_tsvector"('"english"'::"regconfig", COALESCE("content", ''::"text")), 'B'::"char"))) STORED,
    "superseded_by" bigint,
    CONSTRAINT "memory_facts_content_check" CHECK (("length"("btrim"("content")) > 0)),
    CONSTRAINT "memory_facts_status_check" CHECK (("status" = ANY (ARRAY['active'::"text", 'forgotten'::"text", 'superseded'::"text"])))
);


ALTER TABLE "aion"."memory_facts" OWNER TO "postgres";


ALTER TABLE "aion"."memory_facts" ALTER COLUMN "id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "aion"."memory_facts_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "aion"."meta" (
    "key" "text" NOT NULL,
    "value" "text" NOT NULL
);


ALTER TABLE "aion"."meta" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "aion"."opportunities" (
    "opportunity_id" "text" NOT NULL,
    "discovered_at" "text" NOT NULL,
    "scout" "text" NOT NULL,
    "source" "text" NOT NULL,
    "customer_problem" "text" NOT NULL,
    "proposed_solution" "text" NOT NULL,
    "estimated_revenue" double precision NOT NULL,
    "estimated_cost" double precision DEFAULT 0 NOT NULL,
    "probability" double precision NOT NULL,
    "expected_value" double precision NOT NULL,
    "capital_required" double precision DEFAULT 0 NOT NULL,
    "time_hours" double precision DEFAULT 0 NOT NULL,
    "major_risks" "text" NOT NULL,
    "ethical_considerations" "text" NOT NULL,
    "confidence" double precision NOT NULL,
    "durable_value_score" double precision NOT NULL,
    "next_action" "text" NOT NULL,
    "authorization_required" "text" NOT NULL,
    "actual_result" "text" DEFAULT 'unresolved'::"text" NOT NULL,
    "realized_value" double precision DEFAULT 0 NOT NULL
);


ALTER TABLE "aion"."opportunities" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "aion"."paper_meta" (
    "key" "text" NOT NULL,
    "value" "text" NOT NULL
);


ALTER TABLE "aion"."paper_meta" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "aion"."paper_positions" (
    "asset" "text" NOT NULL,
    "qty" double precision NOT NULL
);


ALTER TABLE "aion"."paper_positions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "aion"."paper_snapshots" (
    "id" bigint NOT NULL,
    "timestamp" "text" NOT NULL,
    "equity" double precision NOT NULL,
    "cash" double precision NOT NULL,
    "btc_px" double precision NOT NULL,
    "eth_px" double precision NOT NULL,
    "detail_json" "text" NOT NULL,
    "price_source" "text" DEFAULT 'unknown'::"text" NOT NULL,
    "is_live_market_data" boolean DEFAULT false NOT NULL
);


ALTER TABLE "aion"."paper_snapshots" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "aion"."paper_snapshots_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "aion"."paper_snapshots_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "aion"."paper_snapshots_id_seq" OWNED BY "aion"."paper_snapshots"."id";



CREATE TABLE IF NOT EXISTS "aion"."paper_trades" (
    "id" bigint NOT NULL,
    "timestamp" "text" NOT NULL,
    "asset" "text" NOT NULL,
    "side" "text" NOT NULL,
    "qty" double precision NOT NULL,
    "price" double precision NOT NULL,
    "fee" double precision NOT NULL,
    "slippage" double precision NOT NULL,
    "note" "text",
    "price_source" "text" DEFAULT 'unknown'::"text" NOT NULL,
    "is_live_market_data" boolean DEFAULT false NOT NULL
);


ALTER TABLE "aion"."paper_trades" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "aion"."paper_trades_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "aion"."paper_trades_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "aion"."paper_trades_id_seq" OWNED BY "aion"."paper_trades"."id";



CREATE TABLE IF NOT EXISTS "aion"."positions" (
    "asset" "text" NOT NULL,
    "qty" double precision NOT NULL
);


ALTER TABLE "aion"."positions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "aion"."risk_state" (
    "key" "text" NOT NULL,
    "value_json" "text" NOT NULL,
    "updated_at" "text" NOT NULL
);


ALTER TABLE "aion"."risk_state" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "aion"."scheduler_locks" (
    "lock_name" "text" NOT NULL,
    "owner_id" "text" NOT NULL,
    "acquired_at" "text" NOT NULL,
    "expires_at" "text" NOT NULL,
    "meta_json" "text" DEFAULT '{}'::"text" NOT NULL
);


ALTER TABLE "aion"."scheduler_locks" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "aion"."scheduler_state" (
    "key" "text" NOT NULL,
    "value_json" "text" NOT NULL,
    "updated_at" "text" NOT NULL
);


ALTER TABLE "aion"."scheduler_state" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "aion"."snapshots" (
    "id" bigint NOT NULL,
    "timestamp" "text" NOT NULL,
    "equity" double precision NOT NULL,
    "cash" double precision NOT NULL,
    "btc_px" double precision NOT NULL,
    "eth_px" double precision NOT NULL,
    "detail_json" "text" NOT NULL,
    "price_source" "text" DEFAULT 'unknown'::"text" NOT NULL,
    "is_live_market_data" boolean DEFAULT false NOT NULL
);


ALTER TABLE "aion"."snapshots" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "aion"."snapshots_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "aion"."snapshots_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "aion"."snapshots_id_seq" OWNED BY "aion"."snapshots"."id";



CREATE TABLE IF NOT EXISTS "aion"."trades" (
    "id" bigint NOT NULL,
    "timestamp" "text" NOT NULL,
    "asset" "text" NOT NULL,
    "side" "text" NOT NULL,
    "qty" double precision NOT NULL,
    "price" double precision NOT NULL,
    "fee" double precision NOT NULL,
    "slippage" double precision NOT NULL,
    "note" "text",
    "price_source" "text" DEFAULT 'unknown'::"text" NOT NULL,
    "is_live_market_data" boolean DEFAULT false NOT NULL
);


ALTER TABLE "aion"."trades" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "aion"."trades_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "aion"."trades_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "aion"."trades_id_seq" OWNED BY "aion"."trades"."id";



ALTER TABLE ONLY "aion"."audit_events" ALTER COLUMN "id" SET DEFAULT "nextval"('"aion"."audit_events_id_seq"'::"regclass");



ALTER TABLE ONLY "aion"."autonomy_account_interactions" ALTER COLUMN "id" SET DEFAULT "nextval"('"aion"."autonomy_account_interactions_id_seq"'::"regclass");



ALTER TABLE ONLY "aion"."autonomy_actions" ALTER COLUMN "id" SET DEFAULT "nextval"('"aion"."autonomy_actions_id_seq"'::"regclass");



ALTER TABLE ONLY "aion"."autonomy_blocks" ALTER COLUMN "id" SET DEFAULT "nextval"('"aion"."autonomy_blocks_id_seq"'::"regclass");



ALTER TABLE ONLY "aion"."autonomy_quota_events" ALTER COLUMN "id" SET DEFAULT "nextval"('"aion"."autonomy_quota_events_id_seq"'::"regclass");



ALTER TABLE ONLY "aion"."autonomy_rate_limits" ALTER COLUMN "id" SET DEFAULT "nextval"('"aion"."autonomy_rate_limits_id_seq"'::"regclass");



ALTER TABLE ONLY "aion"."health_alerts" ALTER COLUMN "id" SET DEFAULT "nextval"('"aion"."health_alerts_id_seq"'::"regclass");



ALTER TABLE ONLY "aion"."lead_alerts" ALTER COLUMN "id" SET DEFAULT "nextval"('"aion"."lead_alerts_id_seq"'::"regclass");



ALTER TABLE ONLY "aion"."paper_snapshots" ALTER COLUMN "id" SET DEFAULT "nextval"('"aion"."paper_snapshots_id_seq"'::"regclass");



ALTER TABLE ONLY "aion"."paper_trades" ALTER COLUMN "id" SET DEFAULT "nextval"('"aion"."paper_trades_id_seq"'::"regclass");



ALTER TABLE ONLY "aion"."snapshots" ALTER COLUMN "id" SET DEFAULT "nextval"('"aion"."snapshots_id_seq"'::"regclass");



ALTER TABLE ONLY "aion"."trades" ALTER COLUMN "id" SET DEFAULT "nextval"('"aion"."trades_id_seq"'::"regclass");



ALTER TABLE ONLY "aion"."approvals"
    ADD CONSTRAINT "approvals_idempotency_key_key" UNIQUE ("idempotency_key");



ALTER TABLE ONLY "aion"."approvals"
    ADD CONSTRAINT "approvals_pkey" PRIMARY KEY ("request_id");



ALTER TABLE ONLY "aion"."audit_events"
    ADD CONSTRAINT "audit_events_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "aion"."autonomy_account_interactions"
    ADD CONSTRAINT "autonomy_account_interactions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "aion"."autonomy_actions"
    ADD CONSTRAINT "autonomy_actions_idempotency_key_key" UNIQUE ("idempotency_key");



ALTER TABLE ONLY "aion"."autonomy_actions"
    ADD CONSTRAINT "autonomy_actions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "aion"."autonomy_blocks"
    ADD CONSTRAINT "autonomy_blocks_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "aion"."autonomy_quota_events"
    ADD CONSTRAINT "autonomy_quota_events_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "aion"."autonomy_rate_limits"
    ADD CONSTRAINT "autonomy_rate_limits_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "aion"."conversation_messages"
    ADD CONSTRAINT "conversation_messages_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "aion"."conversations"
    ADD CONSTRAINT "conversations_client_session_id_key" UNIQUE ("client_session_id");



ALTER TABLE ONLY "aion"."conversations"
    ADD CONSTRAINT "conversations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "aion"."daily_reports"
    ADD CONSTRAINT "daily_reports_pkey" PRIMARY KEY ("report_date");



ALTER TABLE ONLY "aion"."drafts"
    ADD CONSTRAINT "drafts_content_hash_key" UNIQUE ("content_hash");



ALTER TABLE ONLY "aion"."drafts"
    ADD CONSTRAINT "drafts_pkey" PRIMARY KEY ("draft_id");



ALTER TABLE ONLY "aion"."health_alerts"
    ADD CONSTRAINT "health_alerts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "aion"."lead_alerts"
    ADD CONSTRAINT "lead_alerts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "aion"."leads"
    ADD CONSTRAINT "leads_content_hash_key" UNIQUE ("content_hash");



ALTER TABLE ONLY "aion"."leads"
    ADD CONSTRAINT "leads_pkey" PRIMARY KEY ("lead_id");



ALTER TABLE ONLY "aion"."memory_facts"
    ADD CONSTRAINT "memory_facts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "aion"."meta"
    ADD CONSTRAINT "meta_pkey" PRIMARY KEY ("key");



ALTER TABLE ONLY "aion"."opportunities"
    ADD CONSTRAINT "opportunities_pkey" PRIMARY KEY ("opportunity_id");



ALTER TABLE ONLY "aion"."opportunities"
    ADD CONSTRAINT "opportunities_scout_source_customer_problem_proposed_soluti_key" UNIQUE ("scout", "source", "customer_problem", "proposed_solution");



ALTER TABLE ONLY "aion"."paper_meta"
    ADD CONSTRAINT "paper_meta_pkey" PRIMARY KEY ("key");



ALTER TABLE ONLY "aion"."paper_positions"
    ADD CONSTRAINT "paper_positions_pkey" PRIMARY KEY ("asset");



ALTER TABLE ONLY "aion"."paper_snapshots"
    ADD CONSTRAINT "paper_snapshots_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "aion"."paper_trades"
    ADD CONSTRAINT "paper_trades_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "aion"."positions"
    ADD CONSTRAINT "positions_pkey" PRIMARY KEY ("asset");



ALTER TABLE ONLY "aion"."risk_state"
    ADD CONSTRAINT "risk_state_pkey" PRIMARY KEY ("key");



ALTER TABLE ONLY "aion"."scheduler_locks"
    ADD CONSTRAINT "scheduler_locks_pkey" PRIMARY KEY ("lock_name");



ALTER TABLE ONLY "aion"."scheduler_state"
    ADD CONSTRAINT "scheduler_state_pkey" PRIMARY KEY ("key");



ALTER TABLE ONLY "aion"."snapshots"
    ADD CONSTRAINT "snapshots_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "aion"."trades"
    ADD CONSTRAINT "trades_pkey" PRIMARY KEY ("id");



CREATE INDEX "conversation_messages_conversation_created_idx" ON "aion"."conversation_messages" USING "btree" ("conversation_id", "created_at", "id");



CREATE INDEX "conversation_messages_fts_idx" ON "aion"."conversation_messages" USING "gin" ("fts");



CREATE INDEX "idx_aion_opportunities_rank" ON "aion"."opportunities" USING "btree" ("durable_value_score" DESC, "discovered_at" DESC);



CREATE INDEX "idx_aion_quota_action_time" ON "aion"."autonomy_quota_events" USING "btree" ("action", "created_at");



CREATE INDEX "idx_autonomy_quota_action_time" ON "aion"."autonomy_quota_events" USING "btree" ("action", "created_at");



CREATE INDEX "memory_facts_active_updated_idx" ON "aion"."memory_facts" USING "btree" ("updated_at" DESC) WHERE ("status" = 'active'::"text");



CREATE INDEX "memory_facts_category_active_idx" ON "aion"."memory_facts" USING "btree" ("category", "updated_at" DESC) WHERE ("status" = 'active'::"text");



CREATE INDEX "memory_facts_fts_idx" ON "aion"."memory_facts" USING "gin" ("fts");



ALTER TABLE ONLY "aion"."conversation_messages"
    ADD CONSTRAINT "conversation_messages_conversation_id_fkey" FOREIGN KEY ("conversation_id") REFERENCES "aion"."conversations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "aion"."memory_facts"
    ADD CONSTRAINT "memory_facts_source_conversation_id_fkey" FOREIGN KEY ("source_conversation_id") REFERENCES "aion"."conversations"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "aion"."memory_facts"
    ADD CONSTRAINT "memory_facts_source_message_id_fkey" FOREIGN KEY ("source_message_id") REFERENCES "aion"."conversation_messages"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "aion"."memory_facts"
    ADD CONSTRAINT "memory_facts_superseded_by_fkey" FOREIGN KEY ("superseded_by") REFERENCES "aion"."memory_facts"("id") ON DELETE SET NULL;



ALTER TABLE "aion"."conversation_messages" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "aion"."conversations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "aion"."memory_facts" ENABLE ROW LEVEL SECURITY;


GRANT USAGE ON SCHEMA "aion" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."approvals" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."audit_events" TO "aion_app";



GRANT SELECT,USAGE ON SEQUENCE "aion"."audit_events_id_seq" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."autonomy_account_interactions" TO "aion_app";



GRANT SELECT,USAGE ON SEQUENCE "aion"."autonomy_account_interactions_id_seq" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."autonomy_actions" TO "aion_app";



GRANT SELECT,USAGE ON SEQUENCE "aion"."autonomy_actions_id_seq" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."autonomy_blocks" TO "aion_app";



GRANT SELECT,USAGE ON SEQUENCE "aion"."autonomy_blocks_id_seq" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."autonomy_quota_events" TO "aion_app";



GRANT SELECT,USAGE ON SEQUENCE "aion"."autonomy_quota_events_id_seq" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."autonomy_rate_limits" TO "aion_app";



GRANT SELECT,USAGE ON SEQUENCE "aion"."autonomy_rate_limits_id_seq" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."conversation_messages" TO "aion_app";



GRANT SELECT,USAGE ON SEQUENCE "aion"."conversation_messages_id_seq" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."conversations" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."daily_reports" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."drafts" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."health_alerts" TO "aion_app";



GRANT SELECT,USAGE ON SEQUENCE "aion"."health_alerts_id_seq" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."lead_alerts" TO "aion_app";



GRANT SELECT,USAGE ON SEQUENCE "aion"."lead_alerts_id_seq" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."leads" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."memory_facts" TO "aion_app";



GRANT SELECT,USAGE ON SEQUENCE "aion"."memory_facts_id_seq" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."meta" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."opportunities" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."paper_meta" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."paper_positions" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."paper_snapshots" TO "aion_app";



GRANT SELECT,USAGE ON SEQUENCE "aion"."paper_snapshots_id_seq" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."paper_trades" TO "aion_app";



GRANT SELECT,USAGE ON SEQUENCE "aion"."paper_trades_id_seq" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."positions" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."risk_state" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."scheduler_locks" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."scheduler_state" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."snapshots" TO "aion_app";



GRANT SELECT,USAGE ON SEQUENCE "aion"."snapshots_id_seq" TO "aion_app";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "aion"."trades" TO "aion_app";



GRANT SELECT,USAGE ON SEQUENCE "aion"."trades_id_seq" TO "aion_app";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "aion" GRANT SELECT,USAGE ON SEQUENCES TO "aion_app";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "aion" GRANT SELECT,INSERT,DELETE,UPDATE ON TABLES TO "aion_app";



\unrestrict IRIskk2FmkoKAlXiynkD5D6RW2Sq5xFX8owhkd3YO0BRiuk50IWKoyAr2RSP178

RESET ALL;
