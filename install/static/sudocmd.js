/*  Authors:
 *    Endi Sukma Dewata <edewata@redhat.com>
 *
 * Copyright (C) 2010 Red Hat
 * see file 'COPYING' for use and warranty information
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; version 2 only
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
 */

/* REQUIRES: ipa.js, details.js, search.js, add.js, entity.js */

function ipa_sudocmd() {

    var that = ipa_entity({
        'name': 'sudocmd'
    });

    that.init = function() {

        var dialog = ipa_sudocmd_add_dialog({
            'name': 'add',
            'title': 'Add New SUDO Command'
        });
        that.add_dialog(dialog);
        dialog.init();

        var facet = ipa_sudocmd_search_facet({
            'name': 'search',
            'label': 'Search'
        });
        that.add_facet(facet);

        facet = ipa_sudocmd_details_facet({
            'name': 'details',
            'label': 'Details'
        });
        that.add_facet(facet);

        that.entity_init();
    };

    return that;
}

IPA.add_entity(ipa_sudocmd());

function ipa_sudocmd_add_dialog(spec) {

    spec = spec || {};

    var that = ipa_add_dialog(spec);

    that.superior_init = that.superior('init');

    that.init = function() {

        that.superior_init();

        that.add_field(ipa_text_widget({name:'sudocmd', label:'Command', undo: false}));
        that.add_field(ipa_text_widget({name:'description', label:'Description', undo: false}));
    };

    return that;
}

function ipa_sudocmd_search_facet(spec) {

    spec = spec || {};

    var that = ipa_search_facet(spec);

    that.init = function() {

        that.create_column({name:'sudocmd', primary_key: true});
        that.create_column({name:'description'});

        that.search_facet_init();
    };

    that.create = function(container) {

        that.search_facet_create(container);

        container.children().last().prepend(
            $('<h2/>', { 'html':   IPA.metadata.sudocmd.label  }));
        container.children().last().prepend('<br/><br/>');
    };

    that.setup = function(container) {

        that.search_facet_setup(container);

        var action_panel = that.get_action_panel();

        var li = $('li[title=sudorule]', action_panel);
        li.click(function() {
            var state = {};
            state['sudorule-entity'] = 'sudorule';
            nav_push_state(state);
            return false;
        });

        li = $('li[title=sudocmdgroup]', action_panel);
        li.click(function() {
            var state = {};
            state['sudorule-entity'] = 'sudocmdgroup';
            nav_push_state(state);
            return false;
        });
    };

    return that;
}


function ipa_sudocmd_details_facet(spec) {

    spec = spec || {};

    var that = ipa_details_facet(spec);

    that.superior_init = that.superior('init');
    that.superior_create = that.superior('create');
    that.superior_setup = that.superior('setup');

    that.init = function() {

        var section = ipa_details_list_section({
            'name': 'general',
            'label': 'General'
        });
        that.add_section(section);

        section.create_field({'name': 'sudocmd'});
        section.create_field({'name': 'description'});

        that.superior_init();
    };

    return that;
}