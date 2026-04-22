from odoo import models, fields

class Deskontuak(models.Model):
    _name = 'jatetxeko.deskontuak'
    _description = 'Jatetxeko Deskontuak'

    name = fields.Char(string='Kodea', required=True)
    balioa = fields.Float(string='Deskontua (%)', required=True)
    aktiboa = fields.Boolean(string='Aktiboa', default=True)
