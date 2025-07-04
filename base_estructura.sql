-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.course_modules (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  course_id uuid NOT NULL,
  module_index integer NOT NULL,
  name text NOT NULL,
  description text,
  duration interval,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT course_modules_pkey PRIMARY KEY (id),
  CONSTRAINT course_modules_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id)
);
CREATE TABLE public.course_prompts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  course_id uuid NOT NULL,
  usage text,
  prompt text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT course_prompts_pkey PRIMARY KEY (id),
  CONSTRAINT course_prompts_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id)
);
CREATE TABLE public.courses (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  short_description text,
  long_description text,
  total_duration interval,
  price_usd numeric,
  currency text,
  course_link text,
  purchase_link text,
  demo_request_link text,
  level text,
  category text,
  language text,
  thumbnail_url text,
  rating numeric,
  reviews_count integer DEFAULT 0,
  published boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  online boolean DEFAULT true,
  tools_used ARRAY,
  schedule text,
  CONSTRAINT courses_pkey PRIMARY KEY (id)
);
CREATE TABLE public.cta_buttons (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  text character varying NOT NULL,
  callback_data character varying NOT NULL,
  context_type character varying DEFAULT 'default'::character varying,
  priority integer DEFAULT 999,
  active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT cta_buttons_pkey PRIMARY KEY (id)
);
CREATE TABLE public.documents (
  id integer GENERATED ALWAYS AS IDENTITY NOT NULL,
  title text NOT NULL,
  content text NOT NULL,
  embedding USER-DEFINED,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT documents_pkey PRIMARY KEY (id)
);
CREATE TABLE public.langchain_chat_histories (
  id integer NOT NULL DEFAULT nextval('langchain_chat_histories_id_seq'::regclass),
  session_id character varying NOT NULL,
  message jsonb NOT NULL,
  CONSTRAINT langchain_chat_histories_pkey PRIMARY KEY (id)
);
CREATE TABLE public.module_exercises (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  module_id uuid NOT NULL,
  order_idx integer NOT NULL,
  description text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT module_exercises_pkey PRIMARY KEY (id),
  CONSTRAINT module_exercises_module_id_fkey FOREIGN KEY (module_id) REFERENCES public.course_modules(id)
);
CREATE TABLE public.promotions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text,
  code text UNIQUE,
  active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT promotions_pkey PRIMARY KEY (id)
);
CREATE TABLE public.user_leads (
  id text NOT NULL DEFAULT gen_random_uuid(),
  email text NOT NULL,
  phone text,
  stage text,
  selected_course uuid,
  created_at timestamp with time zone DEFAULT now(),
  name text,
  role text,
  interests text,
  CONSTRAINT user_leads_pkey PRIMARY KEY (id)
);