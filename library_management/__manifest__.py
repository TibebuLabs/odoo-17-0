{
    'name': 'Library Management System',
    'version': '17.0.1.0.0',
    'category': 'Services',
    'summary': 'Manage books, members, borrowing and returns',
    'description': '''
        Library Management System
        =========================
        - Book catalog management
        - Member registration
        - Borrow and return tracking
        - Overdue fine calculation
        - Dashboard and reports
    ''',
    'author': 'Tibe',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/book_views.xml',
        'views/member_views.xml',
        'views/borrow_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
