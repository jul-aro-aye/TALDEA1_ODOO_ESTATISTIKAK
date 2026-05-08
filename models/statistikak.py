import json
import logging
from datetime import datetime
from urllib import parse as urlparse
from urllib import error as urlerror
from urllib import request as urlrequest

from odoo import api, fields, models
from odoo.exceptions import UserError


_LOGGER = logging.getLogger(__name__)

DEFAULT_API_BASE_URL = "http://192.168.10.5:5093"

WEEKDAY_SELECTION = [
    ("monday", "Astelehena"),
    ("tuesday", "Asteartea"),
    ("wednesday", "Asteazkena"),
    ("thursday", "Osteguna"),
    ("friday", "Ostirala"),
    ("saturday", "Larunbata"),
    ("sunday", "Igandea"),
]


class JatetxekoSyncDashboard(models.Model):
    _name = "jatetxeko.sync.dashboard"
    _description = "Jatetxeko Estatistikak sinkronizazio panela"

    name = fields.Char(required=True, default="Sinkronizazio panela")
    api_base_url = fields.Char(
        string="APIaren oinarrizko URLa",
        required=True,
        default=DEFAULT_API_BASE_URL,
        help="Datuak sinkronizatzeko erabiltzen den kanpoko APIaren oinarrizko URLa.",
    )
    last_sync = fields.Datetime(string="Azken sinkronizazioa", readonly=True)
    last_sync_message = fields.Text(string="Emaitza", readonly=True)
    zerbitzari_kopurua = fields.Integer(
        string="Zerbitzariak", compute="_compute_totals", readonly=True
    )
    plater_kopurua = fields.Integer(
        string="Platerak", compute="_compute_totals", readonly=True
    )
    mahai_kopurua = fields.Integer(string="Mahaiak", compute="_compute_totals", readonly=True)
    eskaera_kopurua = fields.Integer(
        string="Eskaerak", compute="_compute_totals", readonly=True
    )
    faktura_kopurua = fields.Integer(
        string="Fakturak", compute="_compute_totals", readonly=True
    )

    @api.depends("last_sync")
    def _compute_totals(self):
        zerbitzari_model = self.env["jatetxeko.zerbitzaria"]
        plater_model = self.env["jatetxeko.platera"]
        mahai_model = self.env["jatetxeko.mahaia"]
        eskaera_model = self.env["jatetxeko.eskaera"]
        faktura_model = self.env["jatetxeko.faktura"]

        zerbitzari_count = zerbitzari_model.search_count([])
        plater_count = plater_model.search_count([])
        mahai_count = mahai_model.search_count([])
        eskaera_count = eskaera_model.search_count([])
        faktura_count = faktura_model.search_count([])

        for record in self:
            record.zerbitzari_kopurua = zerbitzari_count
            record.plater_kopurua = plater_count
            record.mahai_kopurua = mahai_count
            record.eskaera_kopurua = eskaera_count
            record.faktura_kopurua = faktura_count

    def action_sync_data(self):
        for record in self:
            payload = record._fetch_sync_payload()
            record._sync_payload(payload)
            record.write(
                {
                    "last_sync": fields.Datetime.now(),
                    "last_sync_message": "Sinkronizazioa ondo burutu da.",
                }
            )

        return {
            "type": "ir.actions.act_window",
            "res_model": "jatetxeko.sync.dashboard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }

    @api.model
    def cron_sync_data(self):
        dashboard = self.search([], limit=1)
        if not dashboard:
            dashboard = self.create(
                {
                    "name": "Sinkronizazio panela",
                    "api_base_url": DEFAULT_API_BASE_URL,
                }
            )

        try:
            payload = dashboard._fetch_sync_payload()
            dashboard._sync_payload(payload)
            dashboard.write(
                {
                    "last_sync": fields.Datetime.now(),
                    "last_sync_message": "Sinkronizazio automatikoa ondo burutu da.",
                }
            )
        except Exception as exc:  # pragma: no cover - defensivo para cron
            _LOGGER.exception("Errorea APIko estatistikak sinkronizatzean")
            dashboard.write(
                {
                    "last_sync": fields.Datetime.now(),
                    "last_sync_message": f"Errorea sinkronizazio automatikoan: {exc}",
                }
            )

    def _fetch_sync_payload(self):
        self.ensure_one()
        base_url = self._normalize_api_base_url(self.api_base_url or DEFAULT_API_BASE_URL).rstrip("/")
        endpoint = f"{base_url}/api/odoo/sinkronizazioa"
        request = urlrequest.Request(endpoint, headers={"Accept": "application/json"})

        try:
            with urlrequest.urlopen(request, timeout=30) as response:
                raw_body = response.read().decode("utf-8-sig")
        except urlerror.HTTPError as exc:
            raise UserError(f"APIak HTTP {exc.code} errorea itzuli du.") from exc
        except urlerror.URLError as exc:
            raise UserError(
                "Ezin izan da APIarekin konektatu. Egiaztatu oinarrizko URLa eta APIa martxan dagoela."
            ) from exc

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise UserError("APIak ez du baliozko JSONik itzuli.") from exc

        code = data.get("Code", data.get("code"))
        message = data.get("Message", data.get("message"))
        payloads = data.get("Datuak", data.get("datuak")) or []

        if code != 200:
            raise UserError(message or "APIak errore bat itzuli du.")

        if not payloads:
            raise UserError("APIak ez du sinkronizatzeko daturik itzuli.")

        return payloads[0]

    @staticmethod
    def _normalize_api_base_url(base_url):
        parsed = urlparse.urlparse(base_url)
        if parsed.hostname not in {"localhost", "127.0.0.1"}:
            return base_url

        host = "192.168.10.5"
        netloc = host
        if parsed.port:
            netloc = f"{host}:{parsed.port}"

        return urlparse.urlunparse(
            (
                parsed.scheme or "http",
                netloc,
                parsed.path or "",
                parsed.params or "",
                parsed.query or "",
                parsed.fragment or "",
            )
        )

    def _sync_payload(self, payload):
        zerbitzariak = payload.get("zerbitzariak", [])
        platerak = payload.get("platerak", [])
        mahaiak = payload.get("mahaiak", [])
        eskaerak = payload.get("eskaerak", [])
        fakturak = payload.get("fakturak", [])

        self.env["jatetxeko.zerbitzaria"].sync_from_api(zerbitzariak)
        self.env["jatetxeko.platera"].sync_from_api(platerak)
        self.env["jatetxeko.mahaia"].sync_from_api(mahaiak)
        self.env["jatetxeko.eskaera"].sync_from_api(eskaerak)
        self.env["jatetxeko.eskaera.lerroa"].sync_from_api(eskaerak)
        self.env["jatetxeko.faktura"].sync_from_api(fakturak)


class JatetxekoApiSyncMixin(models.AbstractModel):
    _name = "jatetxeko.api.sync.mixin"
    _description = "APIarekin sinkronizatzeko funtzio komunak"

    api_id = fields.Integer(string="API IDa", required=True, index=True)
    active = fields.Boolean(default=True)

    def _get_existing_by_api_id(self, api_ids):
        records = self.with_context(active_test=False).search([("api_id", "in", api_ids)])
        return {record.api_id: record for record in records}

    def _deactivate_missing(self, api_ids):
        domain = [("api_id", "not in", api_ids)] if api_ids else []
        missing = self.with_context(active_test=False).search(domain)
        if missing:
            missing.write({"active": False})


class JatetxekoZerbitzaria(models.Model):
    _name = "jatetxeko.zerbitzaria"
    _inherit = "jatetxeko.api.sync.mixin"
    _description = "APIarekin sinkronizatutako zerbitzaria"
    _order = "name"
    _sql_constraints = [
        ("jatetxeko_zerbitzaria_api_id_uniq", "unique(api_id)", "API IDak bakarra izan behar du."),
    ]

    name = fields.Char(string="Izena", required=True)
    emaila = fields.Char(string="Posta elektronikoa")
    pasahitza = fields.Char(string="Pasahitza", copy=False)
    rola_izena = fields.Char(string="Rola")
    txat = fields.Boolean(string="Txata")

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("skip_api_create"):
            return super().create(vals_list)

        for vals in vals_list:
            if vals.get("api_id"):
                continue

            api_payload = self._create_zerbitzaria_in_api(vals)
            vals["api_id"] = api_payload["id"]
            vals.setdefault("emaila", api_payload.get("emaila"))
            vals["rola_izena"] = api_payload.get("rolaIzena") or api_payload.get("rola_izena") or "zerbitzaria"
            vals["txat"] = api_payload.get("txat", vals.get("txat", False))
            vals["active"] = True

        return super().create(vals_list)

    def _create_zerbitzaria_in_api(self, vals):
        dashboard = self.env["jatetxeko.sync.dashboard"].search([], limit=1)
        base_url = (
            JatetxekoSyncDashboard._normalize_api_base_url(
                dashboard.api_base_url if dashboard else DEFAULT_API_BASE_URL
            )
            .rstrip("/")
        )
        endpoint = f"{base_url}/api/erabiltzaileak"
        payload = {
            "erabiltzailea": vals.get("name"),
            "emaila": vals.get("emaila") or "",
            "pasahitza": vals.get("pasahitza"),
            "txat": vals.get("txat", False),
        }

        if not payload["erabiltzailea"]:
            raise UserError("Zerbitzariaren izena beharrezkoa da.")

        if not payload["pasahitza"]:
            raise UserError("Pasahitza beharrezkoa da zerbitzaria APIan sortzeko.")

        body = json.dumps(payload).encode("utf-8")
        api_request = urlrequest.Request(
            endpoint,
            data=body,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlrequest.urlopen(api_request, timeout=30) as response:
                raw_body = response.read().decode("utf-8-sig")
        except urlerror.HTTPError as exc:
            error_body = exc.read().decode("utf-8-sig") if exc.fp else ""
            raise UserError(f"APIak HTTP {exc.code} errorea itzuli du: {error_body}") from exc
        except urlerror.URLError as exc:
            raise UserError("Ezin izan da APIarekin konektatu zerbitzaria sortzeko.") from exc

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise UserError("APIak ez du baliozko JSONik itzuli zerbitzaria sortzean.") from exc

        code = data.get("Code", data.get("code"))
        message = data.get("Message", data.get("message"))
        api_items = data.get("Datuak", data.get("datuak")) or []

        if code != 200:
            raise UserError(message or "APIak errore bat itzuli du zerbitzaria sortzean.")

        if not api_items:
            raise UserError("APIak ez du sortutako zerbitzariaren daturik itzuli.")

        api_payload = api_items[0]
        api_id = api_payload.get("id")
        if not api_id:
            raise UserError("APIak ez du sortutako zerbitzariaren IDrik itzuli.")

        return api_payload

    def sync_from_api(self, items):
        api_ids = [item["id"] for item in items]
        existing_by_api_id = self._get_existing_by_api_id(api_ids)

        for item in items:
            vals = {
                "api_id": item["id"],
                "name": item.get("izena") or item.get("erabiltzailea") or f"Zerbitzaria {item['id']}",
                "emaila": item.get("emaila"),
                "rola_izena": item.get("rolaIzena"),
                "txat": item.get("txat", False),
                "active": True,
            }
            record = existing_by_api_id.get(item["id"])
            if record:
                record.write(vals)
            else:
                self.with_context(skip_api_create=True).create(vals)

        self._deactivate_missing(api_ids)


class JatetxekoPlatera(models.Model):
    _name = "jatetxeko.platera"
    _inherit = "jatetxeko.api.sync.mixin"
    _description = "APIarekin sinkronizatutako platera"
    _order = "name"
    _sql_constraints = [
        ("jatetxeko_platera_api_id_uniq", "unique(api_id)", "API IDak bakarra izan behar du."),
    ]

    name = fields.Char(string="Izena", required=True)
    prezioa = fields.Float(string="Prezioa")
    kategoria_id = fields.Integer(string="API kategoria")
    stock_aktuala = fields.Integer(string="Uneko stocka")

    def sync_from_api(self, items):
        api_ids = [item["id"] for item in items]
        existing_by_api_id = self._get_existing_by_api_id(api_ids)

        for item in items:
            vals = {
                "api_id": item["id"],
                "name": item.get("izena") or f"Platera {item['id']}",
                "prezioa": item.get("prezioa", 0.0),
                "kategoria_id": item.get("kategoriaId") or item.get("kategoria_id") or 0,
                "stock_aktuala": item.get("stockAktuala") or item.get("stock_aktuala") or 0,
                "active": True,
            }
            record = existing_by_api_id.get(item["id"])
            if record:
                record.write(vals)
            else:
                self.create(vals)

        self._deactivate_missing(api_ids)


class JatetxekoMahaia(models.Model):
    _name = "jatetxeko.mahaia"
    _inherit = "jatetxeko.api.sync.mixin"
    _description = "APIarekin sinkronizatutako mahaia"
    _order = "zenbakia"
    _sql_constraints = [
        ("jatetxeko_mahaia_api_id_uniq", "unique(api_id)", "API IDak bakarra izan behar du."),
    ]

    name = fields.Char(string="Izena", required=True)
    zenbakia = fields.Integer(string="Zenbakia")
    kapazitatea = fields.Integer(string="Edukiera")
    egoera = fields.Char(string="Egoera")

    def sync_from_api(self, items):
        api_ids = [item["id"] for item in items]
        existing_by_api_id = self._get_existing_by_api_id(api_ids)

        for item in items:
            zenbakia = item.get("zenbakia") or 0
            vals = {
                "api_id": item["id"],
                "name": f"Mahaia {zenbakia}",
                "zenbakia": zenbakia,
                "kapazitatea": item.get("kapazitatea", 0),
                "egoera": item.get("egoera"),
                "active": True,
            }
            record = existing_by_api_id.get(item["id"])
            if record:
                record.write(vals)
            else:
                self.create(vals)

        self._deactivate_missing(api_ids)


class JatetxekoEskaera(models.Model):
    _name = "jatetxeko.eskaera"
    _inherit = "jatetxeko.api.sync.mixin"
    _description = "APIarekin sinkronizatutako eskaera"
    _order = "sortze_data desc, id desc"
    _sql_constraints = [
        ("jatetxeko_eskaera_api_id_uniq", "unique(api_id)", "API IDak bakarra izan behar du."),
    ]

    name = fields.Char(string="Izena", required=True)
    zerbitzaria_id = fields.Many2one("jatetxeko.zerbitzaria", string="Zerbitzaria")
    mahaia_id = fields.Many2one("jatetxeko.mahaia", string="Mahaia")
    komensalak = fields.Integer(string="Komentsalak")
    egoera = fields.Char(string="Egoera")
    sukaldea_egoera = fields.Char(string="Sukaldeko egoera")
    sortze_data = fields.Datetime(string="Eskaeraren data")
    itxiera_data = fields.Datetime(string="Itxiera data")
    txanda = fields.Char(string="Txanda")
    asteko_eguna = fields.Selection(WEEKDAY_SELECTION, string="Asteko eguna", store=True)
    hileko_eguna = fields.Integer(string="Hileko eguna", store=True)
    sortze_eguna = fields.Date(string="Eguna", store=True)
    sortze_hilabetea = fields.Integer(string="Hilabetea", store=True)
    sortze_urtea = fields.Integer(string="Urtea", store=True)
    pedido_kopurua = fields.Integer(string="Eskaera kopurua", default=1)
    lerro_ids = fields.One2many("jatetxeko.eskaera.lerroa", "eskaera_id", string="Lerroak")

    def sync_from_api(self, items):
        zerbitzari_model = self.env["jatetxeko.zerbitzaria"].with_context(active_test=False)
        mahai_model = self.env["jatetxeko.mahaia"].with_context(active_test=False)
        api_ids = [item["id"] for item in items]
        existing_by_api_id = self._get_existing_by_api_id(api_ids)

        for item in items:
            sortze_data = self._parse_datetime(item.get("sortzeData"))
            itxiera_data = self._parse_datetime(item.get("itxieraData"))
            vals = {
                "api_id": item["id"],
                "name": item.get("izena") or f"Eskaera {item['id']}",
                "zerbitzaria_id": zerbitzari_model.search(
                    [("api_id", "=", item.get("erabiltzaileId"))], limit=1
                ).id,
                "mahaia_id": mahai_model.search(
                    [("api_id", "=", item.get("mahaiaId"))], limit=1
                ).id,
                "komensalak": item.get("komensalak") or 0,
                "egoera": item.get("egoera"),
                "sukaldea_egoera": item.get("sukaldeaEgoera"),
                "sortze_data": sortze_data,
                "itxiera_data": itxiera_data,
                "txanda": item.get("txanda"),
                "asteko_eguna": self._weekday_key(sortze_data),
                "hileko_eguna": sortze_data.day if sortze_data else 0,
                "sortze_eguna": sortze_data.date() if sortze_data else False,
                "sortze_hilabetea": sortze_data.month if sortze_data else 0,
                "sortze_urtea": sortze_data.year if sortze_data else 0,
                "pedido_kopurua": 1,
                "active": True,
            }
            record = existing_by_api_id.get(item["id"])
            if record:
                record.write(vals)
            else:
                self.create(vals)

        self._deactivate_missing(api_ids)

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return False
        if isinstance(value, datetime):
            return value
        try:
            return fields.Datetime.to_datetime(value)
        except (TypeError, ValueError):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                raise UserError(f"Data formatua ez da zuzena: {value}")

    @staticmethod
    def _weekday_key(date_value):
        if not date_value:
            return False
        weekday_map = {
            0: "monday",
            1: "tuesday",
            2: "wednesday",
            3: "thursday",
            4: "friday",
            5: "saturday",
            6: "sunday",
        }
        return weekday_map.get(date_value.weekday())


class JatetxekoEskaeraLerroa(models.Model):
    _name = "jatetxeko.eskaera.lerroa"
    _inherit = "jatetxeko.api.sync.mixin"
    _description = "APIarekin sinkronizatutako eskaera lerroa"
    _order = "eskaera_id desc, id desc"
    _sql_constraints = [
        (
            "jatetxeko_eskaera_lerroa_api_id_uniq",
            "unique(api_id)",
            "API IDak bakarra izan behar du.",
        ),
    ]

    name = fields.Char(string="Deskribapena", required=True)
    eskaera_id = fields.Many2one("jatetxeko.eskaera", string="Eskaera", required=True, ondelete="cascade")
    platera_id = fields.Many2one("jatetxeko.platera", string="Platera")
    sortze_eguna = fields.Date(related="eskaera_id.sortze_eguna", string="Eguna", store=True)
    sortze_hilabetea = fields.Integer(
        related="eskaera_id.sortze_hilabetea", string="Hilabetea", store=True
    )
    sortze_urtea = fields.Integer(related="eskaera_id.sortze_urtea", string="Urtea", store=True)
    kantitatea = fields.Integer(string="Kantitatea")
    prezio_unitarioa = fields.Float(string="Unitateko prezioa")
    guztira = fields.Float(string="Lerro osoa")

    def sync_from_api(self, items):
        eskaera_model = self.env["jatetxeko.eskaera"].with_context(active_test=False)
        plater_model = self.env["jatetxeko.platera"].with_context(active_test=False)
        flattened_items = []
        for eskaera in items:
            for lerro in eskaera.get("lerroak", []):
                line_item = dict(lerro)
                line_item["eskaeraApiId"] = eskaera["id"]
                flattened_items.append(line_item)

        api_ids = [item["id"] for item in flattened_items]
        existing_by_api_id = self._get_existing_by_api_id(api_ids)

        for item in flattened_items:
            eskaera = eskaera_model.search([("api_id", "=", item["eskaeraApiId"])], limit=1)
            if not eskaera:
                continue

            platera = plater_model.search([("api_id", "=", item.get("produktuaId"))], limit=1)
            vals = {
                "api_id": item["id"],
                "name": item.get("produktuaIzena") or f"Linea {item['id']}",
                "eskaera_id": eskaera.id,
                "platera_id": platera.id,
                "kantitatea": item.get("kantitatea") or 0,
                "prezio_unitarioa": item.get("prezioUnitarioa") or 0.0,
                "guztira": item.get("guztira") or 0.0,
                "active": True,
            }
            record = existing_by_api_id.get(item["id"])
            if record:
                record.write(vals)
            else:
                self.create(vals)

        self._deactivate_missing(api_ids)


class JatetxekoFaktura(models.Model):
    _name = "jatetxeko.faktura"
    _inherit = "jatetxeko.api.sync.mixin"
    _description = "APIarekin sinkronizatutako faktura"
    _order = "data desc, id desc"
    _sql_constraints = [
        ("jatetxeko_faktura_api_id_uniq", "unique(api_id)", "API IDak bakarra izan behar du."),
    ]

    name = fields.Char(string="Izena", required=True)
    eskaera_id = fields.Many2one("jatetxeko.eskaera", string="Eskaera")
    data = fields.Datetime(string="Fakturaren data")
    totala = fields.Float(string="Guztira")
    pdf_izena = fields.Char(string="PDF fitxategia")
    asteko_eguna = fields.Selection(WEEKDAY_SELECTION, string="Asteko eguna", store=True)
    faktura_eguna = fields.Date(string="Eguna", store=True)
    faktura_hilabetea = fields.Integer(string="Hilabetea", store=True)
    faktura_urtea = fields.Integer(string="Urtea", store=True)

    def sync_from_api(self, items):
        eskaera_model = self.env["jatetxeko.eskaera"].with_context(active_test=False)
        api_ids = [item["id"] for item in items]
        existing_by_api_id = self._get_existing_by_api_id(api_ids)

        for item in items:
            data = JatetxekoEskaera._parse_datetime(item.get("data"))
            vals = {
                "api_id": item["id"],
                "name": f"Faktura {item['id']}",
                "eskaera_id": eskaera_model.search(
                    [("api_id", "=", item.get("eskaeraId"))], limit=1
                ).id,
                "data": data,
                "totala": item.get("totala") or 0.0,
                "pdf_izena": item.get("pdfIzena"),
                "asteko_eguna": JatetxekoEskaera._weekday_key(data),
                "faktura_eguna": data.date() if data else False,
                "faktura_hilabetea": data.month if data else 0,
                "faktura_urtea": data.year if data else 0,
                "active": True,
            }
            record = existing_by_api_id.get(item["id"])
            if record:
                record.write(vals)
            else:
                self.create(vals)

        self._deactivate_missing(api_ids)
