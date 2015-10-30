/*---------------------------------------------------------
 * OpenERP web library
 *---------------------------------------------------------*/
openerp.elneo_layout = function (instance) {
    

    instance.web.Sidebar.include({
 
    on_attachments_loaded: function(attachments) {
        var self = this;
        var items = [];
        var prefix = this.session.url('/web/binary/saveas', {model: 'ir.attachment', field: 'datas', filename_field: 'datas_fname'});
        _.each(attachments,function(a) {
            a.label = a.name;
            if(a.type === "binary") {
                a.url = prefix  + '&id=' + a.id + '&t=' + (new Date().getTime());
            }
        });

        self.items['files'] = attachments;
        self.redraw();
        this.$('.oe_sidebar_add_attachment .oe_form_binary_file').change(this.on_attachment_changed);
        this.$el.find('.oe_sidebar_delete_item').click(this.on_attachment_delete);
    }
    
});
    
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
