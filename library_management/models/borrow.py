from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta


class LibraryBorrow(models.Model):
    _name = 'library.borrow'
    _description = 'Book Borrowing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reference'

    reference = fields.Char(string='Reference', readonly=True, default='New')
    member_id = fields.Many2one('library.member', string='Member', required=True, tracking=True)
    book_id = fields.Many2one('library.book', string='Book', required=True, tracking=True)
    borrow_date = fields.Date(string='Borrow Date', default=fields.Date.today, required=True)
    due_date = fields.Date(string='Due Date', required=True)
    return_date = fields.Date(string='Return Date', tracking=True)
    state = fields.Selection([
        ('borrowed', 'Borrowed'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('lost', 'Lost'),
    ], string='Status', default='borrowed', tracking=True)
    fine_per_day = fields.Float(string='Fine Per Day', default=5.0)
    fine_amount = fields.Float(string='Fine Amount', compute='_compute_fine', store=True)
    days_overdue = fields.Integer(string='Days Overdue', compute='_compute_fine', store=True)
    notes = fields.Text(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code('library.borrow') or 'New'
        return super().create(vals_list)

    @api.constrains('member_id', 'book_id', 'state')
    def _check_availability(self):
        for record in self:
            if record.state == 'borrowed':
                if record.book_id.available_copies < 0:
                    raise ValidationError(
                        'Book "%s" is not available!' % record.book_id.name)
                active = len(record.member_id.borrow_ids.filtered(
                    lambda b: b.state == 'borrowed' and b.id != record.id
                ))
                if active >= record.member_id.max_books:
                    raise ValidationError(
                        'Member "%s" has reached the maximum borrow limit of %d books!'
                        % (record.member_id.name, record.member_id.max_books)
                    )

    @api.depends('due_date', 'return_date', 'state')
    def _compute_fine(self):
        today = fields.Date.today()
        for record in self:
            check_date = record.return_date or today
            if record.due_date and check_date > record.due_date:
                record.days_overdue = (check_date - record.due_date).days
                record.fine_amount = record.days_overdue * record.fine_per_day
            else:
                record.days_overdue = 0
                record.fine_amount = 0.0

    @api.onchange('borrow_date')
    def _onchange_borrow_date(self):
        if self.borrow_date:
            self.due_date = self.borrow_date + timedelta(days=14)

    def action_return(self):
        for record in self:
            if record.state != 'borrowed':
                raise UserError('Only borrowed books can be returned!')
            record.return_date = fields.Date.today()
            record.state = 'overdue' if record.fine_amount > 0 else 'returned'

    def action_mark_lost(self):
        for record in self:
            record.state = 'lost'
            record.book_id.total_copies -= 1

    def action_renew(self):
        for record in self:
            if record.state != 'borrowed':
                raise UserError('Only active borrows can be renewed!')
            record.due_date = record.due_date + timedelta(days=14)

    @api.model
    def _cron_check_overdue(self):
        today = fields.Date.today()
        overdue = self.search([
            ('state', '=', 'borrowed'),
            ('due_date', '<', today),
        ])
        overdue.write({'state': 'overdue'})
