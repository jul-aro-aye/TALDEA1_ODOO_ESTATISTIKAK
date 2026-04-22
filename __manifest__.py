{
    'name': "Jatetxeko Estatistikak",
    'summary': "Jatetxerako estatistikak eta deskontu kudeaketa",
    'description': "Jatetxeko estatistikak modulua deskontu kodeekin",
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Sales/Point of Sale',
    'version': '0.1',
    'depends': ['base', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'jatetxeko_estatistikak/static/src/js/pos_discount.js',
            'jatetxeko_estatistikak/static/src/xml/pos_discount.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
}
