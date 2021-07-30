# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockConfig(models.TransientModel):
    _inherit = 'stock.config.settings'

    approval_adjustment = fields.Boolean(string='Approval Matrix Inventory Adjustment', default=False)

    @api.model
    def get_values(self, fields):
        IrValue = self.env['ir.values'].sudo()
        return {
            'approval_adjustment': IrValue.get_default('stock.config.settings', 'approval_adjustment'),
        }

    @api.multi
    def set_approval_adjustment(self):
        approval_matrix_menu = self.env.ref('approving_matrix_inventory_adjustment.menu_inv_adj_approving_matrix')
        approval_matrix_menu.active = self.approval_adjustment
        return self.env['ir.values'].sudo().set_default(
            'stock.config.settings', 'approval_adjustment', self.approval_adjustment)
