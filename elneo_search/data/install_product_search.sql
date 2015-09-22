--CREATE EXTENSION unaccent;

/*
ALTER TABLE product_product ADD COLUMN search_field character varying(4096);
COMMENT ON COLUMN product_product.search_field IS 'Search';

ALTER TABLE product_product ADD COLUMN search_default_code character varying(4096);
COMMENT ON COLUMN product_product.search_default_code IS 'Default code (search)';

ALTER TABLE product_product ADD COLUMN search character varying(4096);
COMMENT ON COLUMN product_product.search IS 'Search';
*/


CREATE OR REPLACE FUNCTION product_search_code(IN text, OUT id integer)
  RETURNS SETOF integer AS
$BODY$   
    DECLARE 
        code_formated text;
    /*If $1 contains "*" replace */
    BEGIN    
    IF ($1 like '%*%') THEN
	select into code_formated replace(search_format_star($1),'*','%');
    	RETURN QUERY select product_product.id 
    	from product_product 
    	WHERE search_default_code like code_formated;
    ELSE
	select into code_formated search_format($1);
	RETURN QUERY select product_product.id 
    	from product_product 
    	WHERE search_default_code like '%'||code_formated||'%';
    END IF;
    END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100
  ROWS 1000;
ALTER FUNCTION product_search_code(text)
  OWNER TO odoo;


CREATE OR REPLACE FUNCTION product_search_column(IN text, OUT id integer)
  RETURNS SETOF integer AS
$BODY$   
    DECLARE 
        code_formated text;
    /*If $1 contains "*" replace */
    BEGIN    
    IF ($1 like '%*%') THEN
	select into code_formated replace(search_format_star($1),'*','[A-Z0-9]*');
    	RETURN QUERY select product_product.id 
    	from product_product 
    	WHERE (product_product.search_field similar to '([A-Z0-9]*\|)*'||code_formated||'(\|[A-Z0-9]*)*');
    ELSE
	select into code_formated search_format($1);
	RETURN QUERY select product_product.id 
    	from product_product 
    	WHERE (product_product.search_field like '%'||code_formated||'%');
    END IF;
    END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100
  ROWS 1000;
ALTER FUNCTION product_search_column(text)
  OWNER TO odoo;


CREATE OR REPLACE FUNCTION product_search_full(IN text, OUT code text, OUT id integer)
  RETURNS SETOF record AS
$BODY$ select distinct product_product.default_code, product_product.id from product_product left join product_template on product_product.product_tmpl_id = product_template.id 
left join product_supplierinfo on product_supplierinfo.product_tmpl_id = product_template.id 
left join ir_translation on ir_translation.res_id = product_template.id and ir_translation.name = 'product.template,name' 
where
product_product.default_code ilike '%'||$1||'%'
or product_product.alias ilike '%'||$1||'%'
or product_supplierinfo.product_name ilike '%'||$1||'%'
or product_supplierinfo.product_code ilike '%'||$1||'%'
or ir_translation.value ilike '%'||$1||'%'
or product_template.name ilike '%'||$1||'%' $BODY$
  LANGUAGE sql VOLATILE
  COST 100
  ROWS 1000;
ALTER FUNCTION product_search_full(text)
  OWNER TO odoo;





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



CREATE OR REPLACE FUNCTION fill_product_search_field(IN integer, OUT res integer)
  RETURNS integer AS
$BODY$     
    update product_product set search_field = search_format_update(req.search), search_default_code = search_format(req.default_code)
from (select product_product.id, substr(concat_ws(' | ',product_product.default_code, product_template.name, product_product.alias, string_agg(product_supplierinfo.product_name,' | '),
string_agg(product_supplierinfo.product_code, ' | '), string_agg(name_translation.value, ' | ')), 0, 4096) as search, product_product.default_code as default_code
from product_product 
left join product_template
	left join product_supplierinfo on product_supplierinfo.product_tmpl_id = product_template.id 
	left join ir_translation name_translation on name_translation.res_id = product_template.id and name_translation.name = 'product.template,name' 
on product_product.product_tmpl_id = product_template.id 
group by product_product.id, product_template.id
) req
where req.id = product_product.id
and product_product.id = $1 RETURNING product_product.id;
$BODY$
  LANGUAGE sql VOLATILE
  COST 100;
