openerp.edi_simple = function (instance) {
   

    var edi_simple = instance.edi_simple;

    /*openerp_mail_followers(session, edi_simple);          // import mail_followers.js
    openerp_FieldMany2ManyTagsEmail(session);       // import manyy2many_tags_email.js
    openerp_announcement(session);*/
    
    /**
     * ------------------------------------------------------------
     * ChatterUtils
     * ------------------------------------------------------------
     * 
     * This class holds a few tools method for Chatter.
     * Some regular expressions not used anymore, kept because I want to
     * - (^|\s)@((\w|@|\.)*): @login@log.log
     * - (^|\s)\[(\w+).(\w+),(\d)\|*((\w|[@ .,])*)\]: [ir.attachment,3|My Label],
     *   for internal links
     */

    edi_simple.ChatterUtils = {

        /** parse text to find email: Tagada <address@mail.fr> -> [Tagada, address@mail.fr] or False */
        parse_email: function (text) {
            var result = text.match(/(.*)<(.*@.*)>/);
            if (result) {
                return [_.str.trim(result[1]), _.str.trim(result[2])];
            }
            result = text.match(/(.*@.*)/);
            if (result) {
                return [_.str.trim(result[1]), _.str.trim(result[1])];
            }
            return [text, false];
        },

        /* Get an image in /web/binary/image?... */
        get_image: function (session, model, field, id, resize) {
            var r = resize ? encodeURIComponent(resize) : '';
            id = id || '';
            return session.url('/web/binary/image', {model: model, field: field, id: id, resize: r});
        },

        /* Get the url of an attachment {'id': id} */
        get_attachment_url: function (session, message_id, attachment_id) {
            return session.url('/mail/download_attachment', {
                'model': 'mail.message',
                'id': message_id,
                'method': 'download_attachment',
                'attachment_id': attachment_id
            });
        },

        /**
         * Replaces some expressions
         * - :name - shortcut to an image
         */
        do_replace_expressions: function (string) {
            var icon_list = ['al', 'pinky']
            /* special shortcut: :name, try to find an icon if in list */
            var regex_login = new RegExp(/(^|\s):((\w)*)/g);
            var regex_res = regex_login.exec(string);
            while (regex_res != null) {
                var icon_name = regex_res[2];
                if (_.include(icon_list, icon_name))
                    string = string.replace(regex_res[0], regex_res[1] + '<img src="/mail/static/src/img/_' + icon_name + '.png" width="22px" height="22px" alt="' + icon_name + '"/>');
                regex_res = regex_login.exec(string);
            }
            return string;
        },

        /**
         * Replaces textarea text into html text (add <p>, <a>)
         * TDE note : should be done server-side, in Python -> use mail.compose.message ?
         */
        get_text2html: function (text) {
            return text
                .replace(/((?:https?|ftp):\/\/[\S]+)/g,'<a href="$1">$1</a> ')
                .replace(/[\n\r]/g,'<br/>')                
        },

        /* Returns the complete domain with "&" 
         * TDE note: please add some comments to explain how/why
         */
        expand_domain: function (domain) {
            var new_domain = [];
            var nb_and = -1;
            // TDE note: smarted code maybe ?
            for ( var k = domain.length-1; k >= 0 ; k-- ) {
                if ( typeof domain[k] != 'array' && typeof domain[k] != 'object' ) {
                    nb_and -= 2;
                    continue;
                }
                nb_and += 1;
            }

            for (var k = 0; k < nb_and ; k++) {
                domain.unshift('&');
            }

            return domain;
        },

        // inserts zero width space between each letter of a string so that
        // the word will correctly wrap in html boxes smaller than the text
        breakword: function(str){
            var out = '';
            if (!str) {
                return str;
            }
            for(var i = 0, len = str.length; i < len; i++){
                out += _.str.escapeHTML(str[i]) + '&#8203;';
            }
            return out;
        },
    };
    
    /**
     * ------------------------------------------------------------
     * MessageCommon
     * ------------------------------------------------------------
     * 
     * Common base for expandables, chatter messages and composer. It manages
     * the various variables common to those models.
     */

    edi_simple.MessageCommon = instance.web.Widget.extend({

    /**
     * ------------------------------------------------------------
     * FIXME: this comment was moved as is from the ThreadMessage Init as
     * part of a refactoring. Check that it is still correct
     * ------------------------------------------------------------
     * This widget handles the display of a messages in a thread. 
     * Displays a record and performs some formatting on the record :
     * - record.date: formatting according to the user timezone
     * - record.timerelative: relative time givein by timeago lib
     * - record.avatar: image url
     * - record.attachment_ids[].url: url of each attachmentThe
     * thread view :
     * - root thread
     * - - sub message (parent_id = root message)
     * - - - sub thread
     * - - - - sub sub message (parent id = sub thread)
     * - - sub message (parent_id = root message)
     * - - - sub thread
     */
        
        init: function (parent, datasets, options) {
            this._super(parent, options);

            // record options
            this.options = datasets.options || options || {};
            // record domain and context
            this.domain = datasets.domain || options.domain || [];
            this.context = _.extend({
                default_model: false,
                default_res_id: 0,
                default_parent_id: false }, options.context || {});

            // data of this message
            this.id = datasets.id ||  false,
            this.last_id = this.id,
            this.model = datasets.model || this.context.default_model || false,
            this.res_id = datasets.res_id || this.context.default_res_id ||  false,
            this.parent_id = datasets.parent_id ||  false,
            this.type = datasets.type ||  false,
            this.subtype = datasets.subtype ||  false,
            this.is_author = datasets.is_author ||  false,
            this.author_avatar = datasets.author_avatar || false,
            this.is_private = datasets.is_private ||  false,
            this.subject = datasets.subject ||  false,
            this.name = datasets.name ||  false,
            this.record_name = datasets.record_name ||  false,
            this.body = datasets.body || '',
            this.body_short = datasets.body_short || '',
            this.vote_nb = datasets.vote_nb || 0,
            this.has_voted = datasets.has_voted ||  false,
            this.is_favorite = datasets.is_favorite ||  false,
            this.thread_level = datasets.thread_level ||  0,
            this.to_read = datasets.to_read || false,
            this.author_id = datasets.author_id || false,
            this.attachment_ids = datasets.attachment_ids ||  [],
            this.partner_ids = datasets.partner_ids || [];
            this.date = datasets.date;
            this.user_pid = datasets.user_pid || false;
            this.format_data();

            // update record_name: Partner profile
            if (this.model == 'res.partner') {
                this.record_name = 'Partner Profile of ' + this.record_name;
            }
            else if (this.model == 'hr.employee') {
                this.record_name = 'News from ' + this.record_name;
            }
            // record options and data
            this.show_record_name = this.options.show_record_name && this.record_name && !this.thread_level;
            this.options.show_read = false;
            this.options.show_unread = false;
            if (this.options.show_read_unread_button) {
                if (this.options.read_action == 'read') this.options.show_read = true;
                else if (this.options.read_action == 'unread') this.options.show_unread = true;
                else {
                    this.options.show_read = this.to_read;
                    this.options.show_unread = !this.to_read;
                }
                this.options.rerender = true;
                this.options.toggle_read = true;
            }
            this.parent_thread = typeof parent.on_message_detroy == 'function' ? parent : this.options.root_thread;
            this.thread = false;
        },

        /* Convert date, timerelative and avatar in displayable data. */
        format_data: function () {

            //formating and add some fields for render
            this.date = this.date ? session.web.str_to_datetime(this.date) : false;
            this.display_date = this.date.toString(Date.CultureInfo.formatPatterns.fullDateTime);
            if (this.date && new Date().getTime()-this.date.getTime() < 7*24*60*60*1000) {
                this.timerelative = $.timeago(this.date);
            }
            if (this.author_avatar) {
                this.avatar = "data:image/png;base64," + this.author_avatar;
            } else if (this.type == 'email' && (!this.author_id || !this.author_id[0])) {
                this.avatar = ('/mail/static/src/img/email_icon.png');
            } else if (this.author_id && this.template != 'mail.compose_message') {
                this.avatar = edi_simple.ChatterUtils.get_image(this.session, 'res.partner', 'image_small', this.author_id[0]);
            } else {
                this.avatar = edi_simple.ChatterUtils.get_image(this.session, 'res.users', 'image_small', this.session.uid);
            }
            if (this.author_id && this.author_id[1]) {
                var parsed_email = edi_simple.ChatterUtils.parse_email(this.author_id[1]);
                this.author_id.push(parsed_email[0], parsed_email[1]);
            }
            if (this.partner_ids && this.partner_ids.length > 3) {
                this.extra_partners_nbr = this.partner_ids.length - 3;
                this.extra_partners_str = ''
                var extra_partners = this.partner_ids.slice(3);
                for (var key in extra_partners) {
                    this.extra_partners_str += extra_partners[key][1];
                }
            }
        },


        /* upload the file on the server, add in the attachments list and reload display
         */
        display_attachments: function () {
            for (var l in this.attachment_ids) {
                var attach = this.attachment_ids[l];
                if (!attach.formating) {
                    attach.url = edi_simple.ChatterUtils.get_attachment_url(this.session, this.id, attach.id);
                    attach.name = edi_simple.ChatterUtils.breakword(attach.name || attach.filename);
                    attach.formating = true;
                }
            }
            this.$(".oe_msg_attachment_list").html( instance.web.qweb.render('mail.thread.message.attachments', {'widget': this}) );
        },

        /* return the link to resized image
         */
        attachments_resize_image: function (id, resize) {
            return edi_simple.ChatterUtils.get_image(this.session, 'ir.attachment', 'datas', id, resize);
        },

        /* get all child message id linked.
         * @return array of id
        */
        get_child_ids: function () {
            return _.map(this.get_childs(), function (val) { return val.id; });
        },

        /* get all child message linked.
         * @return array of message object
        */
        get_childs: function (nb_thread_level) {
            var res=[];
            if (arguments[1] && this.id) res.push(this);
            if ((isNaN(nb_thread_level) || nb_thread_level>0) && this.thread) {
                _(this.thread.messages).each(function (val, key) {
                    res = res.concat( val.get_childs((isNaN(nb_thread_level) ? undefined : nb_thread_level-1), true) );
                });
            }
            return res;
        },

        /**
         * search a message in all thread and child thread.
         * This method return an object message.
         * @param {object}{int} option.id
         * @param {object}{string} option.model
         * @param {object}{boolean} option._go_thread_wall
         *      private for check the top thread
         * @return thread object
         */
        browse_message: function (options) {
            // goto the wall thread for launch browse
            if (!options._go_thread_wall) {
                options._go_thread_wall = true;
                for (var i in this.options.root_thread.messages) {
                    var res=this.options.root_thread.messages[i].browse_message(options);
                    if (res) return res;
                }
            }

            if (this.id==options.id)
                return this;

            for (var i in this.thread.messages) {
                if (this.thread.messages[i].thread) {
                    var res=this.thread.messages[i].browse_message(options);
                    if (res) return res;
                }
            }

            return false;
        },

        /**
         * call on_message_delete on his parent thread
        */
        destroy: function () {

            this._super();
            this.parent_thread.on_message_detroy(this);

        }

    });
    
    edi_simple.ThreadMessage = edi_simple.MessageCommon.extend({
        template: 'edi_simple.thread.message',
        
        start: function () {
            this._super.apply(this, arguments);
            this.bind_events();
            if(this.thread_level < this.options.display_indented_thread) {
                this.create_thread();
            }
            this.display_attachments();

            this.ds_notification = new instance.web.DataSetSearch(this, 'mail.notification');
            this.ds_message = new instance.web.DataSetSearch(this, 'edi.message');
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function () {
            var self = this;
            // header icons bindings
            this.$('.oe_read').on('click', this.on_message_read);
            this.$('.oe_unread').on('click', this.on_message_unread);
            this.$('.oe_msg_delete').on('click', this.on_message_delete);
            this.$('.oe_reply').on('click', this.on_message_reply);
            this.$('.oe_star').on('click', this.on_star);
            this.$('.oe_msg_vote').on('click', this.on_vote);
            this.$('.oe_mail_expand').on('click', this.on_expand);
            this.$('.oe_mail_reduce').on('click', this.on_expand);
            this.$('.oe_mail_action_model').on('click', this.on_record_clicked);
            this.$('.oe_mail_action_author').on('click', this.on_record_author_clicked);
        },

        on_record_clicked: function  (event) {
            event.preventDefault();
            var self = this;
            var state = {
                'model': this.model,
                'id': this.res_id,
                'title': this.record_name
            };
            session.webclient.action_manager.do_push_state(state);
            this.context.params = {
                model: this.model,
                res_id: this.res_id,
            };
            this.thread.ds_thread.call("message_redirect_action", {context: this.context}).then(function(action){
                self.do_action(action); 
            });
        },

        on_record_author_clicked: function  (event) {
            event.preventDefault();
            var partner_id = $(event.target).data('partner');
            var state = {
                'model': 'res.partner',
                'id': partner_id,
                'title': this.record_name
            };
            session.webclient.action_manager.do_push_state(state);
            var action = {
                type:'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_model: 'res.partner',
                views: [[false, 'form']],
                res_id: partner_id,
            }
            this.do_action(action);
        },

        /* Call the on_compose_message on the thread of this message. */
        on_message_reply:function (event) {
            event.stopPropagation();
            this.create_thread();
            this.thread.on_compose_message(event);
            return false;
        },

        on_expand: function (event) {
            event.stopPropagation();
            this.$('.oe_msg_body:first > .oe_msg_body_short:first').toggle();
            this.$('.oe_msg_body:first > .oe_msg_body_long:first').toggle();
            return false;
        },

        /**
         * Instantiate the thread object of this message.
         * Each message have only one thread.
         */
        create_thread: function () {
            if (this.thread) {
                return false;
            }
            /*create thread*/
            this.thread = new edi_simple.Thread(this, this, {
                    'domain': this.domain,
                    'context':{
                        'default_model': this.model,
                        'default_res_id': this.res_id,
                        'default_parent_id': this.id
                    },
                    'options': this.options
                }
            );
            /*insert thread in parent message*/
            this.thread.insertAfter(this.$el);
        },
        
        /**
         * Fade out the message and his child thread.
         * Then this object is destroyed.
         */
        animated_destroy: function (fadeTime) {
            var self=this;
            this.$el.fadeOut(fadeTime, function () {
                self.parent_thread.message_to_expandable(self);
            });
            if (this.thread) {
                this.thread.$el.fadeOut(fadeTime);
            }
        },

        /**
         * Wait a confirmation for delete the message on the DB.
         * Make an animate destroy
         */
        on_message_delete: function (event) {
            event.stopPropagation();
            if (! confirm(_t("Do you really want to delete this message?"))) { return false; }
            
            this.animated_destroy(150);
            // delete this message and his childs
            var ids = [this.id].concat( this.get_child_ids() );
            this.ds_message.unlink(ids);
            return false;
        },

        /* Check if the message must be destroy and detroy it or check for re render widget
        * @param {callback} apply function
        */
        check_for_rerender: function () {
            var self = this;

            var messages = [this].concat(this.get_childs());
            var message_ids = _.map(messages, function (msg) { return msg.id;});
            var domain = edi_simple.ChatterUtils.expand_domain( this.options.root_thread.domain )
                .concat([["id", "in", message_ids ]]);

            return this.parent_thread.ds_message.call('message_read', [undefined, domain, [], !!this.parent_thread.options.display_indented_thread, this.context, this.parent_thread.id])
                .then( function (records) {
                    // remove message not loaded
                    _.map(messages, function (msg) {
                        if(!_.find(records, function (record) { return record.id == msg.id; })) {
                            msg.animated_destroy(150);
                        } else {
                            msg.renderElement();
                            msg.start();
                        }
                        self.options.root_thread.MailWidget.do_reload_menu_emails();
                    });

                });
        },

        on_message_read: function (event) {
            event.stopPropagation();
            this.on_message_read_unread(true);
            return false;
        },

        on_message_unread: function (event) {
            event.stopPropagation();
            this.on_message_read_unread(false);
            return false;
        },

        /* Set the selected thread and all childs as read or unread, based on
         * read parameter.
         * @param {boolean} read_value
         */
        on_message_read_unread: function (read_value) {
            var self = this;
            var messages = [this].concat(this.get_childs());

            // inside the inbox, when the user mark a message as read/done, don't apply this value
            // for the stared/favorite message
            if (this.options.view_inbox && read_value) {
                var messages = _.filter(messages, function (val) { return !val.is_favorite && val.id; });
                if (!messages.length) {
                    this.check_for_rerender();
                    return false;
                }
            }
            var message_ids = _.map(messages, function (val) { return val.id; });

            this.ds_message.call('set_message_read', [message_ids, read_value, true, this.context])
                .then(function () {
                    // apply modification
                    _.each(messages, function (msg) {
                        msg.to_read = !read_value;
                        if (msg.options.toggle_read) {
                            msg.options.show_read = msg.to_read;
                            msg.options.show_unread = !msg.to_read;
                        }
                    });
                    // check if the message must be display, destroy or rerender
                    self.check_for_rerender();
                });
            return false;
        },

        /**
         * add or remove a vote for a message and display the result
        */
        on_vote: function (event) {
            event.stopPropagation();
            this.ds_message.call('vote_toggle', [[this.id]])
                .then(
                    _.bind(function (vote) {
                        this.has_voted = vote;
                        this.vote_nb += this.has_voted ? 1 : -1;
                        //this.display_vote();
                    }, this));
            return false;
        },

        
        /**
         * Display the render of this message's vote
        */
        /*
        display_vote: function () {
            var vote_element = session.web.qweb.render('mail.thread.message.vote', {'widget': this});
            this.$(".oe_msg_footer:first .oe_mail_vote_count").remove();
            this.$(".oe_msg_footer:first .oe_msg_vote").replaceWith(vote_element);
            this.$('.oe_msg_vote').on('click', this.on_vote);
        },
        */

        /**
         * add or remove a favorite (or starred) for a message and change class on the DOM
        */
        on_star: function (event) {
            event.stopPropagation();
            var self=this;
            var button = self.$('.oe_star:first');

            this.ds_message.call('set_message_starred', [[self.id], !self.is_favorite, true])
                .then(function (star) {
                    self.is_favorite=star;
                    if (self.is_favorite) {
                        button.addClass('oe_starred');
                    } else {
                        button.removeClass('oe_starred');
                    }

                    if (self.options.view_inbox && self.is_favorite) {
                        self.on_message_read_unread(true);
                    } else {
                        self.check_for_rerender();
                    }
                });
            return false;
        },

    });

    
    /**
     * ------------------------------------------------------------
     * Thread Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of a thread of messages. The
     * thread view:
     * - root thread
     * - - sub message (parent_id = root message)
     * - - - sub thread
     * - - - - sub sub message (parent id = sub thread)
     * - - sub message (parent_id = root message)
     * - - - sub thread
     */
    edi_simple.Thread = instance.web.Widget.extend({
        template: 'edi_simple.thread',

        /**
         * @param {Object} parent parent
         * @param {Array} [domain]
         * @param {Object} [context] context of the thread. It should
            contain at least default_model, default_res_id. Please refer to
            the ComposeMessage widget for more information about it.
         * @param {Object} [options]
         *      @param {Object} [message] read about mail.ThreadMessage object
         *      @param {Object} [thread]
         *          @param {int} [display_indented_thread] number thread level to indented threads.
         *              other are on flat mode
         *          @param {Array} [parents] liked with the parents thread
         *              use with browse, fetch... [O]= top parent
         */
        init: function (parent, datasets, options) {
            var self = this;
            this._super(parent, options);
            this.MailWidget = parent instanceof edi_simple.Widget ? parent : false;
            this.domain = options.domain || [];
            this.context = _.extend(options.context || {});

            this.options = options.options;
            this.options.root_thread = (options.options.root_thread != undefined ? options.options.root_thread : this);
            this.options.show_compose_message = this.options.show_compose_message && !this.thread_level;
            
            // record options and data
            this.parent_message= parent.thread!= undefined ? parent : false ;

            // data of this thread
            this.id = datasets.id || false;
            this.last_id = datasets.last_id || false;
            this.parent_id = datasets.parent_id || false;
            this.is_private = datasets.is_private || false;
            this.author_id = datasets.author_id || false;
            this.thread_level = (datasets.thread_level+1) || 0;
            datasets.partner_ids = datasets.partner_ids || [];
            if (datasets.author_id && !_.contains(_.flatten(datasets.partner_ids),datasets.author_id[0]) && datasets.author_id[0]) {
                datasets.partner_ids.push(datasets.author_id);
            }
            this.user_pid = datasets.user_pid || false;
            this.partner_ids = datasets.partner_ids;
            this.messages = [];
            this.options.flat_mode = (this.options.display_indented_thread - this.thread_level > 0);

            // object compose message
            this.compose_message = false;

            this.ds_thread = new instance.web.DataSetSearch(this, this.context.default_model || 'edi.thread');
            this.ds_message = new instance.web.DataSetSearch(this, 'edi.message');
            this.render_mutex = new $.Mutex();
        },
        
        start: function () {
            this._super.apply(this, arguments);
            this.bind_events();
        },

        /* instantiate the compose message object and insert this on the DOM.
        * The compose message is display in compact form.
        */
        /*
        instantiate_compose_message: function () {
            // add message composition form view
            if (!this.compose_message) {
                this.compose_message = new edi.ThreadComposeMessage(this, this, {
                    'context': this.options.compose_as_todo && !this.thread_level ? _.extend(this.context, { 'default_starred': true }) : this.context,
                    'options': this.options,
                });
                if (!this.thread_level || this.thread_level > this.options.display_indented_thread) {
                    this.compose_message.insertBefore(this.$el);
                } else {
                    this.compose_message.prependTo(this.$el);
                }
            }
        },*/

        /* When the expandable object is visible on screen (with scrolling)
         * then the on_expandable function is launch
        */
        on_scroll: function () {
            var expandables = 
            _.each( _.filter(this.messages, function (val) {return val.max_limit && !val.parent_id;}), function (val) {
                var pos = val.$el.position();
                if (pos.top) {
                    /* bottom of the screen */
                    var bottom = $(window).scrollTop()+$(window).height()+200;
                    if (bottom > pos.top) {
                        val.on_expandable();
                    }
                }
            });
        },

        /**
         * Bind events in the widget. Each event is slightly described
         * in the function. */
        bind_events: function () {
            var self = this;
            self.$('.oe_mail_list_recipients .oe_more').on('click', self.on_show_recipients);
            self.$('.oe_mail_compose_textarea .oe_more_hidden').on('click', self.on_hide_recipients);
        },

        /**
         *show all the partner list of this parent message
        */
        on_show_recipients: function () {
            var p=$(this).parent(); 
            p.find('.oe_more_hidden, .oe_hidden').show(); 
            p.find('.oe_more').hide(); 
            return false;
        },

        /**
         *hide a part of the partner list of this parent message
        */
        on_hide_recipients: function () {
            var p=$(this).parent(); 
            p.find('.oe_more_hidden, .oe_hidden').hide(); 
            p.find('.oe_more').show(); 
            return false;
        },

        /* get all child message/thread id linked.
         * @return array of id
        */
        get_child_ids: function () {
            return _.map(this.get_childs(), function (val) { return val.id; });
        },

        /* get all child message/thread linked.
         * @param {int} nb_thread_level, number of traversed thread level for this search
         * @return array of thread object
        */
        get_childs: function (nb_thread_level) {
            var res=[];
            if (arguments[1]) res.push(this);
            if (isNaN(nb_thread_level) || nb_thread_level>0) {
                _(this.messages).each(function (val, key) {
                    if (val.thread) {
                        res = res.concat( val.thread.get_childs((isNaN(nb_thread_level) ? undefined : nb_thread_level-1), true) );
                    }
                });
            }
            return res;
        },

        /**
         *search a thread in all thread and child thread.
         * This method return an object thread.
         * @param {object}{int} option.id
         * @param {object}{string} option.model
         * @param {object}{boolean} option._go_thread_wall
         *      private for check the top thread
         * @param {object}{boolean} option.default_return_top_thread
         *      return the top thread (wall) if no thread found
         * @return thread object
         */
        browse_thread: function (options) {
            // goto the wall thread for launch browse
            if (!options._go_thread_wall) {
                options._go_thread_wall = true;
                return this.options.root_thread.browse_thread(options);
            }

            if (this.id == options.id) {
                return this;
            }

            if (options.id) {
                for (var i in this.messages) {
                    if (this.messages[i].thread) {
                        var res = this.messages[i].thread.browse_thread({'id':options.id, '_go_thread_wall':true});
                        if (res) return res;
                    }
                }
            }

            //if option default_return_top_thread, return the top if no found thread
            if (options.default_return_top_thread) {
                return this;
            }

            return false;
        },

        /**
         *search a message in all thread and child thread.
         * This method return an object message.
         * @param {object}{int} option.id
         * @param {object}{string} option.model
         * @param {object}{boolean} option._go_thread_wall
         *      private for check the top thread
         * @return message object
         */
        browse_message: function (options) {
            if (this.options.root_thread.messages[0])
                return this.options.root_thread.messages[0].browse_message(options);
        },

        /**
         *If compose_message doesn't exist, instantiate the compose message.
        * Call the on_toggle_quick_composer method to allow the user to write his message.
        * (Is call when a user click on "Reply" button)
        */
        on_compose_message: function (event) {
            //this.instantiate_compose_message();
            this.compose_message.on_toggle_quick_composer(event);
            return false;
        },

        /**
         *display the message "there are no message" on the thread
        */
        no_message: function () {
            var no_message = $(instance.web.qweb.render('mail.wall_no_message', {}));
            if (this.options.help) {
                no_message.html(this.options.help);
            }
            if (!this.$el.find(".oe_view_nocontent").length)
            {
                no_message.appendTo(this.$el);
            }
        },

        /**
         *make a request to read the message (calling RPC to "message_read").
         * The result of this method is send to the switch message for sending ach message to
         * his parented object thread.
         * @param {Array} replace_domain: added to this.domain
         * @param {Object} replace_context: added to this.context
         * @param {Array} ids read (if the are some ids, the method don't use the domain)
         */
        message_fetch: function (replace_domain, replace_context, ids, callback) {
            return this.ds_message.call('message_read', [
                    // ids force to read
                    ids === false ? undefined : ids && ids.slice(0, this.options.fetch_limit),
                    // domain + additional
                    (replace_domain ? replace_domain : this.domain), 
                    // ids allready loaded
                    (this.id ? [this.id].concat( this.get_child_ids() ) : this.get_child_ids()), 
                    // option for sending in flat mode by server
                    this.options.flat_mode, 
                    // parent_id
                    this.context.default_parent_id || undefined,
                    this.options.fetch_limit,
                 // context + additional
                    (replace_context ? replace_context : this.context), 
                ]).done(callback ? _.bind(callback, this, arguments) : this.proxy('switch_new_message')
                ).done(this.proxy('message_fetch_set_read'));
        },

        message_fetch_set_read: function (message_list) {
            if (! this.context.mail_read_set_read) return;
            var self = this;
            this.render_mutex.exec(function() {
                msg_ids = _.pluck(message_list, 'id');
                return self.ds_message.call('set_message_read', [msg_ids, true, false, self.context])
                    .then(function (nb_read) {
                        if (nb_read) {
                            self.options.root_thread.MailWidget.do_reload_menu_emails();
                        }
                    });
             });
        },

        /**
         *create the message object and attached on this thread.
         * When the message object is create, this method call insert_message for,
         * displaying this message on the DOM.
         * @param : {object} data from calling RPC to "message_read"
         */
        
        create_message_object: function (data) {
            var self = this;

            data.thread_level = self.thread_level || 0;
            data.options = _.extend(data.options || {}, self.options);

            if (data.type=='expandable') {
                var message = new edi_simple.ThreadExpandable(self, data, {'context':{
                    'default_model': data.model || self.context.default_model,
                    'default_res_id': data.res_id || self.context.default_res_id,
                    'default_parent_id': self.id,
                }});
            } else {
                data.record_name= (data.record_name != '' && data.record_name) || (self.parent_message && self.parent_message.record_name);
                var message = new edi_simple.ThreadMessage(self, data, {'context':{
                    'default_model': data.model,
                    'default_res_id': data.res_id,
                    'default_parent_id': data.id,
                }});
            }

            // check if the message is already create
            for (var i in self.messages) {
                if (message.id && self.messages[i] && self.messages[i].id == message.id) {
                    self.messages[i].destroy();
                }
            }
            self.messages.push( message );

            return message;
        },

        /**
         *insert the message on the DOM.
         * All message (and expandable message) are sorted. The method get the
         * older and newer message to insert the message (before, after).
         * If there are no older or newer, the message is prepend or append to
         * the thread (parent object or on root thread for flat view).
         * The sort is define by the thread_level (O for newer on top).
         * @param : {object} ThreadMessage object
         */
        insert_message: function (message, dom_insert_after, prepend) {
            var self=this;
            if (this.options.show_compact_message > this.thread_level) {
                //this.instantiate_compose_message();
                //this.compose_message.do_show_compact();
            }

            this.$('.oe_view_nocontent').remove();
            if (dom_insert_after && dom_insert_after.parent()[0] == self.$el[0]) {
                message.insertAfter(dom_insert_after);
            } else if (prepend) {
                message.prependTo(self.$el);
            } else {
                message.appendTo(self.$el);
            }
            message.$el.hide().fadeIn(500);

            return message
        },
        
        /**
         *get the parent thread of the messages.
         * Each message is send to his parent object (or parent thread flat mode) for creating the object message.
         * @param : {Array} datas from calling RPC to "message_read"
         */
        switch_new_message: function (records, dom_insert_after) {
            var self=this;
            var dom_insert_after = typeof dom_insert_after == 'object' ? dom_insert_after : false;
            _(records).each(function (record) {
                var thread = self.browse_thread({
                    'id': record.parent_id, 
                    'default_return_top_thread':true
                });
                // create object and attach to the thread object
                var message = thread.create_message_object( record );
                // insert the message on dom
                thread.insert_message( message, dom_insert_after);
            });
            if (!records.length && this.options.root_thread == this) {
                this.no_message();
            }
        },

        /**
         * this method is call when the widget of a message or an expandable message is destroy
         * in this thread. The this.messages array is filter to remove this message
         */
        on_message_detroy: function (message) {

            this.messages = _.filter(this.messages, function (val) { return !val.isDestroyed(); });
            if (this.options.root_thread == this && !this.messages.length) {
                this.no_message();
            }
            return false;

        },

        /**
         * Convert a destroyed message into a expandable message
         */
        /*
        message_to_expandable: function (message) {

            if (!this.thread_level || message.isDestroyed()) {
                message.destroy();
                return false;
            }

            var messages = _.sortBy( this.messages, function (val) { return val.id; });
            var it = _.indexOf( messages, message );

            var msg_up = message.$el.prev('.oe_msg');
            var msg_down = message.$el.next('.oe_msg');
            var msg_up = msg_up.hasClass('oe_msg_expandable') ? _.find( this.messages, function (val) { return val.$el[0] == msg_up[0]; }) : false;
            var msg_down = msg_down.hasClass('oe_msg_expandable') ? _.find( this.messages, function (val) { return val.$el[0] == msg_down[0]; }) : false;

            var message_dom = [ ["id", "=", message.id] ];

            if ( msg_up && msg_up.type == "expandable" && msg_down && msg_down.type == "expandable") {
                // concat two expandable message and add this message to this dom
                msg_up.domain = mail.ChatterUtils.expand_domain( msg_up.domain );
                msg_down.domain = mail.ChatterUtils.expand_domain( msg_down.domain );

                msg_down.domain = ['|','|'].concat( msg_up.domain ).concat( message_dom ).concat( msg_down.domain );

                if ( !msg_down.max_limit ) {
                    msg_down.nb_messages += 1 + msg_up.nb_messages;
                }

                msg_up.$el.remove();
                msg_up.destroy();

                msg_down.reinit();

            } else if ( msg_up && msg_up.type == "expandable") {
                // concat preview expandable message and this message to this dom
                msg_up.domain = mail.ChatterUtils.expand_domain( msg_up.domain );
                msg_up.domain = ['|'].concat( msg_up.domain ).concat( message_dom );
                
                msg_up.nb_messages++;

                msg_up.reinit();

            } else if ( msg_down && msg_down.type == "expandable") {
                // concat next expandable message and this message to this dom
                msg_down.domain = mail.ChatterUtils.expand_domain( msg_down.domain );
                msg_down.domain = ['|'].concat( msg_down.domain ).concat( message_dom );
                
                // it's maybe a message expandable for the max limit read message
                if ( !msg_down.max_limit ) {
                    msg_down.nb_messages++;
                }
                
                msg_down.reinit();

            } else {
                // create a expandable message
                var expandable = new mail.ThreadExpandable(this, {
                    'model': message.model,
                    'parent_id': message.parent_id,
                    'nb_messages': 1,
                    'thread_level': message.thread_level,
                    'parent_id': message.parent_id,
                    'domain': message_dom,
                    'options': message.options,
                    }, {
                    'context':{
                        'default_model': message.model || this.context.default_model,
                        'default_res_id': message.res_id || this.context.default_res_id,
                        'default_parent_id': this.id,
                    }
                });

                // add object on array and DOM
                this.messages.push(expandable);
                expandable.insertAfter(message.$el);
            }

            // destroy message
            message.destroy();

            return true;
        },*/
    });

    /**
     * ------------------------------------------------------------
     * mail : root Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of messages with thread options. Its main
     * use is to receive a context and a domain, and to delegate the message
     * fetching and displaying to the Thread widget.
     */
    instance.web.client_actions.add('edi_simple.Widget', 'instance.edi_simple.Widget');
    edi_simple.Widget = instance.web.Widget.extend({
        template: 'edi_simple.Root',

        /**
         * @param {Object} parent parent
         * @param {Array} [domain]
         * @param {Object} [context] context of the thread. It should
         *   contain at least default_model, default_res_id. Please refer to
         *   the compose_message widget for more information about it.
         * @param {Object} [options]
         *...  @param {Number} [truncate_limit=250] number of character to
         *      display before having a "show more" link; note that the text
         *      will not be truncated if it does not have 110% of the parameter
         *...  @param {Boolean} [show_record_name] display the name and link for do action
         *...  @param {boolean} [show_reply_button] display the reply button
         *...  @param {boolean} [show_read_unread_button] display the read/unread button
         *...  @param {int} [display_indented_thread] number thread level to indented threads.
         *      other are on flat mode
         *...  @param {Boolean} [show_compose_message] allow to display the composer
         *...  @param {Boolean} [show_compact_message] display the compact message on the thread
         *      when the user clic on this compact mode, the composer is open
         *...  @param {Array} [message_ids] List of ids to fetch by the root thread.
         *      When you use this option, the domain is not used for the fetch root.
         *     @param {String} [no_message] Message to display when there are no message
         *     @param {Boolean} [show_link] Display partner (authors, followers...) on link or not
         *     @param {Boolean} [compose_as_todo] The root composer mark automatically the message as todo
         *     @param {Boolean} [readonly] Read only mode, hide all action buttons and composer
         */
        init: function (parent, action) {
            this._super(parent, action);
            var self = this;
            this.action = _.clone(action);
            this.domain = this.action.domain || this.action.params.domain || [];
            this.context = this.action.context || this.action.params.context || {};

            this.action.params = _.extend({
                'display_indented_thread' : -1,
                'show_reply_button' : false,
                'show_read_unread_button' : false,
                'truncate_limit' : 250,
                'show_record_name' : true,
                'show_compose_message' : false,
                'show_compact_message' : false,
                'compose_placeholder': false,
                'show_link': true,
                'view_inbox': false,
                'message_ids': undefined,
                'compose_as_todo' : false,
                'readonly' : false,
                'emails_from_on_composer': true,
                'fetch_limit': 30   // limit of chatter messages
            }, this.action.params);

            this.action.params.help = this.action.help || false;
        },

        start: function (options) {
            this._super.apply(this, arguments);
            this.message_render();
        },
        
        /**
        * create an object "related_menu"
        * contains the menu widget and the sub menu related of this wall
        */
        do_reload_menu_emails: function () {
            var menu = instance.webclient.menu;
            if (!menu || !menu.current_menu) {
                return $.when();
            }
            return menu.rpc("/web/menu/load_needaction", {'menu_ids': [menu.current_menu]}).done(function(r) {
                menu.on_needaction_loaded(r);
            }).then(function () {
                menu.trigger("need_action_reloaded");
            });
        },

        /**
         *Create the root thread and display this object in the DOM.
         * Call the no_message method then c all the message_fetch method 
         * of this root thread to display the messages.
         */
        message_render: function (search) {

            this.thread = new edi_simple.Thread(this, {}, {
                'domain' : this.domain,
                'context' : this.context,
                'options': this.action.params,
            });

            this.thread.appendTo( this.$el );

            if (this.action.params.show_compose_message) {
                //this.thread.instantiate_compose_message();
                //this.thread.compose_message.do_show_compact();
            }

            this.thread.message_fetch(null, null, this.action.params.message_ids);

        },

    });


    /**
     * ------------------------------------------------------------
     * mail_thread Widget
     * ------------------------------------------------------------
     *
     * This widget handles the display of messages on a document. Its main
     * use is to receive a context and a domain, and to delegate the message
     * fetching and displaying to the Thread widget.
     * Use Help on the field to display a custom "no message loaded"
     */
    instance.web.form.widgets.add('edi_thread', 'openerp.edi_simple.RecordThread');
    edi_simple.RecordThread = instance.web.form.AbstractField.extend({
        template: 'edi_simple.record_thread',

        init: function (parent, node) {
            this._super.apply(this, arguments);
            this.ParentViewManager = parent;
            this.node = _.clone(node);
            this.node.params = _.extend({
                'display_indented_thread': -1,
                'show_reply_button': false,
                'show_read_unread_button': true,
                'read_action': 'unread',
                'show_record_name': false,
                'show_compact_message': 1,
                'display_log_button' : true,
            }, this.node.params);
            if (this.node.attrs.placeholder) {
                this.node.params.compose_placeholder = this.node.attrs.placeholder;
            }
            if (this.node.attrs.readonly) {
                this.node.params.readonly = this.node.attrs.readonly;
            }
            if ('display_log_button' in this.options) {
                this.node.params.display_log_button = this.options.display_log_button;
            }
            this.domain = (this.node.params && this.node.params.domain) || (this.field && this.field.domain) || [];

            if (!this.ParentViewManager.is_action_enabled('edit')) {
                this.node.params.show_link = false;
            }
        },

        start: function () {
            this._super.apply(this, arguments);
            // NB: check the actual_mode property on view to know if the view is in create mode anymore
            this.view.on("change:actual_mode", this, this._check_visibility);
            this._check_visibility();
        },

        _check_visibility: function () {
            this.$el.toggle(this.view.get("actual_mode") !== "create");
        },

        render_value: function () {
            var self = this;

            if (! this.view.datarecord.id || instance.web.BufferedDataSet.virtual_id_regex.test(this.view.datarecord.id)) {
                this.$('oe_mail_thread').hide();
                return;
            }
            this.node.params = _.extend(this.node.params, {
                'message_ids': this.get_value(),
                'show_compose_message': false,
            });
            this.node.context = {
                'mail_read_set_read': true,  // set messages as read in Chatter
                'default_res_id': this.view.datarecord.id || false,
                'default_model': this.view.model || false,
            };

            if (this.root) {
                $('<span class="oe_mail-placeholder"/>').insertAfter(this.root.$el);
                this.root.destroy();
            }
            // create and render Thread widget
            this.root = new edi_simple.Widget(this, _.extend(this.node, {
                'domain' : (this.domain || []).concat([['model', '=', this.view.model], ['res_id', '=', this.view.datarecord.id]]),
            }));

            return this.root.replace(this.$('.oe_mail-placeholder'));
        },
    });



};
