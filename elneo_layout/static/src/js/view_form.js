(function() {
var instance = openerp;

/*Redefine Field Many2One to open in popup on readonly mode*/

instance.web.form.FieldMany2One = instance.web.form.AbstractField.extend(instance.web.form.CompletionFieldMixin, instance.web.form.ReinitializeFieldMixin, {
    template: "FieldMany2One",
    events: {
        'keydown input': function (e) {
            switch (e.which) {
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
                e.stopPropagation();
            }
        },
    },
    init: function(field_manager, node) {
        this._super(field_manager, node);
        instance.web.form.CompletionFieldMixin.init.call(this);
        this.set({'value': false});
        this.display_value = {};
        this.display_value_backup = {};
        this.last_search = [];
        this.floating = false;
        this.current_display = null;
        this.is_started = false;
        this.ignore_focusout = false;
    },
    reinit_value: function(val) {
        this.internal_set_value(val);
        this.floating = false;
        if (this.is_started && !this.no_rerender)
            this.render_value();
    },
    initialize_field: function() {
        this.is_started = true;
        instance.web.bus.on('click', this, function() {
            if (!this.get("effective_readonly") && this.$input && this.$input.autocomplete('widget').is(':visible')) {
                this.$input.autocomplete("close");
            }
        });
        instance.web.form.ReinitializeFieldMixin.initialize_field.call(this);
    },
    initialize_content: function() {
        if (!this.get("effective_readonly"))
            this.render_editable();
    },
    destroy_content: function () {
        if (this.$drop_down) {
            this.$drop_down.off('click');
            delete this.$drop_down;
        }
        if (this.$input) {
            this.$input.closest(".modal .modal-content").off('scroll');
            this.$input.off('keyup blur autocompleteclose autocompleteopen ' +
                            'focus focusout change keydown');
            delete this.$input;
        }
        if (this.$follow_button) {
            this.$follow_button.off('blur focus click');
            delete this.$follow_button;
        }
    },
    destroy: function () {
        this.destroy_content();
        return this._super();
    },
    init_error_displayer: function() {
        // nothing
    },
    hide_error_displayer: function() {
        // doesn't work
    },
    show_error_displayer: function() {
        new instance.web.form.M2ODialog(this).open();
    },
    render_editable: function() {
        var self = this;
        this.$input = this.$el.find("input");

        this.init_error_displayer();

        self.$input.on('focus', function() {
            self.hide_error_displayer();
        });

        this.$drop_down = this.$el.find(".oe_m2o_drop_down_button");
        this.$follow_button = $(".oe_m2o_cm_button", this.$el);

        this.$follow_button.click(function(ev) {
            ev.preventDefault();
            if (!self.get('value')) {
                self.focus();
                return;
            }
            var pop = new instance.web.form.FormOpenPopup(self);
            var context = self.build_context().eval();
            var model_obj = new instance.web.Model(self.field.relation);
            model_obj.call('get_formview_id', [self.get("value"), context]).then(function(view_id){
                pop.show_element(
                    self.field.relation,
                    self.get("value"),
                    self.build_context(),
                    {
                        title: _t("Open: ") + self.string,
                        view_id: view_id
                    }
                );
                pop.on('write_completed', self, function(){
                    self.display_value = {};
                    self.display_value_backup = {};
                    self.render_value();
                    self.focus();
                    self.trigger('changed_value');
                });
            });
        });

        // some behavior for input
        var input_changed = function() {
            if (self.current_display !== self.$input.val()) {
                self.current_display = self.$input.val();
                if (self.$input.val() === "") {
                    self.internal_set_value(false);
                    self.floating = false;
                } else {
                    self.floating = true;
                }
            }
        };
        this.$input.keydown(input_changed);
        this.$input.change(input_changed);
        this.$drop_down.click(function() {
            self.$input.focus();
            if (self.$input.autocomplete("widget").is(":visible")) {
                self.$input.autocomplete("close");                
            } else {
                if (self.get("value") && ! self.floating) {
                    self.$input.autocomplete("search", "");
                } else {
                    self.$input.autocomplete("search");
                }
            }
        });

        // Autocomplete close on dialog content scroll
        var close_autocomplete = _.debounce(function() {
            if (self.$input.autocomplete("widget").is(":visible")) {
                self.$input.autocomplete("close");
            }
        }, 50);
        this.$input.closest(".modal .modal-content").on('scroll', this, close_autocomplete);

        self.ed_def = $.Deferred();
        self.uned_def = $.Deferred();
        var ed_delay = 200;
        var ed_duration = 15000;
        var anyoneLoosesFocus = function (e) {
            if (self.ignore_focusout) { return; }
            var used = false;
            if (self.floating) {
                if (self.last_search.length > 0) {
                    if (self.last_search[0][0] != self.get("value")) {
                        self.display_value = {};
                        self.display_value_backup = {};
                        self.display_value["" + self.last_search[0][0]] = self.last_search[0][1];
                        self.reinit_value(self.last_search[0][0]);
                        self.last_search = []
                    } else {
                        used = true;
                        self.render_value();
                    }
                } else {
                    used = true;
                }
                self.floating = false;
            }
            if (used && self.get("value") === false && ! self.no_ed && ! (self.options && (self.options.no_create || self.options.no_quick_create))) {
                self.ed_def.reject();
                self.uned_def.reject();
                self.ed_def = $.Deferred();
                self.ed_def.done(function() {
                    self.show_error_displayer();
                    ignore_blur = false;
                    self.trigger('focused');
                });
                ignore_blur = true;
                setTimeout(function() {
                    self.ed_def.resolve();
                    self.uned_def.reject();
                    self.uned_def = $.Deferred();
                    self.uned_def.done(function() {
                        self.hide_error_displayer();
                    });
                    setTimeout(function() {self.uned_def.resolve();}, ed_duration);
                }, ed_delay);
            } else {
                self.no_ed = false;
                self.ed_def.reject();
            }
        };
        var ignore_blur = false;
        this.$input.on({
            focusout: anyoneLoosesFocus,
            focus: function () { self.trigger('focused'); },
            autocompleteopen: function () { ignore_blur = true; },
            autocompleteclose: function () { setTimeout(function() {ignore_blur = false;},0); },
            blur: function () {
                // autocomplete open
                if (ignore_blur) { $(this).focus(); return; }
                if (_(self.getChildren()).any(function (child) {
                    return child instanceof instance.web.form.AbstractFormPopup;
                })) { return; }
                self.trigger('blurred');
            }
        });

        var isSelecting = false;
        // autocomplete
        this.$input.autocomplete({
            source: function(req, resp) {
                self.get_search_result(req.term).done(function(result) {
                    resp(result);
                });
            },
            select: function(event, ui) {
                isSelecting = true;
                var item = ui.item;
                if (item.id) {
                    self.display_value = {};
                    self.display_value_backup = {};
                    self.display_value["" + item.id] = item.name;
                    self.reinit_value(item.id);
                } else if (item.action) {
                    item.action();
                    // Cancel widget blurring, to avoid form blur event
                    self.trigger('focused');
                    return false;
                }
            },
            focus: function(e, ui) {
                e.preventDefault();
            },
            html: true,
            // disabled to solve a bug, but may cause others
            //close: anyoneLoosesFocus,
            minLength: 0,
            delay: 200,
        });
        var appendTo = this.$el.parents('.oe_view_manager_body:visible, .modal-dialog:visible').last();
        if (appendTo.length === 0){
            appendTo = '.oe_application > *:visible:last';
        }
        this.$input.autocomplete({
            appendTo: appendTo
        });
        // set position for list of suggestions box
        this.$input.autocomplete( "option", "position", { my : "left top", at: "left bottom" } );
        this.$input.autocomplete("widget").openerpClass();
        // used to correct a bug when selecting an element by pushing 'enter' in an editable list
        this.$input.keyup(function(e) {
            if (e.which === 13) { // ENTER
                if (isSelecting)
                    e.stopPropagation();
            }
            isSelecting = false;
        });
        this.setupFocus(this.$follow_button);
    },
    render_value: function(no_recurse) {
        var self = this;
        if (! this.get("value")) {
            this.display_string("");
            return;
        }
        var display = this.display_value["" + this.get("value")];
        if (display) {
            this.display_string(display);
            return;
        }
        if (! no_recurse) {
            var dataset = new instance.web.DataSetStatic(this, this.field.relation, self.build_context());
            var def = this.alive(dataset.name_get([self.get("value")])).done(function(data) {
                if (!data[0]) {
                    self.do_warn(_t("Render"), _t("No value found for the field "+self.field.string+" for value "+self.get("value")));
                    return;
                }
                self.display_value["" + self.get("value")] = data[0][1];
                self.render_value(true);
            }).fail( function (data, event) {
                // avoid displaying crash errors as many2One should be name_get compliant
                event.preventDefault();
                self.display_value["" + self.get("value")] = self.display_value_backup["" + self.get("value")];
                self.render_value(true);
            });
            if (this.view && this.view.render_value_defs){
                this.view.render_value_defs.push(def);
            }
        }
    },
    display_string: function(str) {
        var self = this;
        if (!this.get("effective_readonly")) {
            this.$input.val(str.split("\n")[0]);
            this.current_display = this.$input.val();
            if (this.is_false()) {
                this.$('.oe_m2o_cm_button').css({'display':'none'});
            } else {
                this.$('.oe_m2o_cm_button').css({'display':'inline'});
            }
        } else {
            var lines = _.escape(str).split("\n");
            var link = "";
            var follow = "";
            link = lines[0];
            follow = _.rest(lines).join("<br />");
            if (follow)
                link += "<br />";
            var $link = this.$el.find('.oe_form_uri')
                 .unbind('click')
                 .html(link);
            if (! this.options.no_open)
                $link.click(function () {
                	if ($("div.modal-content").find($(this)).length > 0)
	            		{
	                		var pop = new instance.web.form.FormOpenPopup(self);
	                        var context = self.build_context().eval();
	                        var model_obj = new instance.web.Model(self.field.relation);
	                        model_obj.call('get_formview_id', [self.get("value"), context]).then(function(view_id){
	                            pop.show_element(
	                                self.field.relation,
	                                self.get("value"),
	                                self.build_context(),
	                                {
	                                    title: _t("Open: ") + self.string,
	                                    view_id: view_id, 
	                                    readonly: true
	                                }
	                            );
	                            pop.on('write_completed', self, function(){
	                                self.display_value = {};
	                                self.display_value_backup = {};
	                                self.render_value();
	                                self.focus();
	                                self.trigger('changed_value');
	                            });
	                        });
	            		}
                	else
                		{
	                		var context = self.build_context().eval();
	                        var model_obj = new instance.web.Model(self.field.relation);
	                        model_obj.call('get_formview_action', [self.get("value"), context]).then(function(action){
	                            self.do_action(action);
	                        });
	                        return false;
                		}
                 });
            
            $(".oe_form_m2o_follow", this.$el).html(follow);
        }
    },
    set_value: function(value_) {
        var self = this;
        if (value_ instanceof Array) {
            this.display_value = {};
            this.display_value_backup = {};
            if (! this.options.always_reload) {
                this.display_value["" + value_[0]] = value_[1];
            }
            else {
                this.display_value_backup["" + value_[0]] = value_[1];
            }
            value_ = value_[0];
        }
        value_ = value_ || false;
        this.reinit_value(value_);
    },
    get_displayed: function() {
        return this.display_value["" + this.get("value")];
    },
    add_id: function(id) {
        this.display_value = {};
        this.display_value_backup = {};
        this.reinit_value(id);
    },
    is_false: function() {
        return ! this.get("value");
    },
    focus: function () {
        var input = !this.get('effective_readonly') && this.$input && this.$input[0];
        return input ? input.focus() : false;
    },
    _quick_create: function() {
        this.no_ed = true;
        this.ed_def.reject();
        return instance.web.form.CompletionFieldMixin._quick_create.apply(this, arguments);
    },
    _search_create_popup: function() {
        this.no_ed = true;
        this.ed_def.reject();
        this.ignore_focusout = true;
        this.reinit_value(false);
        var res = instance.web.form.CompletionFieldMixin._search_create_popup.apply(this, arguments);
        this.ignore_focusout = false;
        this.no_ed = false;
        return res;
    },
    set_dimensions: function (height, width) {
        this._super(height, width);
        if (!this.get("effective_readonly") && this.$input)
            this.$input.css('height', height);
    }
});

instance.web.form.Many2OneButton = instance.web.form.AbstractField.extend({
    template: 'Many2OneButton',
    init: function(field_manager, node) {
        this._super.apply(this, arguments);
    },
    start: function() {
        this._super.apply(this, arguments);
        this.set_button();
    },
    set_button: function() {
        var self = this;
        if (this.$button) {
            this.$button.remove();
        }
        this.string = '';
        this.node.attrs.icon = this.get('value') ? '/web/static/src/img/icons/gtk-yes.png' : '/web/static/src/img/icons/gtk-no.png';
        this.$button = $(QWeb.render('WidgetButton', {'widget': this}));
        this.$button.addClass('oe_link').css({'padding':'4px'});
        this.$el.append(this.$button);
        this.$button.on('click', self.on_click);
    },
    on_click: function(ev) {
        var self = this;
        this.popup =  new instance.web.form.FormOpenPopup(this);
        this.popup.show_element(
            this.field.relation,
            this.get('value'),
            this.build_context(),
            {title: this.string}
        );
        this.popup.on('create_completed', self, function(r) {
            self.set_value(r);
        });
    },
    set_value: function(value_) {
        var self = this;
        if (value_ instanceof Array) {
            value_ = value_[0];
        }
        value_ = value_ || false;
        this.set('value', value_);
        this.set_button();
     },
});
})();