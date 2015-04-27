# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from openerp import models,fields,api

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.depends('order_line.delay')
    @api.one
    def _get_delivery_date(self):
        dates_list = []
        reference_date = (self.date_confirm and datetime.strptime(self.date_confirm, '%Y-%m-%d')) or datetime.now()
        for line in self.order_line:                
            dt = reference_date + timedelta(days=(line.delay) or 0.0)
            dt_s = dt.strftime('%Y-%m-%d')
            dates_list.append(dt_s)
        if dates_list:
            dates_list.append(self.confirmed_delivery_date)
            self.delivery_date = max(dates_list)
        return
    
    def _get_delivery_date_display(self):
        if self.confirmed_delivery_date:
            self.delivery_date_display = self.confirmed_delivery_date
        else:
            self.delivery_date_display = self.delivery_date
        return
    
    def _get_effective_date(self):
        dates_list = []
        for pick in self.picking_ids:
            if pick.date_done:
                dates_list.append(pick.date_done)
        if dates_list:
            self.effective_date = max(dates_list)
        else:
            self.effective_date = False
        return
    
    delivery_date = fields.Date('Delivery Date', compute=_get_delivery_date, store=True, help="Date on which delivery of products is to be made.")
    confirmed_delivery_date = fields.Date('Confirmed delivery date', help="Date confirmed to the client for the delivery of the order.")
    delivery_date_display = fields.Date('Confirmed delivery date', compute=_get_delivery_date_display, store=True, help="Confirmed delivery date, or if not filled, computed delivery date.")
    requested_date = fields.Date('Requested Date', help="Date on which customer has requested for sales.")
    effective_date = fields.Date('Effective Date', compute=_get_effective_date, store=True, help="Date on which pickings are done.")
    

    def button_change_confirmed_delivery_date(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            updated_date = order.delivery_date   
        return self.write(cr, uid, ids, {'confirmed_delivery_date': updated_date})