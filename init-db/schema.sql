-- =============================================================================
-- DemoWhatsappAgent — PostgreSQL Schema
-- DB: demobot  |  User: demobot
-- Actualizado: 2026-07-14  (al dia con EP-006: conversaciones + radicados)
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

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

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

CREATE OR REPLACE FUNCTION public.trg_set_actualizado_en() RETURNS trigger
    LANGUAGE plpgsql AS $$
BEGIN
    NEW.actualizado_en = now();
    RETURN NEW;
END;
$$;


-- =============================================================================
-- TABLES  (orden: primero las que no tienen FKs dependientes)
-- =============================================================================

SET default_tablespace = '';
SET default_table_access_method = heap;


-- ---------------------------------------------------------------------------
-- areas
-- ---------------------------------------------------------------------------
CREATE TABLE public.areas (
    id          integer NOT NULL,
    nombre      character varying NOT NULL,
    creado_en   timestamp without time zone DEFAULT now(),
    actualizado_en timestamp without time zone DEFAULT now()
);

CREATE SEQUENCE public.areas_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.areas_id_seq OWNED BY public.areas.id;
ALTER TABLE ONLY public.areas ALTER COLUMN id SET DEFAULT nextval('public.areas_id_seq'::regclass);


-- ---------------------------------------------------------------------------
-- modulos
-- ---------------------------------------------------------------------------
CREATE TABLE public.modulos (
    id                  integer NOT NULL,
    nombre              character varying NOT NULL,
    precio_mensual_cop  integer NOT NULL,
    creado_en           timestamp without time zone DEFAULT now(),
    actualizado_en      timestamp without time zone DEFAULT now()
);

CREATE SEQUENCE public.modulos_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.modulos_id_seq OWNED BY public.modulos.id;
ALTER TABLE ONLY public.modulos ALTER COLUMN id SET DEFAULT nextval('public.modulos_id_seq'::regclass);


-- ---------------------------------------------------------------------------
-- contactos  (sin FK saliente — es la raíz de la cadena de personas)
-- ---------------------------------------------------------------------------
CREATE TABLE public.contactos (
    telefono             character varying NOT NULL,
    nombre               character varying NOT NULL,
    correo               character varying,
    ciudad               character varying,
    atendido_por         integer,                             -- FK -> agentes.id (abajo)
    conectado_en         timestamp without time zone,
    consentimiento_datos boolean DEFAULT false,
    canal                character varying DEFAULT 'meta',
    creado_en            timestamp without time zone DEFAULT now(),
    actualizado_en       timestamp without time zone DEFAULT now()
);


-- ---------------------------------------------------------------------------
-- agentes
-- ---------------------------------------------------------------------------
CREATE TABLE public.agentes (
    id             integer NOT NULL,
    nombre         character varying NOT NULL,
    email          character varying NOT NULL,
    telefono       character varying,
    hora_inicio    character varying NOT NULL,
    hora_fin       character varying NOT NULL,
    activo         boolean,
    area_id        integer NOT NULL,
    creado_en      timestamp without time zone DEFAULT now(),
    actualizado_en timestamp without time zone DEFAULT now()
);

CREATE SEQUENCE public.agentes_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.agentes_id_seq OWNED BY public.agentes.id;
ALTER TABLE ONLY public.agentes ALTER COLUMN id SET DEFAULT nextval('public.agentes_id_seq'::regclass);


-- ---------------------------------------------------------------------------
-- clientes  (extensión de contactos con datos empresa)
-- ---------------------------------------------------------------------------
CREATE TABLE public.clientes (
    telefono              character varying NOT NULL,
    numero_identificacion character varying,
    nit_empresa           character varying,
    tipo                  character varying NOT NULL DEFAULT 'lead',
    nombre_empresa        character varying,
    sector_empresa        character varying,
    actividad_empresa     character varying,
    empleados_empresa     character varying,
    creado_en             timestamp without time zone DEFAULT now(),
    actualizado_en        timestamp without time zone DEFAULT now()
);


-- ---------------------------------------------------------------------------
-- radicados  (EP-006 — registro persistente de cada caso de soporte)
-- ---------------------------------------------------------------------------
CREATE TABLE public.radicados (
    id           integer NOT NULL,
    codigo       character varying UNIQUE,
    telefono     character varying NOT NULL,
    area_id      integer NOT NULL,
    resumen      character varying NOT NULL,
    estado       character varying NOT NULL DEFAULT 'abierto',
    modo         character varying,                          -- conectado | notificacion_con_contacto | notificacion
    agente_id    integer,
    crm_case_id  character varying,
    email_enviado boolean DEFAULT false,
    resuelto_en  timestamp without time zone,              -- NULL = abierto; caso cerrado en este instante
    creado_en    timestamp without time zone DEFAULT now(),
    actualizado_en timestamp without time zone DEFAULT now()
);

