try:
    import simplejson
except:
    raise ImportError('The simplejson module is not found')

try:    
    import urllib
except:
    raise ImportError('The urllib module is not found')

from openerp import models, fields, api, _


class maintenance_installation(models.Model):
    _inherit='maintenance.installation'
    
    @api.one
    def _get_travel_cost(self):
        if not self.address_id or not self.address_id.zip:
            return
       
        travel_cost_ids = self.env['travel.cost'].search([('zip','<=',self.address_id.zip)], limit=1, order='zip desc')
        if not travel_cost_ids:
            return
        self.travel_cost_id=travel_cost_ids[0]
        
    travel_cost_id=fields.Many2one('travel.cost','Travel Cost',default=_get_travel_cost)
    travel_time=fields.Float('Travel Time')
    
    
    #when address change, update travel cost
    @api.one
    @api.onchange('address_id')
    def on_change_address_id(self):
        #find good travel cost
        self._get_travel_cost()
    
    # Compute Travel Time from action button
    @api.one
    def action_compute_time(self):
        self._compute_time()

        
    # Compute travel times for all the installations
    @api.one
    def compute_time(self):
        # Select active installations, with shop defined, address defined and travel_time not already set 
        installations = self.search([('active','=',True),('warehouse_id','!=',False),('address_id','!=',False),'|',('travel_time','=',False),('travel_time','=',0)])
        
        installations._compute_time(silent=True)

    # Private Method to
    @api.one
    def _compute_time(self,silent=False):
        
        duration=None
        response=None
        gmap_obj=GMaps()
       
        if(not self.warehouse_id):
            if(not silent):
                raise Warning(_("No Shop defined for this installation, can't calculate!"))
            
        if (not self.address_id):
            if (not silent):
                raise Warning(_("No Address defined for this installation, can't calculate!"))
        
        # We are looking first in travel_time table before Google Call
        if (self.travel_cost_id and self.warehouse_id.lot_stock_id.address_id):
            time_id = self.env['travel.time'].search([('travel_cost_id','=',self.travel_cost_id.id),('address_id','=',self.shop_id.warehouse_id.lot_stock_id.address_id.id)])
            found=False
            if time_id:
                for time_travel in time_id:
                    duration = time_travel.time
                    found = True

            if (not found):
                # Google Call   
                travel = self._get_clean_travel()
                response = gmap_obj.get_travel(travel['origin'],travel['destination'])
                
                for elements in response.rows:
                    for element in elements:
                        if(element.status and element.status=="OK"):
                            duration =float(element.duration)
                            
        if (duration):
            self.travel_time=float(duration)
                        
        return True
   
    
    # Limit errors due to void addresses parts (city, zip,...)
    @api.one
    def _get_clean_travel(self):
        
        res={'origin':"",
             'destination':""
             }
        if (self):
            if(self.warehouse_id and self.warehouse_id.lot_stock_id and self.warehouse_id.lot_stock_id.address_id):
                address=None
                address = self.warehouse_id.lot_stock_id.address_id
                if (address.street):
                    res['origin']+=address.street
                if (address.zip):
                    res['origin']+=" " + address.zip
                if(address.city):
                    res['origin']+=" " + address.city
                if(address.country_id):
                    res['origin']+= " " + address.country_id.name
            if(self.address_id):
                address=None
                address=self.address_id
                if(address.street):
                    res['destination']+=address.street
                if (address.zip):
                    res['destination']+=" " + address.zip
                if(address.city):
                    res['destination']+=" " + address.city
                if(address.country_id):
                    res['destination']+= " " + address.country_id.name
        return res
    
maintenance_installation()



class maintenance_intervention(models.Model):
    
    _inherit='maintenance.intervention'
    
    # Override invoice generation to input travel cost line if exists
    @api.multi
    def generate_invoice(self):
        
        invoices = super(maintenance_intervention, self).generate_invoice()
        
        # If the invoice has not been generated, skip
        if invoices:
            for intervention in self:
                installation = intervention.installation_id
                
                # If no travel cost defined, skip
                if (installation and installation.travel_cost_id and installation.travel_cost_id.product_id):
                    
                    invoice = invoices[0]
                    
                    travel_product = installation.travel_cost_id.product_id
                    account_id = travel_product.product_tmpl_id.property_account_income.id
                    if not account_id:
                        account_id = travel_product.categ_id.property_account_income_categ.id
                    taxes=travel_product.taxes_id
                    partner = invoice.address_invoice_id.partner_id and invoice.address_invoice_id.partner_id or False
                    
                    account_id = self.env['account.fiscal.position'].map_account(partner.property_account_position, account_id)
                    taxes = travel_product.taxes_id
                    taxes_ids = [x.id for x in taxes]
                    taxes_ids = self.env['account.fiscal.position'].map_tax(partner.property_account_position, taxes)
                    if (invoice.state == 'draft'):
                        values={
                                'name': travel_product.name,
                                'invoice_id': invoice.id,
                                'uos_id': travel_product.uos_id.id,
                                'product_id': travel_product.id,
                                'account_id': account_id,
                                'price_unit': travel_product.list_price,
                                'quantity': 1,
                                'invoice_line_tax_id': [(6, 0,taxes_ids)],
                                'intervention_id':intervention.id
                                }
                        self.env['account.invoice.line'].create(values)
        
        return invoices

