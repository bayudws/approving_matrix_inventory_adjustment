# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InvAdjApproveMatrixLine(models.Model):
    _name = 'inv_adj.approving_matrix_line'
    _description = 'Inv Adj Approve Matrix Line'

    @api.model
    def default_get(self, fields):
        res = super(InvAdjApproveMatrixLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'matrix_line_ids' in context_keys:
                if len(self._context.get('matrix_line_ids')) > 0:
                    next_sequence = len(self._context.get('matrix_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Char(string='Sequence')
    approver = fields.Many2many('res.users', string='Approver', required=True)
    minimal_approval = fields.Integer(string='Minimum approver', required=True, default=1)
    approved_users = fields.Many2many('res.users', 'approved_user_inv_adj_rel', 'std_mr_id', 'user_id', string='Users')
    matrix_id = fields.Many2one('inv_adj.approving_matrix')
    matrix_adj_id = fields.Many2one('stock.inventory')
    state = fields.Selection([('draft', ''),('wait','Waiting for Approve'), ('approve','Approved'),('reject','Rejected')],
            string="Status", default='draft')
    last_approved = fields.Many2one('res.users', string='Users')
    time_stamp =fields.Datetime(string='Time')