# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import UserError

class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    @api.model
    def _get_approval_adjustment(self):
        IrValue = self.env['ir.values'].sudo()
        approval_on_off = IrValue.get_default('stock.config.settings', 'approval_adjustment')
        return approval_on_off

    approval_matrix = fields.Many2one('inv_adj.approving_matrix', string='Approval Matrix', compute='_get_approval_matrix', store=True, help=''' approval matrix will autofill base on selected warehouse ''')
    approval_line_ids = fields.One2many('inv_adj.approving_matrix_line', 'matrix_adj_id', string='Approval line', compute='_get_approval_matrix', store=True)
    state = fields.Selection(string='Status', selection=[
        ('draft', 'Draft'),
        ('confirm', 'In Progress'),
        ('wait_approve', 'Waiting For Approval'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled'),
        ('done', 'Validated'),
        ('reject','Rejected')],
        copy=False, index=True, readonly=True,
        default='draft')
    approval_state = fields.Selection(related='state')
    approval_adjustment = fields.Boolean(string='Approval Matrix Inventory Adjustment', default=_get_approval_adjustment)
    is_show_approve = fields.Boolean(string='Is Show Approve Button', 
                            compute='_is_show_approve', store=False)
    approval_matrix_line_id = fields.Many2one('inv_adj.approving_matrix_line', string='Approval Matrix Line', compute='_get_approve_matrix_line', store=False)

    @api.multi
    def _get_approve_matrix_line(self):
        for record in self:
            if record.state == 'wait_approve':
                matrix_line = sorted(record.approval_line_ids.filtered(lambda r:r.state == 'wait'), key=lambda r:r.sequence)
                if len(matrix_line) > 0:
                    matrix_line_id = matrix_line[0]
                    if self.env.user.id in matrix_line_id.approver.ids and self.env.user.id != matrix_line_id.last_approved.id:
                        record.approval_matrix_line_id = matrix_line_id.id
                    else:
                        record.approval_matrix_line_id = False
                else:
                    record.approval_matrix_line_id = False
            else:
                record.approval_matrix_line_id = False

    @api.multi
    def _is_show_approve(self):
        for record in self:
            user = self.env.user
            if record.approval_matrix_line_id and user.id in record.approval_matrix_line_id.approver.ids \
                and user.id not in record.approval_matrix_line_id.approved_users.ids:
                record.is_show_approve = True
            else:
                record.is_show_approve = False

    @api.depends('location_id', 'approval_adjustment', 'new_price')
    def _get_approval_matrix(self):
        for record in self:
            approving_matrix_id = self.env['inv_adj.approving_matrix']
            if record.location_id and not record.new_price:
                approving_matrix_id = self.env['inv_adj.approving_matrix'].search([('adj_type','in',('non', 'both')), '|',('location_child_ids', 'in', record.location_id.ids),('location_ids', 'in', record.location_id.ids)], limit=1)
            elif record.location_id and record.new_price:
                approving_matrix_id = self.env['inv_adj.approving_matrix'].search([('adj_type','in',('value', 'both')), '|',('location_child_ids', 'in', record.location_id.ids),('location_ids', 'in', record.location_id.ids)], limit=1)
            if approving_matrix_id:
                record.approval_matrix = approving_matrix_id.id
                data = []
                if approving_matrix_id.matrix_line_ids:
                    for line in approving_matrix_id.matrix_line_ids:
                        data.append((0, 0, {
                                'sequence': line.sequence,
                                'approver': [(6, 0, line.approver.ids)],
                                'minimal_approval': line.minimal_approval,
                                'state': 'draft'
                            }))
                record.approval_line_ids = data
            else:
                record.approval_matrix = False

    @api.multi
    def action_wait_approve(self):
        for record in self:
            record.write({'state': 'wait_approve'})
            if record.approval_line_ids:
                approver = record.approval_line_ids[0].approver[0]
                template_id = self.env.ref('approving_matrix_inventory_adjustment.email_template_request_for_approval')
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': approver.partner_id.email,
                    'approver_name': approver.name,
                    'requested_by': self.env.user.name,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
                record.approval_line_ids.write({'state': 'wait', 'time_stamp': datetime.now()})

    @api.multi
    def action_approved(self):
        for record in self:
            user = self.env.user
            email_to = ''
            approver_name = ''
            requested_by = ''
            if record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.approver.ids and \
                    user.id not in approval_matrix_line_id.approved_users.ids:
                    approval_matrix_line_id.write({'last_approved': self.env.user.id, 'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimal_approval != len(approval_matrix_line_id.approved_users):
                        for approver_user in approval_matrix_line_id.approver:
                            if approver_user.id not in approval_matrix_line_id.approved_users.ids:
                                approver_name = approver_user.name
                                requested_by = self.env.user.name
                                email_to = approver_user.partner_id.email
                                break
                        if approver_name and requested_by and email_to:
                            template_id = self.env.ref('approving_matrix_inventory_adjustment.email_template_adjusment_user_approval_mail')
                            ctx = {
                                'email_from': self.env.user.company_id.email,
                                'email_to': email_to,
                                'approver_name': approver_name,
                            }
                            template_id.with_context(ctx).send_mail(record.id, True)
                if approval_matrix_line_id.minimal_approval == len(approval_matrix_line_id.approved_users.ids):
                    approval_matrix_line_id.write({'state': 'approve', 'time_stamp': datetime.now()})
                    next_approval_matrix_line_id = record.approval_line_ids.filtered(lambda r:r.state != 'approve')
                    if next_approval_matrix_line_id and next_approval_matrix_line_id[0].approver:
                        template_id = self.env.ref('approving_matrix_inventory_adjustment.email_template_adjusment_user_approval_mail')
                        ctx = {
                            'email_from': self.env.user.company_id.email,
                            'email_to': next_approval_matrix_line_id[0].approver[0].partner_id.email,
                            'approver_name': next_approval_matrix_line_id[0].approver[0].name,
                        }
                        template_id.with_context(ctx).send_mail(record.id, True)
            if len(record.approval_line_ids) == len(record.approval_line_ids.filtered(lambda r:r.state == 'approve')):
                template_id = self.env.ref('approving_matrix_inventory_adjustment.email_template_adjusment_final_user_approval_mail')
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': record.resp.partner_id.email or record.create_uid.partner_id.email,
                    'approver_name': record.resp.name or record.create_uid.name,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
                record.write({'state': 'approved'})

    @api.multi
    def action_reject(self):
        for record in self:
            record.write({'state': 'reject'})
            if record.approval_line_ids:
                record.approval_line_ids.write({'state': 'reject', 'time_stamp': datetime.now()})

    @api.multi
    def action_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            if record.approval_line_ids:
                record.approval_line_ids.write({'state': 'draft', 'time_stamp': False})

