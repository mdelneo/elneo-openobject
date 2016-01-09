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
            return super(ProcurementOrder, self.with_context(from_orderpoint=True,existing_purchases=procs.mapped('purchase_id.id')))._run(procurement)
        return super(ProcurementOrder, self)._run(procurement)


class PurchaseOrder(models.Model):
    _inherit='purchase.order'
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self._context.get('from_orderpoint',False) and self.env.context.get('existing_purchases',False):
            args.append(('id','not in',self.env.context.get('existing_purchases')))
        res = super(PurchaseOrder, self).search(args, offset=offset, limit=limit, order=order, count=count)
        return res
