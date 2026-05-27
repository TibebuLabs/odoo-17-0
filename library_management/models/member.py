from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LibraryMember(models.Model):
    _name = 'library.member'
    _description = 'Library Member'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    member_id = fields.Char(string='Member ID', readonly=True, default='New')
    email = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Phone')
    address = fields.Text(string='Address')
    membership_date = fields.Date(string='Member Since', default=fields.Date.today)
    expiry_date = fields.Date(string='Membership Expiry')
    state = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    ], string='Status', default='active', tracking=True)
    borrow_ids = fields.One2many('library.borrow', 'member_id', string='Borrow History')
    borrow_count = fields.Integer(string='Books Borrowed', compute='_compute_borrow_count')
    active_borrow_count = fields.Integer(string='Currently Borrowed', compute='_compute_borrow_count')
    total_fine = fields.Float(string='Total Fine Due', compute='_compute_total_fine')
    photo = fields.Binary(string='Photo')
    max_books = fields.Integer(string='Max Books Allowed', default=3)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('member_id', 'New') == 'New':
                vals['member_id'] = self.env['ir.sequence'].next_by_code('library.member') or 'New'
        return super().create(vals_list)

    def _compute_borrow_count(self):
        for member in self:
            member.borrow_count = len(member.borrow_ids)
            member.active_borrow_count = len(
                member.borrow_ids.filtered(lambda b: b.state == 'borrowed'))

    def _compute_total_fine(self):
        for member in self:
            member.total_fine = sum(member.borrow_ids.filtered(
                lambda b: b.state in ['returned', 'overdue']
            ).mapped('fine_amount'))

    def action_suspend(self):
        self.state = 'suspended'

    def action_activate(self):
        self.state = 'active'

    def action_view_borrows(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Borrow History',
            'res_model': 'library.borrow',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
        }
