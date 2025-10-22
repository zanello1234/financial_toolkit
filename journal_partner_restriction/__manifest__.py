{
    'name': 'Journal Partner Restriction',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Restrict partners by journal for invoices and bills',
    'description': """
        This module allows to restrict which partners can be selected
        when creating invoices or bills based on the journal configuration.
        
        Features:
        - Add restriction option to journals
        - Assign specific partners to journals
        - Filter partner selection based on journal in moves
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}