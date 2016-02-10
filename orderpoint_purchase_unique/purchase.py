from openerp import models, fields, api
from openerp.tools.translate import _
from datetime import datetime
from dateutil import relativedelta



class ProcurementOrder(models.Model):
    _inherit='procurement.order'
    
    @api.model
    def _run(self,procurement):
        if procurement.rule_id and procurement.rule_id.action == 'buy' and procurement.orderpoint_id:
            unique = self.env['ir.config_parameter'].get_param('orderpoint_purchase_unique.po_for_orderpoints',False)
            #make a purchase order for the procurement
            if unique == 'True':
                return super(ProcurementOrder, self.with_context(from_orderpoint_unique=True,procurement_group_id=procurement.group_id.id))._run(procurement)
                
        return super(ProcurementOrder, self)._run(procurement)


class PurchaseOrder(models.Model):
    _inherit='purchase.order'
    
    @api.returns('self')
    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        if context.get('from_orderpoint_unique',False) and context.get('procurement_group_id',False):
            group_id = context.get('procurement_group_id',False)
            existing_procurement_ids = self.pool.get('procurement.order').search(cr,user,[('group_id','=',group_id),('state','in',['confirmed','running']),('purchase_line_id','!=',False),('orderpoint_id','!=',False)],context=context)
            existing_procurements = self.pool.get('procurement.order').browse(cr,user,existing_procurement_ids,context=context)
            purchase_ids = existing_procurements.mapped('purchase_id.id')
            if purchase_ids:
                args.append(('id','in',purchase_ids))
            else:
                #Force to create ID
                args.append(('id','=',False))
        res = super(PurchaseOrder, self).search(cr, user, args, offset=offset, limit=limit, order=order, context=context, count=count)
        return res
    