ALTER FUNCTION fill_product_search_field(integer)
  OWNER TO odoo;

/*
CREATE OR REPLACE FUNCTION product_fill_search_column(IN integer, OUT res integer)
  RETURNS integer AS
$BODY$ 
    update product_product set search = req.search
from (select product_product.id, substr(concat_ws(' | ',product_product.alias, product_template.name, product_product.default_code, string_agg(product_supplierinfo.product_name,' | '),
string_agg(product_supplierinfo.product_code, ' | '), string_agg(name_translation.value, ' | ')), 0, 4096) as search
from product_product 
left join product_template
	left join product_supplierinfo on product_supplierinfo.product_tmpl_id = product_template.id 
	left join ir_translation name_translation on name_translation.res_id = product_template.id and name_translation.name = 'product.template,name' 
on product_product.product_tmpl_id = product_template.id 
group by product_product.id, product_template.id
) req
where req.id = product_product.id
and product_product.id = $1 RETURNING product_product.id
$BODY$
  LANGUAGE sql VOLATILE
  COST 100;
ALTER FUNCTION product_fill_search_column(integer)
  OWNER TO odoo;
*/

	

CREATE OR REPLACE FUNCTION fill_all_product_search(OUT id integer)
  RETURNS SETOF integer AS
$BODY$   
    DECLARE 
        r RECORD;    
    BEGIN    
	FOR r IN SELECT product_product.id FROM product_product where active
	LOOP
		PERFORM fill_product_search_field(r.id);
	END LOOP;
	RETURN;
    END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100
  ROWS 1000;
ALTER FUNCTION product_search_column(text)
  OWNER TO odoo;

-- Function: fill_trg_ir_translation()

-- DROP FUNCTION fill_trg_ir_translation();

CREATE OR REPLACE FUNCTION fill_trg_ir_translation()
  RETURNS trigger AS
$BODY$
    DECLARE 
        product_id int;
    BEGIN	

	IF (TG_OP = 'DELETE') THEN		
		select into product_id p.id 
		from ir_translation t 
		left join product_product p 
		on t.res_id = p.product_tmpl_id and t.name = 'product.template,name' 
		where t.id = old.id;	
		perform fill_product_search_field(product_id);
		return old;
        ELSIF (TG_OP = 'UPDATE' OR TG_OP = 'INSERT') THEN	
		select into product_id p.id 
		from ir_translation t 
		left join product_product p 
		on t.res_id = p.product_tmpl_id and t.name = 'product.template,name' 
		where t.id = NEW.id;	
		perform fill_product_search_field(product_id);
		return new;
        END IF;   

        return null;  
    
	
    END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION fill_trg_ir_translation()
  OWNER TO odoo;

-- Function: fill_trg_product_product()

-- DROP FUNCTION fill_trg_product_product();

CREATE OR REPLACE FUNCTION fill_trg_product_product()
  RETURNS trigger AS
$BODY$
    BEGIN	
	IF (TG_OP = 'DELETE') THEN		
            perform fill_product_search_field(OLD.id);
            RETURN OLD;
        ELSIF (TG_OP = 'UPDATE' OR TG_OP = 'INSERT') THEN	
            perform fill_product_search_field(NEW.id);
            RETURN NEW;        
        END IF;   

        return null;     
        
    END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION fill_trg_product_product()
  OWNER TO odoo;
-- Function: fill_trg_product_supplierinfo()

-- DROP FUNCTION fill_trg_product_supplierinfo();

CREATE OR REPLACE FUNCTION fill_trg_product_supplierinfo()
  RETURNS trigger AS
$BODY$
    DECLARE 
        product_id int;
    BEGIN	
	IF (TG_OP = 'DELETE') THEN		
		select into product_id p.id from product_supplierinfo ps left join product_product p on p.product_tmpl_id = ps.product_id where ps.id = old.id;
		perform fill_product_search_field(product_id);
		return old;
        ELSIF (TG_OP = 'UPDATE' OR TG_OP = 'INSERT') THEN	
		select into product_id p.id from product_supplierinfo ps left join product_product p on p.product_tmpl_id = ps.product_id where ps.id = NEW.id;
		perform fill_product_search_field(product_id);
		return new;
        END IF;   

        return null;  
    
	
    END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION fill_trg_product_supplierinfo()
  OWNER TO odoo;