CREATE SEQUENCE public.radicados_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.radicados_id_seq OWNED BY public.radicados.id;
ALTER TABLE ONLY public.radicados ALTER COLUMN id SET DEFAULT nextval('public.radicados_id_seq'::regclass);


-- ---------------------------------------------------------------------------
-- conversaciones  (EP-006 — sesión de conversación por usuario)
-- ---------------------------------------------------------------------------
CREATE TABLE public.conversaciones (
    id              integer NOT NULL,
    telefono        character varying NOT NULL,
    radicado_id     integer,
    estado          character varying NOT NULL DEFAULT 'abierta',
    tipo_solicitud  character varying,
    motivo_cierre   character varying,
    espera_desde    timestamp without time zone,
    espera_hasta    timestamp without time zone,
    duracion_espera_seg integer GENERATED ALWAYS AS ((EXTRACT(epoch FROM (espera_hasta - espera_desde)))::integer) STORED,
    creado_en       timestamp without time zone DEFAULT now(),
    actualizado_en  timestamp without time zone DEFAULT now()
);

CREATE SEQUENCE public.conversaciones_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.conversaciones_id_seq OWNED BY public.conversaciones.id;
ALTER TABLE ONLY public.conversaciones ALTER COLUMN id SET DEFAULT nextval('public.conversaciones_id_seq'::regclass);


-- ---------------------------------------------------------------------------
-- mensajes  (historial de mensajes; conversacion_id añadido en EP-006)
-- ---------------------------------------------------------------------------
CREATE TABLE public.mensajes (
    id              integer NOT NULL,
    telefono        character varying,
    conversacion_id integer,                            -- FK -> conversaciones.id (EP-006)
    role            character varying,
    content         character varying,
    "timestamp"     timestamp without time zone
);

CREATE SEQUENCE public.mensajes_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.mensajes_id_seq OWNED BY public.mensajes.id;
ALTER TABLE ONLY public.mensajes ALTER COLUMN id SET DEFAULT nextval('public.mensajes_id_seq'::regclass);


-- ---------------------------------------------------------------------------
-- ofertas
-- ---------------------------------------------------------------------------
CREATE TABLE public.ofertas (
    id             integer NOT NULL,
    modulo_id      integer NOT NULL,
    descuento_pct  integer NOT NULL,
    fecha_inicio   date NOT NULL,
    fecha_fin      date NOT NULL,
    activo         boolean,
    creado_en      timestamp without time zone DEFAULT now(),
    actualizado_en timestamp without time zone DEFAULT now()
);

CREATE SEQUENCE public.ofertas_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.ofertas_id_seq OWNED BY public.ofertas.id;
ALTER TABLE ONLY public.ofertas ALTER COLUMN id SET DEFAULT nextval('public.ofertas_id_seq'::regclass);


-- ---------------------------------------------------------------------------
-- combos
-- ---------------------------------------------------------------------------
CREATE TABLE public.combos (
    id               integer NOT NULL,
    nombre           character varying NOT NULL,
    descripcion      character varying,
    modulos          character varying NOT NULL,
    precio_anual_cop integer NOT NULL,
    creado_en        timestamp without time zone DEFAULT now(),
    actualizado_en   timestamp without time zone DEFAULT now()
);

CREATE SEQUENCE public.combos_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.combos_id_seq OWNED BY public.combos.id;
ALTER TABLE ONLY public.combos ALTER COLUMN id SET DEFAULT nextval('public.combos_id_seq'::regclass);



-- ---------------------------------------------------------------------------
-- parametros
-- ---------------------------------------------------------------------------
CREATE TABLE public.parametros (
    clave          character varying NOT NULL,
    valor          character varying NOT NULL,
    descripcion    character varying,
    creado_en      timestamp without time zone DEFAULT now(),
    actualizado_en timestamp without time zone DEFAULT now()
);





-- =============================================================================
-- PRIMARY KEYS
-- =============================================================================

