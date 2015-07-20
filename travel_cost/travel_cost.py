try:
    import simplejson
except:
    raise ImportError('The simplejson module is not found')

try:    
    import urllib
except:
    raise ImportError('The urllib module is not found')


from openerp import models, fields,api, _

class travel_cost(models.Model):
    _name='travel.cost'

    name=fields.Char('Name',size=30,required=True,default='Cost',index=True,help="The name you give to this Cost")
    zip=fields.Char('Zip Code',size=30,required=True,help="The zip code for this cost")
    product_id=fields.Many2one('product.product','Product',help="The travel product for this cost")

    _sql_constraints=[('zip_unique','unique(zip)','Zip Code must be unique!')]


class travel_time(models.Model):
    _name='travel.time'
    
    _rec_name='travel_cost_id'
    
    travel_cost_id=fields.Many2one('travel.cost','Travel Cost',help="The Cost linked to this travel time")
    address_id=fields.Many2one('res.partner','Address',help="The origin address")
    time=fields.Float('Travel Time',help="The time from the origin to the destination")
    
    
    # Compute the travel time with google
    @api.multi
    def compute_time(self):
        res={'nodestroy':True}
        
        travel_time=None
        for travel in self:
            if (not travel.travel_cost_id.zip):
                raise Warning(_("The travel destination is not set!"))
            if (not travel.address_id.zip):
                raise Warning(_("The travel origin is not set!"))
                
            gmaps_obj=GMaps()
            response = gmaps_obj.get_travel(travel.address_id.zip + travel.address_id.country_id.name, travel.travel_cost_id.zip + travel.address_id.country_id.name)
            
            for elements in response.rows:
                for element in elements:
                    if element.status=="NOT_FOUND":
                        raise Warning(_("The travel you specified is incorrect. Google has not found it!"))
                    elif element.status=="OK":
                        travel_time=float(element.duration)
                    
            if travel_time:
                self.time = travel_time
                   
        return res


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
