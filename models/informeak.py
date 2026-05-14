from collections import defaultdict

from odoo import fields, models


WEEKDAY_LABELS = {
    "monday": "Astelehena",
    "tuesday": "Asteartea",
    "wednesday": "Asteazkena",
    "thursday": "Osteguna",
    "friday": "Ostirala",
    "saturday": "Larunbata",
    "sunday": "Igandea",
}


class JatetxekoReportMixin(models.AbstractModel):
    _name = "jatetxeko.report.mixin"
    _description = "Jatetxeko txostenetarako laguntzailea"

    def _get_records(self, model_name, docids):
        model = self.env[model_name]
        return model.browse(docids) if docids else model.search([])

    def _generic_values(self, model_name, docids):
        docs = self._get_records(model_name, docids)
        return {
            "doc_ids": docs.ids,
            "doc_model": model_name,
            "docs": docs,
            "generated_at": fields.Datetime.now(),
        }


class ReportJatetxekoZerbitzariak(models.AbstractModel):
    _name = "report.jatetxeko_estatistikak.report_zerbitzariak"
    _inherit = "jatetxeko.report.mixin"
    _description = "Zerbitzarien txostena"

    def _get_report_values(self, docids, data=None):
        return self._generic_values("jatetxeko.zerbitzaria", docids)


class ReportJatetxekoPlaterak(models.AbstractModel):
    _name = "report.jatetxeko_estatistikak.report_platerak"
    _inherit = "jatetxeko.report.mixin"
    _description = "Plateren txostena"

    def _get_report_values(self, docids, data=None):
        return self._generic_values("jatetxeko.platera", docids)


class ReportJatetxekoMahaiak(models.AbstractModel):
    _name = "report.jatetxeko_estatistikak.report_mahaiak"
    _inherit = "jatetxeko.report.mixin"
    _description = "Mahaien txostena"

    def _get_report_values(self, docids, data=None):
        return self._generic_values("jatetxeko.mahaia", docids)


class ReportJatetxekoEskaerak(models.AbstractModel):
    _name = "report.jatetxeko_estatistikak.report_eskaerak"
    _inherit = "jatetxeko.report.mixin"
    _description = "Eskaeren txostena"

    def _get_report_values(self, docids, data=None):
        return self._generic_values("jatetxeko.eskaera", docids)


class ReportJatetxekoFakturak(models.AbstractModel):
    _name = "report.jatetxeko_estatistikak.report_fakturak"
    _inherit = "jatetxeko.report.mixin"
    _description = "Fakturen txostena"

    def _get_report_values(self, docids, data=None):
        return self._generic_values("jatetxeko.faktura", docids)


class ReportJatetxekoEskaerakZerbitzarika(models.AbstractModel):
    _name = "report.jatetxeko_estatistikak.report_eskaerak_zerbitzarika"
    _inherit = "jatetxeko.report.mixin"
    _description = "Zerbitzariko eskaeren txostena"

    def _get_report_values(self, docids, data=None):
        docs = self._get_records("jatetxeko.eskaera", docids)
        totals = defaultdict(int)
        for eskaera in docs:
            name = eskaera.zerbitzaria_id.name or "Zerbitzaririk gabe"
            totals[name] += eskaera.pedido_kopurua or 1

        rows = [{"name": name, "count": count} for name, count in sorted(totals.items())]
        return {
            "doc_ids": docs.ids,
            "doc_model": "jatetxeko.eskaera",
            "docs": docs,
            "rows": rows,
            "generated_at": fields.Datetime.now(),
        }


class ReportJatetxekoEskaerakPlaterka(models.AbstractModel):
    _name = "report.jatetxeko_estatistikak.report_eskaerak_platerka"
    _inherit = "jatetxeko.report.mixin"
    _description = "Plater bakoitzeko eskaeren txostena"

    def _get_report_values(self, docids, data=None):
        docs = self._get_records("jatetxeko.eskaera.lerroa", docids)
        totals = defaultdict(lambda: {"quantity": 0, "amount": 0.0})
        for lerroa in docs:
            name = lerroa.platera_id.name or lerroa.name or "Platerik gabe"
            totals[name]["quantity"] += lerroa.kantitatea or 0
            totals[name]["amount"] += lerroa.guztira or 0.0

        rows = [
            {"name": name, "quantity": values["quantity"], "amount": values["amount"]}
            for name, values in sorted(totals.items())
        ]
        return {
            "doc_ids": docs.ids,
            "doc_model": "jatetxeko.eskaera.lerroa",
            "docs": docs,
            "rows": rows,
            "generated_at": fields.Datetime.now(),
        }


class ReportJatetxekoEskaerakAstekoEguna(models.AbstractModel):
    _name = "report.jatetxeko_estatistikak.report_eskaerak_asteko_eguna"
    _inherit = "jatetxeko.report.mixin"
    _description = "Asteko eguneko eskaeren txostena"

    def _get_report_values(self, docids, data=None):
        docs = self._get_records("jatetxeko.eskaera", docids)
        totals = defaultdict(int)
        for eskaera in docs:
            name = WEEKDAY_LABELS.get(eskaera.asteko_eguna, "Egunik gabe")
            totals[name] += eskaera.pedido_kopurua or 1

        rows = [{"name": name, "count": count} for name, count in sorted(totals.items())]
        return {
            "doc_ids": docs.ids,
            "doc_model": "jatetxeko.eskaera",
            "docs": docs,
            "rows": rows,
            "generated_at": fields.Datetime.now(),
        }


class ReportJatetxekoFakturazioaAstekoEguna(models.AbstractModel):
    _name = "report.jatetxeko_estatistikak.report_fakturazioa_asteko_eguna"
    _inherit = "jatetxeko.report.mixin"
    _description = "Asteko eguneko fakturazioaren txostena"

    def _get_report_values(self, docids, data=None):
        docs = self._get_records("jatetxeko.faktura", docids)
        totals = defaultdict(float)
        for faktura in docs:
            name = WEEKDAY_LABELS.get(faktura.asteko_eguna, "Egunik gabe")
            totals[name] += faktura.totala or 0.0

        rows = [{"name": name, "amount": amount} for name, amount in sorted(totals.items())]
        return {
            "doc_ids": docs.ids,
            "doc_model": "jatetxeko.faktura",
            "docs": docs,
            "rows": rows,
            "generated_at": fields.Datetime.now(),
        }


class ReportJatetxekoEskaerakHilekoEguna(models.AbstractModel):
    _name = "report.jatetxeko_estatistikak.report_eskaerak_hileko_eguna"
    _inherit = "jatetxeko.report.mixin"
    _description = "Hileko eguneko eskaeren txostena"

    def _get_report_values(self, docids, data=None):
        docs = self._get_records("jatetxeko.eskaera", docids)
        totals = defaultdict(int)
        for eskaera in docs:
            name = eskaera.hileko_eguna or 0
            totals[name] += eskaera.pedido_kopurua or 1

        rows = [{"name": name, "count": count} for name, count in sorted(totals.items())]
        return {
            "doc_ids": docs.ids,
            "doc_model": "jatetxeko.eskaera",
            "docs": docs,
            "rows": rows,
            "generated_at": fields.Datetime.now(),
        }