# The Response structure returned by the query 
class GMaps_Response:
    
    status="KO"
    
    rows=[]
    
    destination_addresses=[]
    origin_addresses=[]

# A representation of the Destination Address    
class GMaps_Destination_Address:
    
    name=""
    
    def __init__(self,name):
        self.name=name
    
# A representation of the Origin Address
class GMaps_Origin_Address:
    
    name=""
    
    def __init__(self,name):
        self.name=name

# A representation of the Travel Duration
# Stores the text and duration (in seconds) as returned by google
# Override the __str__ method to format in "XX h XX m XX s"
# Override the __float__ method to return the float in hours
class GMaps_Duration:
    text=""
    value=0
    
    def __init__(self,text="",value=0):
        self.text=text
        self.value=value
        
    def __str__(self):
        tmp=""
        if(self.value / 3600 > 0):
            h = self.value / 3600
            m = self.value - (h * 3600)
            s = self.value - (h * 3600) - (m * 60)
            tmp = str(h) + " h " + str(m) + " m " + s + " s" 
        else :
            m = self.value / 60
            s = self.value - (m * 60) 
            tmp = str(m) + " m " + str(s) + " s" 
            
        return tmp

    def __float__(self):
        tmp=float(float(self.value) / float(3600.0))
        if(tmp > 0.0):
            return float(tmp)
        else:
            return float(0.0) 
            
        
# A representation of the Travel Distance
# Stores the text and distance (in meters) as returned by google
# Override the __str__ method to format in "XX km XX m"
class GMaps_Distance:
    text=""
    value=0
    
    def __init__(self,text="",value=0):
        self.text=text
        self.value=value
        
    def __str__(self):
        tmp=""
        if (self.value / 1000 > 0 ):
            kms = self.value / 1000
            m = self.value - (kms * 1000)
            tmp=str(kms) + " km " + str(m) + " m"
        else :
            tmp=tmp + " m"
            
        return tmp
        
        
class GMaps_Element:
    
    duration = GMaps_Duration()
    
    distance = GMaps_Distance()
    
    status = "NOT_FOUND"
    
    def __init__(self,duration="0",distance="0",status="NOT_FOUND"):
        if(isinstance(duration,GMaps_Duration)):
            self.duration=duration
        if(isinstance(distance,GMaps_Distance)):
            self.distance = distance
        if(status):
            self.status=status

class GMaps_Row:
    
    elements=[]
    
class GMaps:
    
    url="http://maps.googleapis.com/maps/api/distancematrix/json?"
    
    response=GMaps_Response()
    
    def get_travel(self,origin,destination):
        
        
        url = "http://maps.googleapis.com/maps/api/distancematrix/json?origins={0}&destinations={1}&mode=driving&language=en-EN&sensor=false".format(str(origin),str(destination))
        try:
            self.parse_order_response(simplejson.load(urllib.urlopen(url)))
        except Exception, e:
            raise  Warning(_("Error during Google Query") + " " + e.message)
        
        return self.response
        
    # Parse the Google Maps json response
    def parse_order_response(self,response):
        
        self.response=GMaps_Response()
        
        if (response and response.has_key('status')):
            self.response.status=response['status']
            
        if self.response.status=="KO":
            return
        
        for address in response['destination_addresses']:
            self.response.destination_addresses.append(GMaps_Destination_Address(address))
            
        
        for address in response['origin_addresses']:
            self.response.origin_addresses.append(GMaps_Origin_Address(address))
            
       
        for row in response['rows']:
            tmp_element=[]
            for element in row['elements']:
                if(element.has_key('status') and element['status']=='NOT_FOUND'):
                    el=GMaps_Element(status='NOT_FOUND')
                elif(element.has_key('status') and element['status']=='ZERO_RESULTS'):
                    el=GMaps_Element(status='ZERO_RESULTS')
                elif(element.has_key('status') and element['status']=='ZERO_RESULTS'):
                    el=GMaps_Element(status='OVER_QUERY_LIMIT')
                elif(element.has_key('duration') and element['duration'].has_key('text') and element['duration'].has_key('value')):
                    dur=GMaps_Duration(element['duration']['text'],element['duration']['value'])
                    dist=GMaps_Distance(element['distance']['text'],element['distance']['value'])
                    el = GMaps_Element(dur,dist,element['status'])
               
                else:
                    if (element.has_key('status')):
                        el=GMaps_Element(status=element['status'])
                    else:
                        el=GMaps_Element(status='ERROR')
                tmp_element.append(el)
                
            self.response.rows.append(tmp_element)
            
        
        return True
