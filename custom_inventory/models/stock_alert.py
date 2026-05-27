from odoo import models, fields, api
from odoo.exceptions import UserError


class CustomStockAlert(models.Model):
    _name = 'custom.stock.alert'
    _description = 'Stock Alert'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reference'
    _order = 'create_date desc'

    reference = fields.Char(
        string='Reference', readonly=True, default='New', copy=False
    )
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product', required=True, tracking=True
    )
    product_id = fields.Many2one(
        'product.product', string='Product Variant',
        domain="[('product_tmpl_id', '=', product_tmpl_id)]"
    )
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    alert_type = fields.Selection([
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('overstock', 'Overstock'),
        ('expiry', 'Near Expiry'),
        ('critical', 'Critical Level'),
    ], string='Alert Type', required=True, tracking=True)
    current_qty = fields.Float(string='Current Qty', tracking=True)
    min_qty = fields.Float(string='Min Qty Threshold')
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('ignored', 'Ignored'),
    ], string='Status', default='open', tracking=True)
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Important'),
        ('2', 'Very Urgent'),
        ('3', 'Critical'),
    ], string='Priority', default='0')
    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True)
    resolution_note = fields.Text(string='Resolution Note')
    resolved_date = fields.Datetime(string='Resolved On', readonly=True)
    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'custom.stock.alert') or 'New'
        return super().create(vals_list)

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_resolve(self):
        self.write({
            'state': 'resolved',
            'resolved_date': fields.Datetime.now(),
        })

    def action_ignore(self):
        self.write({'state': 'ignored'})

    def action_reopen(self):
        self.write({'state': 'open', 'resolved_date': False})

    @api.model
    def _cron_generate_alerts(self):
        """Scheduled action: scan all products and create alerts for low/out stock."""
        products = self.env['product.template'].search([
            ('type', '=', 'consu'),
            ('min_stock_qty', '>', 0),
        ])
        for tmpl in products:
            qty = sum(tmpl.product_variant_ids.mapped('qty_available'))
            existing = self.search([
                ('product_tmpl_id', '=', tmpl.id),
                ('state', 'in', ['open', 'in_progress']),
            ])
            if qty <= 0 and not existing.filtered(lambda a: a.alert_type == 'out_of_stock'):
                self.create({
                    'product_tmpl_id': tmpl.id,
                    'alert_type': 'out_of_stock',
                    'current_qty': qty,
                    'min_qty': tmpl.min_stock_qty,
                    'priority': '3',
                })
            elif 0 < qty <= tmpl.min_stock_qty and not existing.filtered(
                    lambda a: a.alert_type in ['low_stock', 'critical']):
                alert_type = 'critical' if qty <= tmpl.min_stock_qty * 0.5 else 'low_stock'
                self.create({
                    'product_tmpl_id': tmpl.id,
                    'alert_type': alert_type,
                    'current_qty': qty,
                    'min_qty': tmpl.min_stock_qty,
                    'priority': '2' if alert_type == 'critical' else '1',
                })
