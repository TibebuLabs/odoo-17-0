from odoo import models, fields, api


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Title', required=True, tracking=True)
    isbn = fields.Char(string='ISBN', tracking=True)
    author = fields.Char(string='Author', required=True)
    publisher = fields.Char(string='Publisher')
    category_id = fields.Many2one('library.book.category', string='Category')
    publish_date = fields.Date(string='Publish Date')
    total_copies = fields.Integer(string='Total Copies', default=1)
    available_copies = fields.Integer(
        string='Available Copies', compute='_compute_available', store=True)
    cover_image = fields.Binary(string='Cover Image')
    description = fields.Text(string='Description')
    state = fields.Selection([
        ('available', 'Available'),
        ('borrowed', 'All Borrowed'),
        ('lost', 'Lost'),
    ], string='Status', default='available', tracking=True,
        compute='_compute_state', store=True)
    borrow_ids = fields.One2many('library.borrow', 'book_id', string='Borrow History')
    borrow_count = fields.Integer(string='Times Borrowed', compute='_compute_borrow_count')

    @api.depends('borrow_ids', 'borrow_ids.state', 'total_copies')
    def _compute_available(self):
        for book in self:
            borrowed = len(book.borrow_ids.filtered(lambda b: b.state == 'borrowed'))
            book.available_copies = book.total_copies - borrowed

    @api.depends('available_copies')
    def _compute_state(self):
        for book in self:
            if book.available_copies <= 0:
                book.state = 'borrowed'
            else:
                book.state = 'available'

    def _compute_borrow_count(self):
        for book in self:
            book.borrow_count = len(book.borrow_ids)

    def action_view_borrows(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Borrow History',
            'res_model': 'library.borrow',
            'view_mode': 'list,form',
            'domain': [('book_id', '=', self.id)],
        }


class LibraryBookCategory(models.Model):
    _name = 'library.book.category'
    _description = 'Book Category'

    name = fields.Char(string='Category', required=True)
    description = fields.Text(string='Description')
    book_ids = fields.One2many('library.book', 'category_id', string='Books')
    book_count = fields.Integer(string='Books', compute='_compute_book_count')

    def _compute_book_count(self):
        for cat in self:
            cat.book_count = len(cat.book_ids)
