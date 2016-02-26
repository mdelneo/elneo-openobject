'''
Created on Feb 25, 2016

@author: elneo
'''


from openerp import models, fields, api, _

class stock_move(models.Model):
    _inherit = 'stock.move'
    
    returned_moves = fields.Many2many('stock.move','stock_move_returned_move_rel','original_move_id','returned_move_id', string='Returned moves')
    
    @api.one
    def copy(self, default=None):
        new_move = super(stock_move, self).copy(default)
        #only way found to know if it's a return : compare locations (context is not passed as parameter) 
        if self.location_id.id == default.get('location_dest_id') and self.location_dest_id.id == default.get('location_id'):
            self.write({'returned_moves':[(4,new_move.id)]})
        return new_move