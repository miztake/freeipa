# Authors:
#   Martin Kosek <mkosek@redhat.com>
#   Pavel Zuna <pzuna@redhat.com>
#
# Copyright (C) 2010  Red Hat
# see file 'COPYING' for use and warranty information
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import six
import copy

from ipaclient.frontend import MethodOverride, CommandOverride
from ipalib import errors
from ipalib.dns import (get_part_rrtype,
                        get_record_rrtype,
                        has_cli_options,
                        iterate_rrparams_by_parts,
                        record_name_format)
from ipalib.parameters import Bool
from ipalib.plugable import Registry
from ipalib import _, ngettext
from ipapython.dnsutil import DNSName

if six.PY3:
    unicode = str

register = Registry()

# most used record types, always ask for those in interactive prompt
_top_record_types = ('A', 'AAAA', )
_rev_top_record_types = ('PTR', )
_zone_top_record_types = ('NS', 'MX', 'LOC', )


def __get_part_param(cmd, part, output_kw, default=None):
    name = part.name
    label = unicode(part.label)
    optional = not part.required

    output_kw[name] = cmd.prompt_param(part,
                                       optional=optional,
                                       label=label)


def prompt_parts(rrtype, cmd, mod_dnsvalue=None):
    mod_parts = None
    if mod_dnsvalue is not None:
        name = record_name_format % rrtype.lower()
        mod_parts = cmd.api.Command.dnsrecord_split_parts(
            name, mod_dnsvalue)['result']

    user_options = {}
    parts = [p for p in cmd.params() if get_part_rrtype(p.name) == rrtype]
    if not parts:
        return user_options

    for part_id, part in enumerate(parts):
        if mod_parts:
            default = mod_parts[part_id]
        else:
            default = None

        __get_part_param(cmd, part, user_options, default)

    return user_options


def prompt_missing_parts(rrtype, cmd, kw, prompt_optional=False):
    user_options = {}
    parts = [p for p in cmd.params() if get_part_rrtype(p.name) == rrtype]
    if not parts:
        return user_options

    for part in parts:
        name = part.name

        if name in kw:
            continue

        optional = not part.required
        if optional and not prompt_optional:
            continue

        default = part.get_default(**kw)
        __get_part_param(cmd, part, user_options, default)

    return user_options


class DNSZoneMethodOverride(MethodOverride):
    def get_options(self):
        for option in super(DNSZoneMethodOverride, self).get_options():
            if option.name == 'idnsallowdynupdate':
                option = option.clone_retype(option.name, Bool)
            yield option


@register(override=True)
class dnszone_add(DNSZoneMethodOverride):
    pass


@register(override=True)
class dnszone_mod(DNSZoneMethodOverride):
    pass


@register(override=True)
class dnsrecord_add(MethodOverride):
    no_option_msg = 'No options to add a specific record provided.\n' \
            "Command help may be consulted for all supported record types."

    def interactive_prompt_callback(self, kw):
        try:
            has_cli_options(self, kw, self.no_option_msg)

            # Some DNS records were entered, do not use full interactive help
            # We should still ask user for required parts of DNS parts he is
            # trying to add in the same way we do for standard LDAP parameters
            #
            # Do not ask for required parts when any "extra" option is used,
            # it can be used to fill all required params by itself
            new_kw = {}
            for rrparam in iterate_rrparams_by_parts(self, kw,
                                                     skip_extra=True):
                rrtype = get_record_rrtype(rrparam.name)
                user_options = prompt_missing_parts(rrtype, self, kw,
                                                    prompt_optional=False)
                new_kw.update(user_options)
            kw.update(new_kw)
            return
        except errors.OptionError:
            pass

        try:
            idnsname = DNSName(kw['idnsname'])
        except Exception as e:
            raise errors.ValidationError(name='idnsname', error=unicode(e))

        try:
            zonename = DNSName(kw['dnszoneidnsname'])
        except Exception as e:
            raise errors.ValidationError(name='dnszoneidnsname', error=unicode(e))

        # check zone type
        if idnsname.is_empty():
            common_types = u', '.join(_zone_top_record_types)
        elif zonename.is_reverse():
            common_types = u', '.join(_rev_top_record_types)
        else:
            common_types = u', '.join(_top_record_types)

        self.Backend.textui.print_plain(_(u'Please choose a type of DNS resource record to be added'))
        self.Backend.textui.print_plain(_(u'The most common types for this type of zone are: %s\n') %\
                                          common_types)

        ok = False
        while not ok:
            rrtype = self.Backend.textui.prompt(_(u'DNS resource record type'))

            if rrtype is None:
                return

            try:
                name = record_name_format % rrtype.lower()
                param = self.params[name]

                if 'no_option' in param.flags:
                    raise ValueError()
            except (KeyError, ValueError):
                all_types = u', '.join(get_record_rrtype(p.name)
                                       for p in self.params()
                                       if (get_record_rrtype(p.name) and
                                           'no_option' not in p.flags))
                self.Backend.textui.print_plain(_(u'Invalid or unsupported type. Allowed values are: %s') % all_types)
                continue
            ok = True

        user_options = prompt_parts(rrtype, self)
        kw.update(user_options)


