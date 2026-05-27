from odoo import models, fields, api


class StockLocation(models.Model):
    _inherit = 'stock.location'

    location_type_custom = fields.Selection([
        ('shelf', 'Shelf'),
        ('bin', 'Bin'),
        ('cold_storage', 'Cold Storage'),
        ('hazmat', 'Hazardous Materials'),
        ('bulk', 'Bulk Storage'),
        ('staging', 'Staging Area'),
    ], string='Location Type')
    max_weight = fields.Float(string='Max Weight (kg)')
    barcode_label = fields.Char(string='Barcode Label')
    responsible_id = fields.Many2one('res.users', string='Responsible')
    temperature_controlled = fields.Boolean(string='Temperature Controlled', default=False)
    notes = fields.Text(string='Notes')
    product_count = fields.Integer(
        string='Products Stored', compute='_compute_product_count'
    )

    def _compute_product_count(self):
        for loc in self:
            loc.product_count = self.env['stock.quant'].search_count([
                ('location_id', '=', loc.id),
                ('quantity', '>', 0),
            ])
