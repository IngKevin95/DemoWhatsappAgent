--
-- PostgreSQL database dump
--

\restrict mEDenqiDPie6JKHUWHOJ5cjolPzrSPBIkEZyiKVezl9KRAoqjGaOJKR6ophPRN0

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

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

--
-- Name: trg_set_actualizado_en(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_set_actualizado_en() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.actualizado_en = now();
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agentes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agentes (
    id integer NOT NULL,
    nombre character varying NOT NULL,
    email character varying NOT NULL,
    telefono character varying,
    hora_inicio character varying NOT NULL,
    hora_fin character varying NOT NULL,
    activo boolean,
    creado_en timestamp without time zone DEFAULT now(),
    actualizado_en timestamp without time zone DEFAULT now(),
    area_id integer NOT NULL
);


--
-- Name: agentes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agentes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agentes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agentes_id_seq OWNED BY public.agentes.id;


--
-- Name: areas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.areas (
    id integer NOT NULL,
    nombre character varying NOT NULL,
    creado_en timestamp without time zone DEFAULT now(),
    actualizado_en timestamp without time zone DEFAULT now()
);


--
-- Name: areas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.areas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: areas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.areas_id_seq OWNED BY public.areas.id;


--
-- Name: clientes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clientes (
    telefono character varying NOT NULL,
    numero_identificacion character varying,
    nit_empresa character varying,
    tipo character varying NOT NULL DEFAULT 'lead',
    nombre_empresa character varying,
    sector_empresa character varying,
    actividad_empresa character varying,
    empleados_empresa character varying,
    creado_en timestamp without time zone DEFAULT now(),
    actualizado_en timestamp without time zone DEFAULT now()
);


--
-- Name: cola_espera; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cola_espera (
    telefono character varying NOT NULL,
    desde timestamp without time zone DEFAULT now(),
    hasta timestamp without time zone,
    creado_en timestamp without time zone DEFAULT now(),
    actualizado_en timestamp without time zone DEFAULT now(),
    agente_id integer,
    duracion_seg integer GENERATED ALWAYS AS ((EXTRACT(epoch FROM (hasta - desde)))::integer) STORED,
    area_id integer NOT NULL
);


--
-- Name: contactos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contactos (
    telefono character varying NOT NULL,
    nombre character varying NOT NULL,
    empresa character varying,
    correo character varying,
    atendido_por integer,
    conectado_en timestamp without time zone,
    creado_en timestamp without time zone DEFAULT now(),
    actualizado_en timestamp without time zone DEFAULT now()
);


--
-- Name: mensajes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mensajes (
    id integer NOT NULL,
    telefono character varying,
    role character varying,
    content character varying,
    "timestamp" timestamp without time zone,
    area_id integer
);


--
-- Name: mensajes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.mensajes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mensajes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.mensajes_id_seq OWNED BY public.mensajes.id;


--
-- Name: modulos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.modulos (
    id integer NOT NULL,
    nombre character varying NOT NULL,
    precio_mensual_cop integer NOT NULL,
    creado_en timestamp without time zone DEFAULT now(),
    actualizado_en timestamp without time zone DEFAULT now()
);


--
-- Name: modulos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.modulos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: modulos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.modulos_id_seq OWNED BY public.modulos.id;


--
-- Name: ofertas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ofertas (
    id integer NOT NULL,
    modulo_id integer NOT NULL,
    descuento_pct integer NOT NULL,
    fecha_inicio date NOT NULL,
    fecha_fin date NOT NULL,
    activo boolean,
    creado_en timestamp without time zone DEFAULT now(),
    actualizado_en timestamp without time zone DEFAULT now()
);


--
-- Name: ofertas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ofertas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ofertas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ofertas_id_seq OWNED BY public.ofertas.id;


--
-- Name: parametros; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parametros (
    clave character varying NOT NULL,
    valor character varying NOT NULL,
    descripcion character varying,
    creado_en timestamp without time zone DEFAULT now(),
    actualizado_en timestamp without time zone DEFAULT now()
);


--
-- Name: agentes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agentes ALTER COLUMN id SET DEFAULT nextval('public.agentes_id_seq'::regclass);


--
-- Name: areas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.areas ALTER COLUMN id SET DEFAULT nextval('public.areas_id_seq'::regclass);


--
-- Name: mensajes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes ALTER COLUMN id SET DEFAULT nextval('public.mensajes_id_seq'::regclass);


--
-- Name: modulos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modulos ALTER COLUMN id SET DEFAULT nextval('public.modulos_id_seq'::regclass);


--
-- Name: ofertas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ofertas ALTER COLUMN id SET DEFAULT nextval('public.ofertas_id_seq'::regclass);


--
-- Name: agentes agentes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agentes
    ADD CONSTRAINT agentes_pkey PRIMARY KEY (id);


--
-- Name: areas areas_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.areas
    ADD CONSTRAINT areas_nombre_key UNIQUE (nombre);


--
-- Name: areas areas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.areas
    ADD CONSTRAINT areas_pkey PRIMARY KEY (id);


--
-- Name: clientes clientes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_pkey PRIMARY KEY (telefono);


--
-- Name: cola_espera cola_espera_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cola_espera
    ADD CONSTRAINT cola_espera_pkey PRIMARY KEY (telefono);


--
-- Name: contactos contactos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contactos
    ADD CONSTRAINT contactos_pkey PRIMARY KEY (telefono);


--
-- Name: mensajes mensajes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes
    ADD CONSTRAINT mensajes_pkey PRIMARY KEY (id);


--
-- Name: modulos modulos_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modulos
    ADD CONSTRAINT modulos_nombre_key UNIQUE (nombre);


--
-- Name: modulos modulos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modulos
    ADD CONSTRAINT modulos_pkey PRIMARY KEY (id);


--
-- Name: ofertas ofertas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ofertas
    ADD CONSTRAINT ofertas_pkey PRIMARY KEY (id);


--
-- Name: parametros parametros_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parametros
    ADD CONSTRAINT parametros_pkey PRIMARY KEY (clave);


--
-- Name: ix_agentes_area_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agentes_area_id ON public.agentes USING btree (area_id);


--
-- Name: ix_cola_espera_area_id_hasta; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cola_espera_area_id_hasta ON public.cola_espera USING btree (area_id, hasta);


--
-- Name: ix_contactos_atendido_por; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contactos_atendido_por ON public.contactos USING btree (atendido_por) WHERE (atendido_por IS NOT NULL);


--
-- Name: ix_mensajes_area_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mensajes_area_id ON public.mensajes USING btree (area_id) WHERE (area_id IS NOT NULL);


--
-- Name: ix_mensajes_telefono; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mensajes_telefono ON public.mensajes USING btree (telefono);


--
-- Name: ix_ofertas_modulo_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ofertas_modulo_id ON public.ofertas USING btree (modulo_id);


--
-- Name: agentes set_actualizado_en; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.agentes FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();


--
-- Name: clientes set_actualizado_en; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.clientes FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();


--
-- Name: cola_espera set_actualizado_en; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.cola_espera FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();


--
-- Name: contactos set_actualizado_en; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.contactos FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();


--
-- Name: modulos set_actualizado_en; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.modulos FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();


--
-- Name: ofertas set_actualizado_en; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.ofertas FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();


--
-- Name: parametros set_actualizado_en; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER set_actualizado_en BEFORE UPDATE ON public.parametros FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();


--
-- Name: areas trg_areas_actualizado_en; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_areas_actualizado_en BEFORE UPDATE ON public.areas FOR EACH ROW EXECUTE FUNCTION public.trg_set_actualizado_en();


--
-- Name: agentes agentes_area_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agentes
    ADD CONSTRAINT agentes_area_id_fkey FOREIGN KEY (area_id) REFERENCES public.areas(id);


--
-- Name: clientes clientes_telefono_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_telefono_fkey FOREIGN KEY (telefono) REFERENCES public.contactos(telefono);


--
-- Name: cola_espera cola_espera_agente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cola_espera
    ADD CONSTRAINT cola_espera_agente_id_fkey FOREIGN KEY (agente_id) REFERENCES public.agentes(id);


--
-- Name: cola_espera cola_espera_area_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cola_espera
    ADD CONSTRAINT cola_espera_area_id_fkey FOREIGN KEY (area_id) REFERENCES public.areas(id);


--
-- Name: cola_espera cola_espera_telefono_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cola_espera
    ADD CONSTRAINT cola_espera_telefono_fkey FOREIGN KEY (telefono) REFERENCES public.contactos(telefono);


--
-- Name: contactos contactos_atendido_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contactos
    ADD CONSTRAINT contactos_atendido_por_fkey FOREIGN KEY (atendido_por) REFERENCES public.agentes(id);


--
-- Name: mensajes mensajes_area_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensajes
    ADD CONSTRAINT mensajes_area_id_fkey FOREIGN KEY (area_id) REFERENCES public.areas(id);


--
-- Name: ofertas ofertas_modulo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ofertas
    ADD CONSTRAINT ofertas_modulo_id_fkey FOREIGN KEY (modulo_id) REFERENCES public.modulos(id);


--
-- PostgreSQL database dump complete
--

\unrestrict mEDenqiDPie6JKHUWHOJ5cjolPzrSPBIkEZyiKVezl9KRAoqjGaOJKR6ophPRN0

