# -*- coding: utf-8 -*-
from openerp import models,fields,api

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.one
    def _picked_rate(self):
        
        res = {}
       
        res[self.id] = [0.0,0.0]
        
        cursor = self.env.cr
        cursor.execute('''SELECT
                so.id, sum(m.product_qty), mp.state as mp_state
            FROM stock_move m
        LEFT JOIN procurement_order mp on (mp.move_dest_id=m.id)
            LEFT JOIN sale_order_line sol on (sol.id=mp.sale_line_id)
                LEFT JOIN sale_order so on (sol.order_id=so.id)
                    LEFT JOIN stock_picking p on (p.id=m.picking_id)
    WHERE
                mp.id is not null and so.id = %s GROUP BY mp.state, so.id''', (tuple([self.id]),))
        
        for oid, nbr, mp_state in cursor.fetchall():
            if mp_state == 'cancel':
                continue
            if mp_state == 'done':
                res[oid][0] += nbr or 0.0
                res[oid][1] += nbr or 0.0
            else:
                res[oid][1] += nbr or 0.0
                
        for r in res:
            if not res[r][1]:
                self.picked_rate = 0.0
            else:
                self.picked_rate = 100.0 * res[r][0] / res[r][1]
        
        if self.shipped:
            self.picked_rate = 100.0
    
    @api.one
    def _invoiced_rate(self):
        
        if self.invoiced:
            self.invoiced_rate = 100.0
            return
        
        tot = 0.0
        for invoice in self.invoice_ids:
            if invoice.state not in ('draft', 'cancel'):
                tot += invoice.amount_untaxed
        if tot:
            self.invoiced_rate = min(100.0, tot * 100.0 / (self.amount_untaxed or 1.00))
        else:
            self.invoiced_rate = 0.0
 
    picked_rate = fields.Float("Picked Rate",compute=_picked_rate,help="The picking movements that are done")
    invoiced_rate = fields.Float("Invoiced Rate",compute=_invoiced_rate,store=True,help="The Invoice Lines corresponding to the Sale Order Lines")