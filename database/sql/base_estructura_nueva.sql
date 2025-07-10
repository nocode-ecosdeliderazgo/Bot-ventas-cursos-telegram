-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.ai_course_sessions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  course_id uuid NOT NULL,
  session_index integer NOT NULL,
  title text NOT NULL,
  objective text,
  duration_minutes text,
  created_at timestamp without time zone DEFAULT now(),
  scheduled_at timestamp without time zone,
  display_order integer,
  modality text DEFAULT 'online'::text,
  resources_url text,
  CONSTRAINT ai_course_sessions_pkey PRIMARY KEY (id),
  CONSTRAINT ai_course_sessions_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.ai_courses(id)
);
CREATE TABLE public.ai_courses (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  short_description text NOT NULL,
  long_description text NOT NULL,
  created_at timestamp without time zone DEFAULT now(),
  subtheme_id uuid NOT NULL,
  session_count integer NOT NULL DEFAULT 0,
  total_duration_min text NOT NULL,
  price text,
  currency character varying DEFAULT 'USD'::character varying,
  course_url text,
  purchase_url text,
  level text DEFAULT 'básico'::text,
  language text DEFAULT 'es'::text,
  audience_category text,
  status text DEFAULT 'borrador'::text,
  start_date date,
  end_date date,
  max_enrollees integer DEFAULT 0,
  roi text,
  CONSTRAINT ai_courses_pkey PRIMARY KEY (id),
  CONSTRAINT ai_courses_subtheme_id_fkey FOREIGN KEY (subtheme_id) REFERENCES public.ai_subthemes(id)
);
CREATE TABLE public.ai_session_deliverables (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL,
  name text NOT NULL,
  type text NOT NULL,
  resource_url text,
  created_at timestamp without time zone DEFAULT now(),
  estimated_duration_min integer DEFAULT 0,
  resource_type text,
  is_mandatory boolean DEFAULT true,
  CONSTRAINT ai_session_deliverables_pkey PRIMARY KEY (id),
  CONSTRAINT ai_session_deliverables_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.ai_course_sessions(id)
);
CREATE TABLE public.ai_subthemes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT ai_subthemes_pkey PRIMARY KEY (id)
);
CREATE TABLE public.ai_tematarios (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  course_id uuid NOT NULL,
  session_id uuid NOT NULL,
  item_index integer NOT NULL,
  title text NOT NULL,
  item_type text NOT NULL,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT ai_tematarios_pkey PRIMARY KEY (id),
  CONSTRAINT ai_tematarios_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.ai_courses(id),
  CONSTRAINT ai_tematarios_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.ai_course_sessions(id)
);
CREATE TABLE public.bot_course_resources (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  course_id uuid NOT NULL,
  resource_id uuid NOT NULL,
  context_description text,
  priority integer DEFAULT 1,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT bot_course_resources_pkey PRIMARY KEY (id),
  CONSTRAINT bot_course_resources_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.ai_courses(id),
  CONSTRAINT bot_course_resources_resource_id_fkey FOREIGN KEY (resource_id) REFERENCES public.bot_resources(id)
);
CREATE TABLE public.bot_resources (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  resource_type character varying NOT NULL,
  resource_key character varying NOT NULL UNIQUE,
  resource_url text NOT NULL,
  resource_title text NOT NULL,
  resource_description text,
  is_active boolean DEFAULT true,
  created_at timestamp without time zone DEFAULT now(),
  updated_at timestamp without time zone DEFAULT now(),
  CONSTRAINT bot_resources_pkey PRIMARY KEY (id)
);
CREATE TABLE public.bot_session_resources (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL,
  resource_id uuid NOT NULL,
  context_description text,
  priority integer DEFAULT 1,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT bot_session_resources_pkey PRIMARY KEY (id),
  CONSTRAINT bot_session_resources_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.ai_course_sessions(id),
  CONSTRAINT bot_session_resources_resource_id_fkey FOREIGN KEY (resource_id) REFERENCES public.bot_resources(id)
);
CREATE TABLE public.course_bonuses (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  course_id uuid,
  bonus_name text NOT NULL,
  bonus_description text NOT NULL,
  bonus_type text,
  resource_url text,
  value_usd numeric,
  condition_type text,
  condition_detail text,
  is_active boolean DEFAULT true,
  created_at timestamp without time zone DEFAULT now(),
  CONSTRAINT course_bonuses_pkey PRIMARY KEY (id),
  CONSTRAINT course_bonuses_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.ai_courses(id)
);
CREATE TABLE public.free_resources (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  course_id uuid,
  resource_name text NOT NULL,
  resource_type text CHECK (resource_type = ANY (ARRAY['video'::text, 'document'::text, 'pdf'::text, 'PDF'::text, 'link'::text, 'image'::text])),
  resource_url text NOT NULL,
  resource_description text,
  file_size text,
  tags ARRAY,
  created_at timestamp without time zone DEFAULT now(),
  active boolean DEFAULT true,
  CONSTRAINT free_resources_pkey PRIMARY KEY (id)
);
CREATE TABLE public.payment_info (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  company_name character varying NOT NULL,
  bank_name character varying NOT NULL,
  clabe_account character varying NOT NULL,
  rfc character varying NOT NULL,
  cfdi_usage character varying NOT NULL,
  cfdi_description character varying,
  is_active boolean DEFAULT true,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT payment_info_pkey PRIMARY KEY (id)
);