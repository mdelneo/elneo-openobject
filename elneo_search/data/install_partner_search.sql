CREATE EXTENSION IF NOT EXISTS unaccent;

-- Format function

CREATE OR REPLACE FUNCTION search_format(IN text, OUT text)
  RETURNS text AS
$BODY$
	SELECT regexp_replace(upper(unaccent($1)), '[^a-zA-Z0-9]+', '','g');
$BODY$
  LANGUAGE sql VOLATILE
  COST 100;
ALTER FUNCTION search_format(text)
  OWNER TO odoo;


CREATE OR REPLACE FUNCTION search_format_star(IN text, OUT text)
  RETURNS text AS
$BODY$
	SELECT regexp_replace(upper(unaccent($1)), '[^a-zA-Z0-9|*]+', '','g');
$BODY$
  LANGUAGE sql VOLATILE
  COST 100;
ALTER FUNCTION search_format_star(text)
  OWNER TO odoo;

  
CREATE OR REPLACE FUNCTION search_format_update(IN text, OUT text)
  RETURNS text AS
$BODY$
	SELECT regexp_replace(upper(unaccent($1)), '[^a-zA-Z0-9|]+', '','g');
$BODY$
  LANGUAGE sql VOLATILE
  COST 100;
ALTER FUNCTION search_format_update(text)
  OWNER TO odoo;


-- Add fields

DO $$
	BEGIN
		BEGIN
			ALTER TABLE res_partner ADD COLUMN search_field character varying(4096);
			COMMENT ON COLUMN res_partner.search_field IS 'Search';
		EXCEPTION
			WHEN duplicate_column THEN RAISE NOTICE 'column search_field already exists in res_partner.';
		END;
	END;
$$;

DO $$
	BEGIN
		BEGIN
			ALTER TABLE res_partner ADD COLUMN alias character varying(255);
			COMMENT ON COLUMN res_partner.alias IS 'Alias';
		EXCEPTION
			WHEN duplicate_column THEN RAISE NOTICE 'column alias already exists in res_partner.';
		END;
	END;
$$;


-- Search function

CREATE OR REPLACE FUNCTION partner_search_column(IN text, OUT id integer)
  RETURNS SETOF integer AS
$BODY$   
    DECLARE 
        code_formated text;
    /*If $1 contains "*" replace */
    BEGIN    
    IF ($1 like '%*%') THEN
	select into code_formated replace(search_format_star($1),'*','[A-Z0-9]*');
    	RETURN QUERY select res_partner.id 
    	from res_partner 
    	WHERE (res_partner.search_field similar to '([A-Z0-9]*\|)*'||code_formated||'(\|[A-Z0-9]*)*');
    ELSE
	select into code_formated search_format($1);
	RETURN QUERY select res_partner.id 
    	from res_partner 
    	WHERE (res_partner.search_field like '%'||code_formated||'%');
    END IF;
    END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100
  ROWS 1000;
ALTER FUNCTION partner_search_column(text)
  OWNER TO odoo;


-- General fill function

CREATE OR REPLACE FUNCTION fill_partner_search_field(IN integer, OUT res integer)
  RETURNS integer AS
$BODY$     
    update res_partner set search_field = search_format_update(req.search)
from (
	select 
		res_partner.id, 
		substr(concat_ws(' | ',res_partner.name, res_partner.ref, res_partner.alias,res_partner.vat), 0, 4096) as search
	from res_partner 
) req
where req.id = res_partner.id
and res_partner.id = $1 RETURNING res_partner.id;
$BODY$
  LANGUAGE sql VOLATILE
  COST 100;
ALTER FUNCTION fill_partner_search_field(integer)
  OWNER TO odoo;


	
-- Child table fill functions

CREATE OR REPLACE FUNCTION fill_trg_res_partner()
  RETURNS trigger AS
$BODY$
    BEGIN	
	IF (TG_OP = 'DELETE') THEN		
            perform fill_partner_search_field(OLD.id);
            RETURN OLD;
        ELSIF (TG_OP = 'UPDATE' OR TG_OP = 'INSERT') THEN	
            perform fill_partner_search_field(NEW.id);
            RETURN NEW;        
        END IF;   

        return null;     
        
    END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION fill_trg_res_partner()
  OWNER TO odoo;

CREATE OR REPLACE FUNCTION fill_all_partner_search(OUT id integer)
  RETURNS SETOF integer AS
$BODY$   
    DECLARE 
        r RECORD;    
    BEGIN    
	FOR r IN SELECT res_partner.id FROM res_partner where active and search_field is null
	LOOP		
		PERFORM fill_partner_search_field(r.id);
	END LOOP;
	RETURN;
    END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100
  ROWS 1000;
ALTER FUNCTION partner_search_column(text)
  OWNER TO odoo;


-- TRIGGERS 

DROP TRIGGER IF EXISTS trg_search_res_partner ON res_partner;
CREATE TRIGGER trg_search_res_partner
  AFTER INSERT OR DELETE
  ON res_partner
  FOR EACH ROW
  EXECUTE PROCEDURE fill_trg_res_partner();

DROP TRIGGER IF EXISTS trg_search_res_partner_update ON res_partner;
CREATE TRIGGER trg_search_res_partner_update
  AFTER UPDATE
  ON res_partner
  FOR EACH ROW
  WHEN 
	(
		((old.ref)::text IS DISTINCT FROM (new.ref)::text) OR 
		((old.name)::text IS DISTINCT FROM (new.name)::text) OR
		((old.alias)::text IS DISTINCT FROM (new.alias)::text) OR
		((old.vat)::text IS DISTINCT FROM (new.vat)::text)
	)
  EXECUTE PROCEDURE fill_trg_res_partner();


DO $$
	BEGIN
		RAISE NOTICE 'fill search_field for all partners...';
		perform fill_all_partner_search();
		RAISE NOTICE '...ok !';
	END;
$$;