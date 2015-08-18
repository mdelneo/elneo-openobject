from openerp import models, fields,api

class product_template(models.Model):
    _inherit = 'product.template'
    
    @api.multi
    @api.onchange('categ_id')
    @api.depends('categ_id')
    def get_categ_family(self):
        for product in self:        
            cat = product.categ_id
            cats = []
            while cat:
                cats.append(cat)
                cat = cat.parent_id
            cats.reverse()
            len_cats = len(cats)              
            if len_cats > 0:
                product.categ_dpt = cats[0].name
            else:
                product.categ_dpt = ''
            if len_cats > 1:
                product.categ_group = cats[1].name
            else:
                product.categ_group = ''
            if len_cats > 2:
                product.categ_family = cats[2].name
            else:
                product.categ_family = ''
            if len_cats > 3:
                product.categ_subfamily = cats[3].name
            else:
                product.categ_subfamily = ''
                
    
    categ_dpt = fields.Char('Department', size=255, compute='get_categ_family', store=True, readonly=True)
    categ_group = fields.Char('Group', size=255, compute='get_categ_family', store=True, readonly=True)
    categ_family = fields.Char('Family', size=255, compute='get_categ_family', store=True, readonly=True)
    categ_subfamily = fields.Char('Sub-Family', size=255, compute='get_categ_family', store=True, readonly=True)
    
class product_category(models.Model):
    
    _inherit = 'product.category'
    
    def _subfamily_search(self, operator, value):
        return [('id','in',self.search(['&','&','&','&',('name','ilike',value),('parent_id','!=',False),('parent_id.parent_id','!=',False),('parent_id.parent_id.parent_id','!=',False)]).get_children_ids())]
    
    def _family_search(self, operator, value):
        return [('id','in',self.search(['&','&','&',('name','ilike',value),('parent_id','!=',False),('parent_id.parent_id','!=',False),('parent_id.parent_id.parent_id','=',False)]).get_children_ids())]
    
    def _group_search(self, operator, value):
        return [('id','in',self.search(['&','&',('name','ilike',value),('parent_id','!=',False),('parent_id.parent_id','=',False)]).get_children_ids())]
    
    def _dpt_search(self, operator, value):
        return [('id','in',self.search(['&',('name','ilike',value),('parent_id','=',False)]).get_children_ids())]
    
    def get_children_ids(self):
        children = self
        categ_ids = [child.id for child in children]
        while children:
            children = self.search([('parent_id','in',[child.id for child in children])])
            categ_ids.extend([child.id for child in children])
        return categ_ids
    
    def _get_family(self):
        if not self.parent_id:
            self.dpt = self.name
        elif self.parent_id and not self.parent_id.parent_id:
            self.dpt = self.parent_id.name
            self.group = self.name
        elif self.parent_id and self.parent_id.parent_id and not self.parent_id.parent_id.parent_id:
            self.dpt = self.parent_id.parent_id.name
            self.group = self.parent_id.name
            self.family = self.name
        else:
            self.dpt = self.parent_id.parent_id.parent_id.name
            self.group = self.parent_id.parent_id.name
            self.family = self.parent_id.name
            self.subfamily = self.name
    
    dpt = fields.Char(compute='_get_family', search='_dpt_search', string="Department", readonly=True)
    group = fields.Char(compute='_get_family', search='_group_search', string="Group", readonly=True)
    family = fields.Char(compute='_get_family', search='_family_search', string="Family", readonly=True)
    subfamily = fields.Char(compute='_get_family', search='_subfamily_search', string="Sub-family", readonly=True)