@register(override=True)
class dnsrecord_mod(MethodOverride):
    no_option_msg = 'No options to modify a specific record provided.'

    def interactive_prompt_callback(self, kw):
        try:
            has_cli_options(self, kw, self.no_option_msg, True)
        except errors.OptionError:
            pass
        else:
            # some record type entered, skip this helper
            return

        # get DNS record first so that the NotFound exception is raised
        # before the helper would start
        dns_record = self.api.Command['dnsrecord_show'](kw['dnszoneidnsname'], kw['idnsname'])['result']

        self.Backend.textui.print_plain(_("No option to modify specific record provided."))

        # ask user for records to be removed
        self.Backend.textui.print_plain(_(u'Current DNS record contents:\n'))
        record_params = []

        for attr in dns_record:
            try:
                param = self.params[attr]
            except KeyError:
                continue
            rrtype = get_record_rrtype(param.name)
            if not rrtype:
                continue

            record_params.append((param, rrtype))
            rec_type_content = u', '.join(dns_record[param.name])
            self.Backend.textui.print_plain(u'%s: %s' % (param.label, rec_type_content))
        self.Backend.textui.print_plain(u'')

        # ask what records to remove
        for param, rrtype in record_params:
            rec_values = list(dns_record[param.name])
            for rec_value in dns_record[param.name]:
                rec_values.remove(rec_value)
                mod_value = self.Backend.textui.prompt_yesno(
                        _("Modify %(name)s '%(value)s'?") % dict(name=param.label, value=rec_value), default=False)
                if mod_value is True:
                    user_options = prompt_parts(rrtype, self,
                                                mod_dnsvalue=rec_value)
                    kw[param.name] = [rec_value]
                    kw.update(user_options)

                    if rec_values:
                         self.Backend.textui.print_plain(ngettext(
                            u'%(count)d %(type)s record skipped. Only one value per DNS record type can be modified at one time.',
                            u'%(count)d %(type)s records skipped. Only one value per DNS record type can be modified at one time.',
                            0) % dict(count=len(rec_values), type=rrtype))
                         break


@register(override=True)
class dnsrecord_del(MethodOverride):
    no_option_msg = _('Neither --del-all nor options to delete a specific record provided.\n'\
            "Command help may be consulted for all supported record types.")

    def interactive_prompt_callback(self, kw):
        if kw.get('del_all', False):
            return
        try:
            has_cli_options(self, kw, self.no_option_msg)
        except errors.OptionError:
            pass
        else:
            # some record type entered, skip this helper
            return

        # get DNS record first so that the NotFound exception is raised
        # before the helper would start
        dns_record = self.api.Command['dnsrecord_show'](kw['dnszoneidnsname'], kw['idnsname'])['result']

        self.Backend.textui.print_plain(_("No option to delete specific record provided."))
        user_del_all = self.Backend.textui.prompt_yesno(_("Delete all?"), default=False)

        if user_del_all is True:
            kw['del_all'] = True
            return

        # ask user for records to be removed
        self.Backend.textui.print_plain(_(u'Current DNS record contents:\n'))
        present_params = []

        for attr in dns_record:
            try:
                param = self.params[attr]
            except KeyError:
                continue
            if not get_record_rrtype(param.name):
                continue

            present_params.append(param)
            rec_type_content = u', '.join(dns_record[param.name])
            self.Backend.textui.print_plain(u'%s: %s' % (param.label, rec_type_content))
        self.Backend.textui.print_plain(u'')

        # ask what records to remove
        for param in present_params:
            deleted_values = []
            for rec_value in dns_record[param.name]:
                user_del_value = self.Backend.textui.prompt_yesno(
                        _("Delete %(name)s '%(value)s'?")
                            % dict(name=param.label, value=rec_value), default=False)
                if user_del_value is True:
                     deleted_values.append(rec_value)
            if deleted_values:
                kw[param.name] = tuple(deleted_values)


@register(override=True)
class dnsconfig_mod(MethodOverride):
    def interactive_prompt_callback(self, kw):

        # show informative message on client side
        # server cannot send messages asynchronous
        if kw.get('idnsforwarders', False):
            self.Backend.textui.print_plain(
                _("Server will check DNS forwarder(s)."))
            self.Backend.textui.print_plain(
                _("This may take some time, please wait ..."))


@register(override=True)
class dnsforwardzone_add(MethodOverride):
    def interactive_prompt_callback(self, kw):
        # show informative message on client side
        # server cannot send messages asynchronous
        if kw.get('idnsforwarders', False):
            self.Backend.textui.print_plain(
                _("Server will check DNS forwarder(s)."))
            self.Backend.textui.print_plain(
                _("This may take some time, please wait ..."))


@register(override=True)
class dnsforwardzone_mod(MethodOverride):
    def interactive_prompt_callback(self, kw):
        # show informative message on client side
        # server cannot send messages asynchronous
        if kw.get('idnsforwarders', False):
            self.Backend.textui.print_plain(
                _("Server will check DNS forwarder(s)."))
            self.Backend.textui.print_plain(
                _("This may take some time, please wait ..."))


@register(override=True)
class dns_update_system_records(CommandOverride):
    def output_for_cli(self, textui, output, *args, **options):
        output_super = copy.deepcopy(output)
        super_res = output_super.get('result', {})
        super_res.pop('ipa_records', None)
        super_res.pop('location_records', None)

        super(dns_update_system_records, self).output_for_cli(
            textui, output_super, *args, **options)

        labels = {
            p.name: unicode(p.label) for p in self.output_params()
        }

        result = output.get('result', {})
        for key in ('ipa_records', 'location_records'):
            if result.get(key):
                textui.print_indented(u'{}:'.format(labels[key]), indent=1)
                for val in sorted(result[key]):
                    textui.print_indented(val, indent=2)
                textui.print_line(u'')

        return int(not output['value'])
