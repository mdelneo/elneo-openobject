from openerp import models
from openerp.tools import html_escape as escape
from openerp.addons.base.ir.ir_qweb import HTMLSafe

class TextConverter(models.AbstractModel):
    _inherit = 'ir.qweb.field.text'

    def value_to_html(self, cr, uid, value, field, options=None, context=None):
        """
        Escapes the value and converts newlines to br. This is bullshit.
        """
        if not value: return ''

        return nl2br(value, options=options)
    


def nl2br(string, options=None):
    """ Converts newlines to HTML linebreaks in ``string``. Automatically
    escapes content unless options['html-escape'] is set to False, and returns
    the result wrapped in an HTMLSafe object.
    
    :param str string:
    :param dict options:
    :rtype: HTMLSafe
    """
    if options is None: options = {}
    
    if options.get('html-escape', True):
        string = escape(string.replace('\n', '<br>\n'))
    else:
        string = string.replace('\n', '')
        
    return HTMLSafe(string) 