import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class JatetxekoAPI(http.Controller):
    @http.route('/jatetxeko/egiaztatu_deskontua', type='json', auth='public', methods=['POST'], csrf=False)
    def egiaztatu_deskontua(self, kodea):
        _logger.info("Deskontu kodea egiaztatzen: %s", kodea)
        
        kode_garbia = str(kodea).strip()
        
        deskontua = request.env['jatetxeko.deskontuak'].sudo().search([
            ('name', '=ilike', kode_garbia),
            ('aktiboa', '=', True)
        ], limit=1)
        
        if deskontua:
            _logger.info("Deskontua aurkitu da: %s (%s%%)", deskontua.name, deskontua.balioa)
            return {
                'existitzen_da': True,
                'balioa': deskontua.balioa
            }
        else:
            _logger.warning("Ez da deskonturik aurkitu kode honekin: %s", kode_garbia)
            return {
                'existitzen_da': False,
                'balioa': 0
            }
