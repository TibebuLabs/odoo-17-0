from odoo import models, fields, api
from datetime import timedelta


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Smart reorder settings
    min_stock_qty = fields.Float(
        string='Min Stock (Reorder Point)',
        default=0.0,
        help='When stock falls below this level, a low stock alert is triggered.'
    )
    max_stock_qty = fields.Float(
        string='Max Stock Level',
        default=0.0,
        help='Ideal maximum quantity to keep in stock.'
    )
    reorder_qty = fields.Float(
        string='Reorder Quantity',
        default=0.0,
        help='Quantity to order when restocking.'
    )
    lead_time_days = fields.Integer(
        string='Lead Time (Days)',
        default=7,
        help='Expected days from order to delivery.'
    )
    stock_alert_ids = fields.One2many(
        'custom.stock.alert', 'product_tmpl_id', string='Stock Alerts'
    )
    alert_count = fields.Integer(
        string='Active Alerts', compute='_compute_alert_count'
    )
    # Analytics
    avg_daily_consumption = fields.Float(
        string='Avg Daily Consumption', compute='_compute_consumption', store=True
    )
    days_of_stock = fields.Float(
        string='Days of Stock Remaining', compute='_compute_days_of_stock'
    )
    stock_status = fields.Selection([
        ('ok', 'OK'),
        ('low', 'Low Stock'),
        ('critical', 'Critical'),
        ('overstock', 'Overstock'),
        ('out', 'Out of Stock'),
    ], string='Stock Status', compute='_compute_stock_status', store=True)
    last_restock_date = fields.Date(string='Last Restock Date')
    supplier_ref = fields.Char(string='Supplier Reference')
    storage_location = fields.Char(string='Preferred Storage Location')
    notes = fields.Text(string='Internal Notes')

    def _compute_alert_count(self):
        for tmpl in self:
            tmpl.alert_count = self.env['custom.stock.alert'].search_count([
                ('product_tmpl_id', '=', tmpl.id),
                ('state', '=', 'open'),
            ])

    @api.depends('product_variant_ids')
    def _compute_consumption(self):
        today = fields.Date.today()
        date_from = today - timedelta(days=30)
        for tmpl in self:
            moves = self.env['stock.move'].search([
                ('product_id.product_tmpl_id', '=', tmpl.id),
                ('state', '=', 'done'),
                ('picking_id.picking_type_code', '=', 'outgoing'),
                ('date', '>=', date_from),
            ])
            total_out = sum(moves.mapped('product_qty'))
            tmpl.avg_daily_consumption = total_out / 30.0 if total_out else 0.0

    @api.depends('avg_daily_consumption', 'product_variant_ids.qty_available')
    def _compute_days_of_stock(self):
        for tmpl in self:
            qty = sum(tmpl.product_variant_ids.mapped('qty_available'))
            if tmpl.avg_daily_consumption > 0:
                tmpl.days_of_stock = qty / tmpl.avg_daily_consumption
            else:
                tmpl.days_of_stock = 999.0

    @api.depends('product_variant_ids.qty_available', 'min_stock_qty', 'max_stock_qty')
    def _compute_stock_status(self):
        for tmpl in self:
            qty = sum(tmpl.product_variant_ids.mapped('qty_available'))
            if qty <= 0:
                tmpl.stock_status = 'out'
            elif tmpl.min_stock_qty > 0 and qty <= tmpl.min_stock_qty * 0.5:
                tmpl.stock_status = 'critical'
            elif tmpl.min_stock_qty > 0 and qty <= tmpl.min_stock_qty:
                tmpl.stock_status = 'low'
            elif tmpl.max_stock_qty > 0 and qty > tmpl.max_stock_qty:
                tmpl.stock_status = 'overstock'
            else:
                tmpl.stock_status = 'ok'

    def action_view_alerts(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Alerts',
            'res_model': 'custom.stock.alert',
            'view_mode': 'tree,form',
            'domain': [('product_tmpl_id', '=', self.id)],
        }

    def action_create_reorder(self):
        """Open replenishment for this product."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reorder Rules',
            'res_model': 'stock.warehouse.orderpoint',
            'view_mode': 'tree,form',
            'domain': [('product_id.product_tmpl_id', '=', self.id)],
            'context': {
                'default_product_id': self.product_variant_ids[:1].id,
                'default_qty_to_order': self.reorder_qty or 1.0,
            },
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    barcode_scan_count = fields.Integer(
        string='Scan Count', default=0,
        help='Number of times this product was scanned in inventory operations.'
    )
    last_inventory_date = fields.Datetime(string='Last Inventory Check')
