-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.bonus_claims (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  bonus_id uuid,
  user_lead_id uuid,
  claimed_at timestamp with time zone DEFAULT now(),
  status text CHECK (status = ANY (ARRAY['pending'::text, 'active'::text, 'expired'::text, 'used'::text])),
  CONSTRAINT bonus_claims_pkey PRIMARY KEY (id),
  CONSTRAINT bonus_claims_bonus_id_fkey FOREIGN KEY (bonus_id) REFERENCES public.limited_time_bonuses(id),
  CONSTRAINT bonus_claims_user_lead_id_fkey FOREIGN KEY (user_lead_id) REFERENCES public.user_leads(id)
);
CREATE TABLE public.conversations (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  lead_id uuid NOT NULL,
  message_type text NOT NULL CHECK (message_type = ANY (ARRAY['user_message'::text, 'bot_response'::text, 'faq_question'::text])),
  content text NOT NULL,
  context jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT conversations_pkey PRIMARY KEY (id),
  CONSTRAINT fk_lead FOREIGN KEY (lead_id) REFERENCES public.user_leads(id)
);
CREATE TABLE public.course_interactions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  lead_id uuid NOT NULL,
  course_id uuid NOT NULL,
  interaction_type text NOT NULL CHECK (interaction_type = ANY (ARRAY['view'::text, 'inquiry'::text, 'demo_request'::text, 'purchase'::text])),
  metadata jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT course_interactions_pkey PRIMARY KEY (id),
  CONSTRAINT fk_lead FOREIGN KEY (lead_id) REFERENCES public.user_leads(id),
  CONSTRAINT fk_course FOREIGN KEY (course_id) REFERENCES public.courses(id)
);
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
CREATE TABLE public.course_sales (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  lead_id uuid NOT NULL,
  course_id uuid NOT NULL,
  amount_paid numeric NOT NULL CHECK (amount_paid >= 0::numeric),
  currency text NOT NULL,
  payment_method text,
  payment_status text NOT NULL DEFAULT 'pending'::text CHECK (payment_status = ANY (ARRAY['pending'::text, 'completed'::text, 'failed'::text, 'refunded'::text])),
  purchase_date timestamp with time zone DEFAULT now(),
  CONSTRAINT course_sales_pkey PRIMARY KEY (id),
  CONSTRAINT fk_lead FOREIGN KEY (lead_id) REFERENCES public.user_leads(id),
  CONSTRAINT fk_course FOREIGN KEY (course_id) REFERENCES public.courses(id)
);
CREATE TABLE public.courses (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  short_description text,
  long_description text,
  total_duration interval,
  price_usd numeric CHECK (price_usd >= 0::numeric),
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
  original_price_usd numeric,
  discount_percentage numeric CHECK (discount_percentage >= 0::numeric AND discount_percentage <= 100::numeric),
  discount_end_date timestamp with time zone,
  min_students integer DEFAULT 1,
  max_students integer,
  prerequisites ARRAY,
  requirements ARRAY,
  meta_keywords ARRAY,
  meta_description text,
  syllabus_url text,
  preview_url text,
  resources_url text,
  CONSTRAINT courses_pkey PRIMARY KEY (id)
);
CREATE TABLE public.limited_time_bonuses (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text NOT NULL,
  value_proposition text NOT NULL,
  original_value numeric,
  expires_at timestamp with time zone NOT NULL,
  max_claims integer,
  current_claims integer DEFAULT 0,
  course_id uuid,
  active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT limited_time_bonuses_pkey PRIMARY KEY (id),
  CONSTRAINT limited_time_bonuses_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id)
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
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  telegram_id text NOT NULL UNIQUE,
  name text NOT NULL,
  email text UNIQUE CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'::text),
  phone text,
  language text DEFAULT 'es'::text,
  stage text NOT NULL DEFAULT 'nuevo'::text,
  source text,
  campaign_id text,
  selected_course uuid,
  last_contact timestamp with time zone,
  next_followup timestamp with time zone,
  role text,
  company text,
  industry text,
  experience_level text CHECK (experience_level = ANY (ARRAY['principiante'::text, 'intermedio'::text, 'avanzado'::text])),
  interests ARRAY,
  preferred_schedule text,
  budget_range text,
  learning_goals text,
  last_interaction timestamp with time zone,
  interaction_count integer DEFAULT 0,
  interest_score integer DEFAULT 0 CHECK (interest_score >= 0 AND interest_score <= 100),
  privacy_accepted boolean DEFAULT false,
  marketing_consent boolean DEFAULT false,
  notifications_enabled boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_leads_pkey PRIMARY KEY (id),
  CONSTRAINT fk_selected_course FOREIGN KEY (selected_course) REFERENCES public.courses(id)
);