ALTER TABLE ONLY public.agentes        ADD CONSTRAINT agentes_pkey        PRIMARY KEY (id);
ALTER TABLE ONLY public.areas          ADD CONSTRAINT areas_pkey           PRIMARY KEY (id);
ALTER TABLE ONLY public.areas          ADD CONSTRAINT areas_nombre_key     UNIQUE (nombre);
ALTER TABLE ONLY public.clientes       ADD CONSTRAINT clientes_pkey        PRIMARY KEY (telefono);
ALTER TABLE ONLY public.contactos      ADD CONSTRAINT contactos_pkey       PRIMARY KEY (telefono);
ALTER TABLE ONLY public.conversaciones ADD CONSTRAINT conversaciones_pkey  PRIMARY KEY (id);
ALTER TABLE ONLY public.mensajes       ADD CONSTRAINT mensajes_pkey        PRIMARY KEY (id);
ALTER TABLE ONLY public.combos         ADD CONSTRAINT combos_pkey         PRIMARY KEY (id);
ALTER TABLE ONLY public.combos         ADD CONSTRAINT combos_nombre_key   UNIQUE (nombre);
ALTER TABLE ONLY public.modulos        ADD CONSTRAINT modulos_pkey         PRIMARY KEY (id);
ALTER TABLE ONLY public.modulos        ADD CONSTRAINT modulos_nombre_key   UNIQUE (nombre);
ALTER TABLE ONLY public.ofertas        ADD CONSTRAINT ofertas_pkey         PRIMARY KEY (id);
ALTER TABLE ONLY public.parametros     ADD CONSTRAINT parametros_pkey      PRIMARY KEY (clave);
ALTER TABLE ONLY public.radicados      ADD CONSTRAINT radicados_pkey       PRIMARY KEY (id);


-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX ix_agentes_area_id              ON public.agentes        USING btree (area_id);
CREATE INDEX ix_contactos_atendido_por       ON public.contactos      USING btree (atendido_por) WHERE (atendido_por IS NOT NULL);
CREATE INDEX ix_conversaciones_telefono      ON public.conversaciones USING btree (telefono);
CREATE INDEX ix_conversaciones_estado        ON public.conversaciones USING btree (estado);
CREATE INDEX ix_conversaciones_espera        ON public.conversaciones USING btree (espera_desde, espera_hasta);
CREATE INDEX ix_mensajes_telefono            ON public.mensajes       USING btree (telefono);
CREATE INDEX ix_mensajes_conversacion_id     ON public.mensajes       USING btree (conversacion_id) WHERE (conversacion_id IS NOT NULL);
CREATE INDEX ix_ofertas_modulo_id            ON public.ofertas        USING btree (modulo_id);
CREATE INDEX ix_radicados_telefono           ON public.radicados      USING btree (telefono);
CREATE INDEX ix_radicados_estado             ON public.radicados      USING btree (estado);


-- =============================================================================
-- TRIGGERS  (set actualizado_en automáticamente)
-- =============================================================================

CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.agentes        FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();
CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.areas          FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();
CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.clientes       FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();
CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.contactos      FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();
CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.conversaciones FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();
CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.mensajes       FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();
CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.combos         FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();
CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.modulos        FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();
CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.ofertas        FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();
CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.parametros     FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();
CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.radicados      FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();


-- =============================================================================
-- FOREIGN KEYS
-- =============================================================================

-- agentes -> areas
ALTER TABLE ONLY public.agentes
    ADD CONSTRAINT agentes_area_id_fkey FOREIGN KEY (area_id) REFERENCES public.areas(id);

-- clientes -> contactos
ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_telefono_fkey FOREIGN KEY (telefono) REFERENCES public.contactos(telefono);



-- contactos -> agentes (auto-referencia diferida: agentes depende de areas, areas no depende de nadie)
ALTER TABLE ONLY public.contactos
    ADD CONSTRAINT contactos_atendido_por_fkey FOREIGN KEY (atendido_por) REFERENCES public.agentes(id);

-- conversaciones -> contactos, radicados
ALTER TABLE ONLY public.conversaciones
    ADD CONSTRAINT conversaciones_telefono_fkey   FOREIGN KEY (telefono)    REFERENCES public.contactos(telefono);
ALTER TABLE ONLY public.conversaciones
    ADD CONSTRAINT conversaciones_radicado_id_fkey FOREIGN KEY (radicado_id) REFERENCES public.radicados(id);

-- mensajes -> conversaciones
ALTER TABLE ONLY public.mensajes
    ADD CONSTRAINT mensajes_conversacion_id_fkey FOREIGN KEY (conversacion_id) REFERENCES public.conversaciones(id);

-- ofertas -> modulos
ALTER TABLE ONLY public.ofertas
    ADD CONSTRAINT ofertas_modulo_id_fkey FOREIGN KEY (modulo_id) REFERENCES public.modulos(id);

-- radicados -> contactos, areas, agentes
ALTER TABLE ONLY public.radicados
    ADD CONSTRAINT radicados_telefono_fkey  FOREIGN KEY (telefono)  REFERENCES public.contactos(telefono);
ALTER TABLE ONLY public.radicados
    ADD CONSTRAINT radicados_area_id_fkey   FOREIGN KEY (area_id)   REFERENCES public.areas(id);
ALTER TABLE ONLY public.radicados
    ADD CONSTRAINT radicados_agente_id_fkey FOREIGN KEY (agente_id) REFERENCES public.agentes(id);
