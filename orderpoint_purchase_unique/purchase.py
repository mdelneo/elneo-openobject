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
                procs = self.search([('state','in',['running','exception']),('group_id','!=',False),('purchase_id','!=',False)])
                if procs:
                    return super(ProcurementOrder, self.with_context(from_orderpoint=True,existing_purchases=procs.mapped('purchase_id.id')))._run(procurement)
        return super(ProcurementOrder, self)._run(procurement)


class PurchaseOrder(models.Model):
    _inherit='purchase.order'
    
    @api.returns('self')
    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        if context.get('from_orderpoint',False) and context.get('existing_purchases',False):
            args.append(('id','not in',context.get('existing_purchases')))
        res = super(PurchaseOrder, self).search(cr, user, args, offset=offset, limit=limit, order=order, context=context, count=count)
        return res
    
