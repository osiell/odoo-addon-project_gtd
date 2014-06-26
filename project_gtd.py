# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import sys

from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _

class project_gtd_context(osv.osv):
    _name = "project.gtd.context"
    _description = "Context"
    _columns = {
        'name': fields.char('Context', size=64, required=True, select=1, translate=1),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of contexts."),
    }
    _defaults = {
        'sequence': 1
    }
    _order = "sequence, name"

project_gtd_context()


class project_gtd_timebox(osv.osv):
    _name = "project.gtd.timebox"
    _order = "sequence"
    _columns = {
        'name': fields.char('Timebox', size=64, required=True, select=1, translate=1),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of timebox."),
        'icon': fields.selection(tools.icons, 'Icon', size=64),
        'fold': fields.boolean(
            u"Folded by default",
            help=("This timebox is not visible in kanban view, when there are "
                  "no records in that timebox to display.")),
    }
    _defaults = {
        'fold': False,
    }

project_gtd_timebox()

class project_task(osv.osv):
    _inherit = "project.task"
    _columns = {
        'timebox_id': fields.many2one('project.gtd.timebox', "Timebox",help="Time-laps during which task has to be treated"),
        'context_id': fields.many2one('project.gtd.context', "Context",help="The context place where user has to treat task"),
     }

    def copy_data(self, cr, uid, id, default=None, context=None):
        if context is None:
            context = {}
        if not default:
            default = {}
        default['timebox_id'] = False
        default['context_id'] = False
        return super(project_task,self).copy_data(cr, uid, id, default, context)

    def _get_context(self, cr, uid, context=None):
        ids = self.pool.get('project.gtd.context').search(cr, uid, [], context=context)
        return ids and ids[0] or False

    _defaults = {
        'context_id': _get_context
    }

    def next_timebox(self, cr, uid, ids, *args):
        timebox_obj = self.pool.get('project.gtd.timebox')
        timebox_ids = timebox_obj.search(cr,uid,[])
        if not timebox_ids: return True
        for task in self.browse(cr,uid,ids):
            timebox = task.timebox_id.id
            if not timebox:
                self.write(cr, uid, task.id, {'timebox_id': timebox_ids[0]})
            elif timebox_ids.index(timebox) != len(timebox_ids)-1:
                index = timebox_ids.index(timebox)
                self.write(cr, uid, task.id, {'timebox_id': timebox_ids[index+1]})
        return True

    def prev_timebox(self, cr, uid, ids, *args):
        timebox_obj = self.pool.get('project.gtd.timebox')
        timebox_ids = timebox_obj.search(cr,uid,[])
        for task in self.browse(cr,uid,ids):
            timebox = task.timebox_id.id
            if timebox:
                if timebox_ids.index(timebox):
                    index = timebox_ids.index(timebox)
                    self.write(cr, uid, task.id, {'timebox_id': timebox_ids[index - 1]})
                else:
                    self.write(cr, uid, task.id, {'timebox_id': False})
        return True

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        # In a GTD context, force the GTD kanban view ID
        if context.get('gtd') and view_type == 'kanban':
            model_data_obj = self.pool.get('ir.model.data')
            view_model, view_id = model_data_obj.get_object_reference(
                cr, uid, 'project_gtd', 'view_task_gtd_kanban')
        res = super(project_task,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        search_extended = False
        timebox_obj = self.pool.get('project.gtd.timebox')
        if (res['type'] == 'search') and context.get('gtd', False):
            tt = timebox_obj.browse(cr, uid, timebox_obj.search(cr,uid,[]), context=context)
            search_extended =''
            for time in tt:
                if time.icon:
                    icon = time.icon
                else :
                    icon=""
                search_extended += '''<filter domain="[('timebox_id','=', ''' + str(time.id) + ''')]" icon="''' + icon + '''" string="''' + time.name + '''" context="{'user_invisible': True}"/>\n'''
            search_extended +='''<separator orientation="vertical"/>'''

            res['arch'] = tools.ustr(res['arch']).replace('<separator name="gtdsep"/>', search_extended)

        return res

    def _read_group_timebox_ids(
            self, cr, uid, ids, domain, read_group_order=None,
            access_rights_uid=None, context=None):
        if context is None:
            context = {}
        timebox_obj = self.pool.get('project.gtd.timebox')
        order = timebox_obj._order
        access_rights_uid = access_rights_uid or uid
        if read_group_order == 'timebox_id desc':
            order = '%s desc' % order
        search_domain = []
        project_id = self._resolve_project_id_from_context(
            cr, uid, context=context)
        if project_id:
            search_domain += ['|', ('project_ids', '=', project_id)]
        #search_domain += [('id', 'in', ids)]
        timebox_ids = timebox_obj._search(
            cr, uid, search_domain, order=order,
            access_rights_uid=access_rights_uid, context=context)
        result = timebox_obj.name_get(
            cr, access_rights_uid, timebox_ids, context=context)
        # restore order of the search
        result.sort(
            lambda x, y: cmp(timebox_ids.index(x[0]), timebox_ids.index(y[0])))
        fold = {}
        for timebox in timebox_obj.browse(
                cr, access_rights_uid, timebox_ids, context=context):
            fold[timebox.id] = timebox.fold or False
        return result, fold

    _group_by_full = {
        'timebox_id': _read_group_timebox_ids,
    }

project_task()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
