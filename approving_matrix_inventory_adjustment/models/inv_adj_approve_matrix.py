# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError
from datetime import datetime

class InvAdjApproveMatrix(models.Model):
    _name = 'inv_adj.approving_matrix'
    _description = 'Inv Adj Approve Matrix'

    name = fields.Char(string='Name', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    location_ids = fields.Many2many('stock.location', string='Location', required=True)
    location_child_ids = fields.Many2many('stock.location', 'stock_location_inv_adj_child', 'location_id', 'inv_adj_id',store=True,string='Child Locations', compute='_get_child_locations')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self:self.env.user.company_id.id)
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self:self.env.user.branch_id.id)
    matrix_line_ids = fields.One2many('inv_adj.approving_matrix_line', 'matrix_id', string='Approing Matrix Lines')
    adj_type = fields.Selection([('value', 'Adjustment With Value'), ('non', 'Adjustment'), ('both', 'Both of Them')], 
                default='both', string='For Adjustment')
    filter_location_ids = fields.Many2many('stock.location', compute='_get_stock_locations', store=False)

    @api.depends('location_child_ids')
    def _get_stock_locations(self):
        for record in self:
            record.filter_location_ids = [(6, 0, record.location_child_ids.ids)]

    _sql_constraints = [
        ('warehouse_uniq', 'unique (warehouse)', 'The warehouse must be unique!')
    ]

    @api.constrains('adj_type')
    def check_location_ids(self):
        for record in self:
            for location in record.location_ids:                                                                                        
                if record.adj_type in 'non' :
                    apporving_matrix_ids = self.search(['|', ('location_ids', 'in', location.ids), ('location_child_ids', 'in', location.ids),('adj_type','in',('both','non'))], order='id')
                    if len(apporving_matrix_ids) >= 2:
                        raise ValidationError('The location selected is already existed :\n • %s is already exist in record %s'%(location.name_get()[0][1], apporving_matrix_ids[0].name))
                if record.adj_type in 'value' :
                    apporving_matrix_ids = self.search(['|', ('location_ids', 'in', location.ids), ('location_child_ids', 'in', location.ids),('adj_type','in',('both','value'))], order='id')
                    if len(apporving_matrix_ids) >= 2:
                        raise ValidationError('The location selected is already existed :\n • %s is already exist in record %s'%(location.name_get()[0][1], apporving_matrix_ids[0].name))
                if record.adj_type in 'both' :
                    apporving_matrix_ids = self.search(['|', ('location_ids', 'in', location.ids), ('location_child_ids', 'in', location.ids),('adj_type','in',('non','value','both'))], order='id')
                    if len(apporving_matrix_ids) >= 2:
                        raise ValidationError('The location selected is already existed :\n • %s is already exist in record %s'%(location.name_get()[0][1], apporving_matrix_ids[0].name))
                

    @api.model
    def default_get(self, fields):
        res = super(InvAdjApproveMatrix, self).default_get(fields)
        res.update({'create_uid': self.env.uid, 'create_date': datetime.strftime(datetime.now(), tools.DEFAULT_SERVER_DATETIME_FORMAT)})
        return res

    # @api.onchange('warehouse_id')
    # def change_warehouse(self):
    #     if self.warehouse_id:
    #         self.location_ids = [(6, 0, self.warehouse_id.lot_stock_id.ids)]
    #     else:
    #         self.location_ids = [(6, 0, [])]
            
    @api.onchange('warehouse_id')
    def onchange_warehouse(self):
        """
        Make warehouse compatible with company
        """
        location_ids = []
        if self.warehouse_id:
            location_obj = self.env['stock.location']
            store_location_id = self.warehouse_id.view_location_id.id
            addtional_ids = location_obj.search([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
            for location in addtional_ids:
                if location.location_id.id not in addtional_ids.ids:
                    location_ids.append(location.id)
            self.location_ids = [(6, 0, location_ids)]
        else:
            self.location_ids = [(6, 0, [])]

    @api.depends('location_ids')
    def _get_child_locations(self):
        for record in self:
            if record.location_ids:
                child_location_ids = self.env['stock.location'].search([('id', 'child_of', record.location_ids.ids), ('id', 'not in', record.location_ids.ids)])
                record.location_child_ids = [(6, 0, child_location_ids.ids)]
            else:
                record.location_child_ids = [(6, 0, [])]

    @api.onchange('location_ids')
    def change_location(self):
        return {'domain': {'location_child_ids': [('id', 'not in', self.location_ids.ids)]}}

    @api.constrains('matrix_line_ids', 'matrix_line_ids.approver', 'matrix_line_ids.minimal_approval')
    def check_minimum_approval(self):
        for record in self:
            if record.matrix_line_ids:
                for line in record.matrix_line_ids:
                    if len(line.approver.ids) < line.minimal_approval:
                        raise ValidationError('The number of approver must be same or equal with quantity minimal_approver!')