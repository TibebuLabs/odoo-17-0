from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    custom_notes = fields.Text(string='Internal Notes')
    priority_level = fields.Selection([
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('critical', 'Critical'),
    ], string='Priority Level', default='normal', tracking=True)
    expected_completion = fields.Datetime(string='Expected Completion')
    quality_check_done = fields.Boolean(string='Quality Check Done', default=False)
    quality_check_by = fields.Many2one('res.users', string='Checked By')
    quality_check_date = fields.Datetime(string='Check Date')
    total_product_count = fields.Integer(
        string='Total Products', compute='_compute_totals'
    )
    total_qty = fields.Float(
        string='Total Quantity', compute='_compute_totals'
    )

    @api.depends('move_ids_without_package')
    def _compute_totals(self):
        for pick in self:
            pick.total_product_count = len(pick.move_ids_without_package)
            pick.total_qty = sum(pick.move_ids_without_package.mapped('product_uom_qty'))

    def action_mark_quality_checked(self):
        self.write({
            'quality_check_done': True,
            'quality_check_by': self.env.user.id,
            'quality_check_date': fields.Datetime.now(),
        })


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    manager_id = fields.Many2one('res.users', string='Warehouse Manager')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    capacity = fields.Float(string='Storage Capacity (m³)')
    current_utilization = fields.Float(
        string='Utilization (%)', compute='_compute_utilization'
    )
    notes = fields.Text(string='Notes')

    def _compute_utilization(self):
        for wh in self:
            if wh.capacity and wh.capacity > 0:
                quant_count = self.env['stock.quant'].search_count([
                    ('location_id', 'child_of', wh.lot_stock_id.id),
                ])
                wh.current_utilization = min((quant_count / wh.capacity) * 100, 100)
            else:
                wh.current_utilization = 0.0
