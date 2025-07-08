BEGIN;
SET CONSTRAINTS ALL DEFERRED;

-- 1️⃣ Curso
INSERT INTO courses (
  id, name, short_description, long_description, total_duration,
  price_usd, currency, demo_request_link, resources_url, preview_url, syllabus_url,
  level, category, language, published, meta_keywords, meta_description
) VALUES (
  'a392bf83-4908-4807-89a9-95d0acc807c9',
  'Experto en IA para Profesionales: Dominando ChatGPT y Gemini para la Productividad',
  'Integra ChatGPT y Gemini en tu rutina y multiplica tu productividad.',
  'Capacita a profesionales para diseñar prompts avanzados, crear agentes personalizados y desarrollar flujos de trabajo con IA en 4 sesiones prácticas.',
  INTERVAL '8 hours',
  197, 'USD',
  'https://calendly.com/demo-ia-pro',
  'https://recursos.aprendayaplique.com/ia-pro/',
  'https://vimeo.com/preview-ia-pro',
  'https://recursos.aprendayaplique.com/syllabus-ia-pro.pdf',
  'intermedio', 'productividad', 'es', TRUE,
  ARRAY['ChatGPT','Gemini','Productividad','Prompting'],
  'Curso práctico para dominar IA generativa (ChatGPT + Gemini) y aplicarla en tu trabajo diario.'
);

-- 2️⃣ Módulos
INSERT INTO course_modules (id, course_id, module_index, name, description, duration) VALUES
(gen_random_uuid(), 'a392bf83-4908-4807-89a9-95d0acc807c9', 1,
 'Descubriendo la IA para Profesionales',
 'Comprender la relevancia de la IA, configurar ChatGPT y Gemini y aplicar prompting básico para optimizar el CV.',
 INTERVAL '2 hours'),
(gen_random_uuid(), 'a392bf83-4908-4807-89a9-95d0acc807c9', 2,
 'Dominando la Comunicación con IA',
 'Técnicas avanzadas de prompt design y creación de Custom GPTs y Gems para automatizar marketing e informes.',
 INTERVAL '2 hours'),
(gen_random_uuid(), 'a392bf83-4908-4807-89a9-95d0acc807c9', 3,
 'IMPULSO con ChatGPT para PYMES',
 'Aplicar el modelo IMPULSO para resolver problemas de negocio, definir KPI y ciclos de mejora quincenal.',
 INTERVAL '2 hours'),
(gen_random_uuid(), 'a392bf83-4908-4807-89a9-95d0acc807c9', 4,
 'Proyecto Integrador y Estrategia de IA',
 'Diseñar e implementar un proyecto real de IA generativa con plan de integración diaria y métricas SMART.',
 INTERVAL '2 hours');

-- 3️⃣ Prompts
INSERT INTO course_prompts (course_id, usage, prompt) VALUES
('a392bf83-4908-4807-89a9-95d0acc807c9','sess1_intro','https://gamma.app/docs/Workshop-12hrs-El-Despertar-de-una-Nueva-Era-Humana-rh14jbpv1jnud26'),
('a392bf83-4908-4807-89a9-95d0acc807c9','sess1_framework','https://gamma.app/docs/Paso-1-El-Lenguaje-del-Futuro-Wrkshop-el-despertar-g5sfpejnj3duh3u'),
('a392bf83-4908-4807-89a9-95d0acc807c9','sess2_framework','https://gamma.app/docs/Paso-2-Frameworks-para-la-Creacion-de-Prompts-Workshop-el-des-pdk2fo0zkz3xr66?mode=doc'),
('a392bf83-4908-4807-89a9-95d0acc807c9','sess3_impulso','Aplicar el acrónimo IMPULSO a un caso real de PYME: Identificar, Mapear y formular prompts.'),
('a392bf83-4908-4807-89a9-95d0acc807c9','sess4_proyecto','Diseñar un proyecto integrador y plan de implementación diaria con métricas SMART.');

-- 4️⃣ Ejercicios
INSERT INTO module_exercises (module_id, order_idx, description) VALUES
((SELECT id FROM course_modules WHERE course_id='a392bf83-4908-4807-89a9-95d0acc807c9' AND module_index=1),1,'Imaginar el futuro digital de tu rol y escribir tu primer “conjuro digital”.'),
((SELECT id FROM course_modules WHERE course_id='a392bf83-4908-4807-89a9-95d0acc807c9' AND module_index=1),2,'Ejercicio de reflexión: ¿Qué futuro quieres invocar con tu prompt?'),
((SELECT id FROM course_modules WHERE course_id='a392bf83-4908-4807-89a9-95d0acc807c9' AND module_index=2),1,'Crear un megaprompt usando metaprompt y prompt progresivo para una campaña de marketing.'),
((SELECT id FROM course_modules WHERE course_id='a392bf83-4908-4807-89a9-95d0acc807c9' AND module_index=2),2,'Desarrollar un Custom GPT que automatice informes ejecutivos.'),
((SELECT id FROM course_modules WHERE course_id='a392bf83-4908-4807-89a9-95d0acc807c9' AND module_index=3),1,'Icebreaker: “Reto en 6 palabras” para identificar desafíos de negocio.'),
((SELECT id FROM course_modules WHERE course_id='a392bf83-4908-4807-89a9-95d0acc807c9' AND module_index=3),2,'Mapear datos compartibles vs sensibles y diseñar un prompt con intención.'),
((SELECT id FROM course_modules WHERE course_id='a392bf83-4908-4807-89a9-95d0acc807c9' AND module_index=4),1,'Definir el problema real y plantear objetivos SMART.'),
((SELECT id FROM course_modules WHERE course_id='a392bf83-4908-4807-89a9-95d0acc807c9' AND module_index=4),2,'Bosquejar el workflow de integración de IA en 5 pasos.');

COMMIT;
