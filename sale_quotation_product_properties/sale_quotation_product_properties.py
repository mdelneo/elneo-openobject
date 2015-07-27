from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
from openerp import models,fields,api
from operator import itemgetter
import re


class sale_order(models.Model):
    _inherit = 'sale.order'

    display_properties = fields.Boolean("Display properties")

sale_order()

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    def get_properties_by_category(self):
        result = []
        for prop in self.sale_quotation_properties:
            property_tab = None
            for t in result:
                if t[0] == prop.category:
                    property_tab = t[1]
            if not property_tab:
                t = (prop.category,[])
                result.append(t)
                property_tab = t[1]
            property_tab.append(prop)
        return result
            
            
    
sale_order_line()