-- Function: fill_trg_product_template()

-- DROP FUNCTION fill_trg_product_template();

CREATE OR REPLACE FUNCTION fill_trg_product_template()
  RETURNS trigger AS
$BODY$
    DECLARE 
        product_id int;
    BEGIN	

	IF (TG_OP = 'DELETE') THEN		
		select into product_id p.id from product_template pt left join product_product p on p.product_tmpl_id = pt.id where pt.id = OLD.id;	
		perform fill_product_search_field(product_id);
		return OLD;
        ELSIF (TG_OP = 'UPDATE' OR TG_OP = 'INSERT') THEN	
		select into product_id p.id from product_template pt left join product_product p on p.product_tmpl_id = pt.id where pt.id = NEW.id;	
		perform fill_product_search_field(product_id);
		return new;
        END IF;   

        return null;  
	
    END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION fill_trg_product_template()
  OWNER TO odoo;


----------------
--- TRIGGERS ---
----------------

DROP TRIGGER IF EXISTS trg_search_ir_translation ON ir_translation;
CREATE TRIGGER trg_search_ir_translation
  AFTER INSERT OR DELETE
  ON ir_translation
  FOR EACH ROW
  EXECUTE PROCEDURE fill_trg_ir_translation();

DROP TRIGGER IF EXISTS trg_search_ir_translation_update ON ir_translation;
CREATE TRIGGER trg_search_ir_translation_update
  AFTER UPDATE
  ON ir_translation
  FOR EACH ROW
  WHEN ((((new.name)::text = 'product.template,name'::text) AND (old.value IS DISTINCT FROM new.value)))
  EXECUTE PROCEDURE fill_trg_ir_translation();

DROP TRIGGER IF EXISTS trg_search_product_product ON product_product;
CREATE TRIGGER trg_search_product_product
  AFTER INSERT OR DELETE
  ON product_product
  FOR EACH ROW
  EXECUTE PROCEDURE fill_trg_product_product();

DROP TRIGGER IF EXISTS trg_search_product_product_update ON product_product;
CREATE TRIGGER trg_search_product_product_update
  AFTER UPDATE
  ON product_product
  FOR EACH ROW
  WHEN ((((old.alias)::text IS DISTINCT FROM (new.alias)::text) OR ((old.default_code)::text IS DISTINCT FROM (new.default_code)::text)))
  EXECUTE PROCEDURE fill_trg_product_product();

DROP TRIGGER IF EXISTS trg_search_product_supplierinfo ON product_supplierinfo;
CREATE TRIGGER trg_search_product_supplierinfo
  AFTER INSERT OR DELETE
  ON product_supplierinfo
  FOR EACH ROW
  EXECUTE PROCEDURE fill_trg_product_supplierinfo();

DROP TRIGGER IF EXISTS trg_search_product_supplierinfo_update ON product_supplierinfo;
CREATE TRIGGER trg_search_product_supplierinfo_update
  AFTER UPDATE
  ON product_supplierinfo
  FOR EACH ROW
  WHEN ((((old.product_name)::text IS DISTINCT FROM (new.product_name)::text) OR ((old.product_code)::text IS DISTINCT FROM (new.product_code)::text)))
  EXECUTE PROCEDURE fill_trg_product_supplierinfo();

DROP TRIGGER IF EXISTS trg_search_product_template ON product_template;
CREATE TRIGGER trg_search_product_template
  AFTER INSERT OR DELETE
  ON product_template
  FOR EACH ROW
  EXECUTE PROCEDURE fill_trg_product_template();

DROP TRIGGER IF EXISTS trg_search_product_template_update ON product_template;
CREATE TRIGGER trg_search_product_template_update
  AFTER UPDATE
  ON product_template
  FOR EACH ROW
  WHEN (((old.name)::text IS DISTINCT FROM (new.name)::text))
  EXECUTE PROCEDURE fill_trg_product_template();





-- Function: product_fill_search_column_trigger()

-- DROP FUNCTION product_fill_search_column_trigger();
/*
CREATE OR REPLACE FUNCTION product_fill_search_column_trigger()
  RETURNS trigger AS
$BODY$
    BEGIN
        select * from product_fill_search_column(NEW.id);
        return new;
    END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION product_fill_search_column_trigger()
  OWNER TO odoo;
*/

-- select fill_all_product_search()

