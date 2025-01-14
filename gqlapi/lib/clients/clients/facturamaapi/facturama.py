from abc import ABC
import base64
from datetime import datetime
import json
from enum import Enum
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from typing import Any, Dict, List, Optional
from uuid import UUID
from gqlapi.domain.models.v2.utils import InvoiceType

import requests
import strawberry
from strawberry import type as strawberry_type

from gqlapi.domain.models.v2.core import MxSatInvoicingCertificateInfo
from gqlapi.utils.domain_mapper import domain_to_dict

logger = get_logger(get_app())


@strawberry.enum
class PaymentForm(Enum):
    CASH = "01"
    MONEY_ORDER = "02"
    TRANSFER = "03"
    CARD = "04"
    TBD = "99"


PaymentFormFacturama = {
    "PUE - Pago en una sola exhibición": InvoiceType.PUE,
    "PPD - Pago en parcialidades ó diferido": InvoiceType.PPD,
}


@strawberry_type
class CustomerAddress(ABC):
    Street: Optional[str] = None
    ExteriorNumber: Optional[str] = None
    InteriorNumber: Optional[str] = None
    Neighborhood: Optional[str] = None
    ZipCode: Optional[str] = None
    Locality: Optional[str] = None
    Municipality: Optional[str] = None
    State: Optional[str] = None
    Country: Optional[str] = None


@strawberry_type
class Customer(ABC):
    Id: Optional[str] = None
    Email: Optional[str] = None
    Address: Optional[CustomerAddress] = None
    Rfc: str
    Name: str
    CfdiUse: Optional[str] = None
    TaxResidence: Optional[str] = ""
    NumRegIdTrib: Optional[str] = ""
    FiscalRegime: Optional[str] = ""
    TaxZipCode: Optional[str] = None


@strawberry_type
class Issuer(ABC):
    FiscalRegime: Optional[str] = None
    Rfc: str
    Name: Optional[str] = None
    Phone: Optional[str] = None
    TaxName: Optional[str] = None


@strawberry_type
class InternalIssuer(ABC):
    FiscalRegime: Optional[str] = None
    Rfc: str
    Email: Optional[str] = None
    Phone: Optional[str] = None
    TaxName: Optional[str] = None
    TaxAddress: Optional[CustomerAddress] = None
    IssuedIn: Optional[CustomerAddress] = None


@strawberry_type
class SatTaxes:
    Total: float
    Name: str
    Base: Optional[float] = None
    Rate: float
    IsRetention: Optional[bool] = None
    Type: Optional[str] = None
    IsFederalTax: Optional[str] = None


@strawberry_type
class TaxStamp:
    Uuid: UUID
    Date: datetime
    CfdiSign: str
    SatCertNumber: str
    SatSign: str
    RfcProvCertif: str
    AutNumProvCertif: Optional[str] = None


@strawberry_type
class Complement:
    TaxStamp: TaxStamp


@strawberry_type
class GlobalInformationFacturama:
    Periodicity: str
    Months: str
    Year: str


@strawberry_type
class Item(ABC):
    ProductCode: str
    Description: str
    UnitCode: str
    Quantity: float
    UnitPrice: Optional[float] = None
    Subtotal: Optional[float] = None
    TaxObject: Optional[str] = None
    Taxes: Optional[List[SatTaxes]] = None
    Total: float
    Discount: Optional[float] = None
    CuentaPredial: Optional[str] = None
    Unit: Optional[str] = None
    UnitValue: Optional[str] = None
    IdentificationNumber: Optional[str] = None


@strawberry_type
class RelatedDocuments(ABC):
    TaxObject: str
    Uuid: str
    Folio: str
    PaymentMethod: str
    PartialityNumber: int
    PreviousBalanceAmount: float
    AmountPaid: float
    ImpSaldoInsoluto: float


@strawberry_type
class FacturamaComplement(ABC):
    Date: str
    PaymentForm: str
    Amount: float
    RelatedDocuments: List[RelatedDocuments]


@strawberry_type
class FacturamaPayments(ABC):
    Payments: List[FacturamaComplement]


@strawberry_type
class FacturamaInternalInvoiceComplement(ABC):
    CfdiType: str
    NameId: str
    ExpeditionPlace: str
    Folio: Optional[int] = None
    Receiver: Customer
    Complemento: FacturamaPayments
    # Issuer: Issuer


@strawberry_type
class FacturamaInvoiceComplement(ABC):
    LogoUrl: Optional[str] = None
    CfdiType: str
    NameId: str
    ExpeditionPlace: str
    Folio: Optional[str] = None
    Receiver: Customer
    Observations: Optional[str] = None
    Complemento: FacturamaPayments
    Issuer: Issuer


@strawberry_type
class FacturamaInvoice(ABC):
    LogoUrl: Optional[str] = None
    CfdiType: str
    PaymentForm: str
    ExpeditionPlace: str
    PaymentMethod: str
    Date: datetime
    Folio: Optional[str] = None
    Issuer: Issuer
    Receiver: Customer
    Observations: Optional[str] = None
    Items: List[Item]
    OrdenNumber: str
    GlobalInformation: Optional[GlobalInformationFacturama] = None


@strawberry_type
class FacturamaInternalInvoice(ABC):
    Receiver: Customer
    NameId: str
    ExpeditionPlace: str
    CfdiType: str
    PaymentForm: str
    PaymentMethod: str
    Exportation: Optional[str] = None
    Date: Optional[datetime] = None
    Currency: Optional[str] = None
    Decimals: Optional[int] = None
    Serie: Optional[int] = None
    Folio: Optional[int] = None
    Items: List[Item]
    GlobalInformation: Optional[GlobalInformationFacturama] = None


@strawberry_type
class NewInvoiceResponse:
    Id: str
    CfdiType: str
    Type: str
    Serie: str
    Folio: str
    Date: datetime
    CertNumber: str
    PaymentTerms: Optional[str] = None
    PaymentMethod: Optional[str] = None
    ExpeditionPlace: str
    ExchangeRate: float
    Currency: str
    Subtotal: float
    Discount: float
    Total: float
    Observations: str
    Issuer: Issuer
    Receiver: Customer
    Items: List[Item]
    Taxes: List[SatTaxes]
    Status: str
    OriginalString: str
    Complement: Complement
    Result: Optional[str] = None


@strawberry_type
class NewInternalInvoiceResponse:
    Id: str
    CfdiType: str
    Type: str
    Serie: str
    Folio: str
    Date: datetime
    CertNumber: str
    PaymentTerms: Optional[str] = None
    PaymentMethod: Optional[str] = None
    PaymentAccountNumber: Optional[str] = None
    PaymentBankName: Optional[str] = None
    ExpeditionPlace: str
    ExchangeRate: float
    Currency: str
    Subtotal: float
    Discount: float
    Total: float
    Observations: str
    Issuer: Issuer
    Receiver: Customer
    Items: List[Item]
    Taxes: List[SatTaxes]
    Status: str
    OriginalString: str
    Complement: Complement
    Result: Optional[str] = None


class FacturamaEndpoints(Enum):
    POST_CSE = "api-lite/csds"
    PUT_CSE = "api-lite/csds/"  # +rfc
    GET_CSE = "api-lite/csds/"  # +rfc
    POST_CFDI = "api-lite/3/cfdis"
    POST_CLIENT = "client"
    GET_CLIENT = "client?page="  # + page_number
    GET_3RD_PARTY_XML_INVOICE = "cfdi/xml/issuedLite/{id}"
    GET_3RD_PARTY_PDF_INVOICE = "cfdi/pdf/issuedLite/{id}"
    GET_XML_INTERNAL_INVOICE = "cfdi/xml/issued/{id}"
    GET_PDF_INTERNAL_INVOICE = "cfdi/pdf/issued/{id}"
    GET_3RD_PARTY_CFDI_JSON = "api-lite/cfdis/{id}"
    CANCEL_3RD_PARTY_INVOICE = "api-lite/cfdis/{id}?motive={motive}"  # &uuidReplacement={uuidReplacement [Optional]
    CANCEL_INTERNAL_INVOICE = (
        "cfdi/{id}?motive={motive}"  # &uuidReplacement={uuidReplacement [Optional]
    )
    POST_INTERNAL_CFDI = "3/cfdis"
    COMPLEMENT = "3/cfdis"


class FacturamaClientApi:
    def __init__(self, usr, pasw, env) -> None:
        self.usr = usr
        self.pasw = pasw
        self.headers = {
            "Authorization": "Basic %s"
            % (
                base64.b64encode(("{}:{}".format(self.usr, self.pasw)).encode("utf-8"))
            ).decode("ascii"),
            "content-type": "application/json",
        }
        self.url_base = (
            "https://api.facturama.mx/{endpoint}"
            if env.lower() == "prod"
            else "https://apisandbox.facturama.mx/{endpoint}"
        )

    async def new_client(self, client: Customer) -> Dict[Any, Any]:
        url = self.url_base.format(endpoint=FacturamaEndpoints.POST_CLIENT.value)
        # address = domain_to_dict(client.Address)
        data = domain_to_dict(client)
        data["Address"] = domain_to_dict(client.Address)
        fact_resp = requests.post(url=url, headers=self.headers, json=data)
        if fact_resp.status_code == 201:
            return {
                "status": "ok",
                "status_code": fact_resp.status_code,
                "data": fact_resp.json(),
            }
        if fact_resp.status_code == 400:
            return {
                "status": "error",
                "status_code": fact_resp.status_code,
                "msg": fact_resp.content.decode("utf-8"),
            }
        return {
            "status": "error",
            "status_code": fact_resp.status_code,
            "msg": fact_resp.content.decode("utf-8"),
        }

    async def get_client(self, id: str) -> Dict[Any, Any]:
        pages_limit = 10
        for page in range(pages_limit):
            url = self.url_base.format(
                endpoint=FacturamaEndpoints.GET_CLIENT.value + str(page)
            )
            fact_resp = requests.get(url=url, headers=self.headers)
            if fact_resp.status_code == 200 and fact_resp.json():
                for client in fact_resp.json():
                    if client["Id"] == id:
                        if "Address" in client:
                            client["Address"] = CustomerAddress(**client["Address"])
                        client = Customer(**client)
                return {
                    "status": "ok",
                    "status_code": fact_resp.status_code,
                    "data": "client created",
                }

        return {
            "status": "error",
            "data": "not find client",
        }

    async def new_csd(
        self, mx_sat_invoice_certificate: MxSatInvoicingCertificateInfo
    ) -> Dict[Any, Any]:
        url = self.url_base
        url = url.format(endpoint=FacturamaEndpoints.POST_CSE.value)
        # read info data from files
        cer_fact_data = json.loads(mx_sat_invoice_certificate.cer_file)
        key_fact_data = json.loads(mx_sat_invoice_certificate.key_file)
        data = {
            "Rfc": mx_sat_invoice_certificate.rfc,
            "Certificate": cer_fact_data["content"],
            "PrivateKey": key_fact_data["content"],
            "PrivateKeyPassword": mx_sat_invoice_certificate.sat_pass_code,
        }

        fact_resp = requests.post(url=url, headers=self.headers, json=data)
        if fact_resp.status_code == 200:
            return {"status": "ok", "status_code": fact_resp.status_code}
        return {
            "status": "error",
            "status_code": fact_resp.status_code,
            "msg": fact_resp.content.decode("utf-8"),
        }

    async def edit_csd(
        self, mx_sat_invoice_certificate: MxSatInvoicingCertificateInfo
    ) -> Dict[Any, Any]:
        url = self.url_base
        url = url.format(
            endpoint=FacturamaEndpoints.PUT_CSE.value + mx_sat_invoice_certificate.rfc
        )
        # read info data from files
        cer_fact_data = json.loads(mx_sat_invoice_certificate.cer_file)
        key_fact_data = json.loads(mx_sat_invoice_certificate.key_file)
        data = {
            "Rfc": mx_sat_invoice_certificate.rfc,
            "Certificate": cer_fact_data["content"],
            "PrivateKey": key_fact_data["content"],
            "PrivateKeyPassword": mx_sat_invoice_certificate.sat_pass_code,
        }
        fact_resp = requests.put(url=url, headers=self.headers, json=data)
        if fact_resp.status_code == 200:
            return {
                "status": "ok",
                "status_code": fact_resp.status_code,
                "data": "CSD update",
            }
        if fact_resp.status_code == 400:
            return {
                "status": "error",
                "status_code": fact_resp.status_code,
                "msg": fact_resp.json(),
            }
        logger.warning(fact_resp.content.decode("utf-8"))
        return {
            "status": "error",
            "status_code": fact_resp.status_code,
            "msg": fact_resp.content.decode("utf-8"),
        }

    async def get_csd(self, rfc) -> Dict[Any, Any]:
        url = self.url_base.format(endpoint=FacturamaEndpoints.GET_CSE.value + rfc)

        fact_resp = requests.get(url=url, headers=self.headers)
        if fact_resp.status_code == 404:
            return {
                "status": "error",
                "status_code": fact_resp.status_code,
                "msg": "No se encontro CSD",
            }
        if fact_resp.status_code == 200:
            return {
                "data": fact_resp.json(),
                "status": "ok",
                "status_code": fact_resp.status_code,
            }
        logger.warning(fact_resp.content.decode("utf-8"))
        return {
            "msg": fact_resp.content.decode("utf-8"),
            "status": "error",
            "status_code": fact_resp.status_code,
        }

    async def new_3rd_party_invoice(self, invoice: FacturamaInvoice) -> Dict[Any, Any]:
        url = self.url_base.format(endpoint=FacturamaEndpoints.POST_CFDI.value)
        data = domain_to_dict(invoice)
        data["Date"] = data["Date"].strftime("%Y-%m-%d %H:%M:%S")
        data["Issuer"] = domain_to_dict(invoice.Issuer, skip=["phone", "TaxName"])
        data["Receiver"] = domain_to_dict(
            invoice.Receiver, skip=["Email", "Id", "TaxResidence", "NumRegIdTrib"]
        )
        data["Receiver"]["Address"] = domain_to_dict(
            invoice.Receiver.Address, skip=["Locality", "Municipality"]
        )
        item_list = []
        for items in invoice.Items:
            item = domain_to_dict(
                items, skip=["Discount", "CuentaPredial", "Unit", "UnitValue"]
            )
            taxes_list = []
            for taxes in item["Taxes"]:
                taxes_list.append(domain_to_dict(taxes, skip=["Type"]))
            item["Taxes"] = taxes_list
            item_list.append(item)
        data["Items"] = item_list
        if invoice.GlobalInformation:
            data["GlobalInformation"] = domain_to_dict(
                invoice.GlobalInformation,
                skip=["Email", "Id", "TaxResidence", "NumRegIdTrib"],
            )
        fact_resp = requests.post(url=url, headers=self.headers, json=data)
        if fact_resp.status_code == 201:
            _rmp = fact_resp.json()
            _rmp["Result"] = json.dumps(_rmp)
            _rmp["Date"] = datetime.strptime(_rmp["Date"], "%Y-%m-%dT%H:%M:%S")
            _rmp["Receiver"] = Customer(**_rmp["Receiver"])
            _rmp["Issuer"] = Issuer(**_rmp["Issuer"])
            resp_taxes_list = []
            for taxes in _rmp["Taxes"]:
                resp_taxes_list.append(SatTaxes(**taxes))
            _rmp["Taxes"] = resp_taxes_list
            resp_items_list = []
            for item in _rmp["Items"]:
                resp_taxes_list.append(Item(**item))
            _rmp["Items"] = resp_items_list
            _rmp["Complement"]["TaxStamp"] = TaxStamp(**_rmp["Complement"]["TaxStamp"])
            _rmp["Complement"] = Complement(**_rmp["Complement"])
            invoice_resp = NewInvoiceResponse(**_rmp)
            return {
                "status": "ok",
                "status_code": fact_resp.status_code,
                "data": invoice_resp,
            }
        else:
            logger.warning(
                "FACTURAMA INVOICE ERROR: " + fact_resp.content.decode("utf-8")
            )
            return {
                "status": "error",
                "status_code": fact_resp.status_code,
                "msg": fact_resp.content.decode("utf-8"),
            }

    def new_internal_invoice(self, invoice: FacturamaInternalInvoice) -> Dict[Any, Any]:
        url = self.url_base.format(endpoint=FacturamaEndpoints.POST_INTERNAL_CFDI.value)
        data = domain_to_dict(invoice)
        data["Receiver"] = domain_to_dict(
            invoice.Receiver,
            skip=["Email", "Id", "TaxResidence", "NumRegIdTrib", "Address"],
        )
        item_list = []
        for items in invoice.Items:
            item = domain_to_dict(
                items, skip=["Discount", "CuentaPredial", "Unit", "UnitValue"]
            )
            taxes_list = []
            for taxes in item["Taxes"]:
                taxes_list.append(domain_to_dict(taxes, skip=["Type"]))
            item["Taxes"] = taxes_list
            item_list.append(item)
        data["Items"] = item_list
        if invoice.GlobalInformation:
            data["GlobalInformation"] = domain_to_dict(
                invoice.GlobalInformation,
            )
        fact_resp = requests.post(url=url, headers=self.headers, json=data)
        if fact_resp.status_code == 201:
            _rmp = fact_resp.json()
            _rmp["Result"] = json.dumps(_rmp)
            _rmp["Date"] = datetime.strptime(_rmp["Date"], "%Y-%m-%dT%H:%M:%S")
            _rmp["Receiver"] = Customer(**_rmp["Receiver"])
            _rmp["Issuer"] = InternalIssuer(**_rmp["Issuer"])
            resp_taxes_list = []
            for taxes in _rmp["Taxes"]:
                resp_taxes_list.append(SatTaxes(**taxes))
            _rmp["Taxes"] = resp_taxes_list
            resp_items_list = []
            for item in _rmp["Items"]:
                resp_taxes_list.append(Item(**item))
            _rmp["Items"] = resp_items_list
            _rmp["Complement"]["TaxStamp"] = TaxStamp(**_rmp["Complement"]["TaxStamp"])
            _rmp["Complement"] = Complement(**_rmp["Complement"])
            invoice_resp = NewInternalInvoiceResponse(**_rmp)
            return {
                "status": "ok",
                "status_code": fact_resp.status_code,
                "data": invoice_resp,
            }
        else:
            logger.warning(fact_resp.content.decode("utf-8"))
            return {
                "status": "error",
                "status_code": fact_resp.status_code,
                "msg": fact_resp.content.decode("utf-8"),
            }

    async def cancel_internal_invoice_by_id(
        self, id: str, motive: str, uuid_replacement: Optional[str] = None
    ) -> Dict[Any, Any]:
        url = self.url_base.format(
            endpoint=FacturamaEndpoints.CANCEL_INTERNAL_INVOICE.value.format(
                id=id, motive=motive
            )
        )
        if uuid_replacement:
            url += "&uuidReplacement=" + uuid_replacement
        fact_resp = requests.delete(url=url, headers=self.headers)

        if fact_resp.status_code == 200:
            _resp = fact_resp.content.decode("utf-8")
            if _resp != "null":
                return {
                    "status": "ok",
                    "status_code": fact_resp.status_code,
                    "data": fact_resp.content.decode("utf-8"),
                }
            else:
                return {
                    "status": "error",
                    "status_code": fact_resp.status_code,
                    "msg": "invoice doesn't found",
                }
        else:
            logger.warning(fact_resp.content.decode("utf-8"))
            return {
                "status": "error",
                "status_code": fact_resp.status_code,
                "msg": fact_resp.content.decode("utf-8"),
            }

    async def get_xml_internal_invoice_by_id(self, id: str) -> Dict[Any, Any]:
        url = self.url_base.format(
            endpoint=FacturamaEndpoints.GET_XML_INTERNAL_INVOICE.value.format(id=id)
        )
        fact_resp = requests.get(url=url, headers=self.headers)
        if fact_resp.status_code == 200:
            xmldata = json.loads(fact_resp.content)
            xml_file = base64.b64decode(xmldata["Content"])
            return {
                "status": "ok",
                "status_code": fact_resp.status_code,
                "data": xml_file,
            }
        else:
            logger.warning(fact_resp.content.decode("utf-8"))
            return {
                "status": "error",
                "status_code": fact_resp.status_code,
                "msg": fact_resp.content.decode("utf-8"),
            }

    async def get_pdf_internal_invoice_by_id(self, id: str) -> Dict[Any, Any]:
        url = self.url_base.format(
            endpoint=FacturamaEndpoints.GET_PDF_INTERNAL_INVOICE.value.format(id=id)
        )
        fact_resp = requests.get(url=url, headers=self.headers)
        if fact_resp.status_code == 200:
            xmldata = json.loads(fact_resp.content)
            xml_file = base64.b64decode(xmldata["Content"])
            return {
                "status": "ok",
                "status_code": fact_resp.status_code,
                "data": xml_file,
            }
        else:
            logger.warning(fact_resp.content.decode("utf-8"))
            return {
                "status": "error",
                "status_code": fact_resp.status_code,
                "msg": fact_resp.content.decode("utf-8"),
            }

    async def get_3rd_party_xml_invoice_by_id(self, id: str) -> Dict[Any, Any]:
        url = self.url_base.format(
            endpoint=FacturamaEndpoints.GET_3RD_PARTY_XML_INVOICE.value.format(id=id)
        )
        fact_resp = requests.get(url=url, headers=self.headers)

        if fact_resp.status_code == 200:
            xmldata = json.loads(fact_resp.content)
            xml_file = base64.b64decode(xmldata["Content"])
            return {
                "status": "ok",
                "status_code": fact_resp.status_code,
                "data": xml_file,
            }
        else:
            logger.warning(fact_resp.content.decode("utf-8"))
            return {
                "status": "error",
                "status_code": fact_resp.status_code,
                "msg": fact_resp.content.decode("utf-8"),
            }

    async def get_3rd_party_pdf_invoice_by_id(self, id: str) -> Dict[Any, Any]:
        url = self.url_base.format(
            endpoint=FacturamaEndpoints.GET_3RD_PARTY_PDF_INVOICE.value.format(id=id)
        )
        fact_resp = requests.get(url=url, headers=self.headers)
        if fact_resp.status_code == 200:
            pdfdata = json.loads(fact_resp.content)
            pdf_file = base64.b64decode(pdfdata["Content"])
            return {
                "status": "ok",
                "status_code": fact_resp.status_code,
                "data": pdf_file,
            }
        else:
            return {
                "status": "error",
                "status_code": fact_resp.status_code,
                "msg": fact_resp.content.decode("utf-8"),
            }

    def get_3rd_party_invoice(self):
        pass

    def get_internal_invoice(self, id: str) -> Dict[Any, Any]:
        url = self.url_base.format(
            endpoint=FacturamaEndpoints.GET_3RD_PARTY_CFDI_JSON.value.format(id=id)
        )
        fact_resp = requests.get(url=url, headers=self.headers)
        if fact_resp.status_code == 200:
            _resp = fact_resp.content.decode("utf-8")
            if _resp != "null":
                data = fact_resp.json()
                return {
                    "status": "ok",
                    "status_code": fact_resp.status_code,
                    "data": data,
                }
            else:
                return {
                    "status": "error",
                    "status_code": fact_resp.status_code,
                    "msg": "invoice doesn't found",
                }
        else:
            logger.warning(fact_resp.content.decode("utf-8"))
            return {
                "status": "error",
                "status_code": fact_resp.status_code,
                "msg": fact_resp.content.decode("utf-8"),
            }

    async def cancel_3rd_party_pdf_invoice_by_id(
        self, id: str, motive: str, uuid_replacement: Optional[str] = None
    ) -> Dict[Any, Any]:
        url = self.url_base.format(
            endpoint=FacturamaEndpoints.CANCEL_3RD_PARTY_INVOICE.value.format(
                id=id, motive=motive
            )
        )
        if uuid_replacement:
            url += "&uuidReplacement=" + uuid_replacement
        fact_resp = requests.delete(url=url, headers=self.headers)

        if fact_resp.status_code == 200:
            _resp = fact_resp.content.decode("utf-8")

            if _resp != "null":
                return {
                    "status": "ok",
                    "status_code": fact_resp.status_code,
                    "data": fact_resp.json(),
                }
            else:
                return {
                    "status": "error",
                    "status_code": fact_resp.status_code,
                    "msg": "invoice doesn't found",
                }
        else:
            logger.warning(fact_resp.content.decode("utf-8"))
            return {
                "status": "error",
                "status_code": fact_resp.status_code,
                "msg": fact_resp.content.decode("utf-8"),
            }

    async def new_internal_invoice_complement(
        self, invoice_complement: FacturamaInternalInvoiceComplement
    ) -> Dict[Any, Any]:
        url = self.url_base.format(endpoint=FacturamaEndpoints.POST_INTERNAL_CFDI.value)
        data = domain_to_dict(invoice_complement)
        data["Receiver"] = domain_to_dict(
            invoice_complement.Receiver,
            skip=["Email", "Id", "TaxResidence", "NumRegIdTrib", "Address"],
        )
        data["Complemento"].Payments[0].RelatedDocuments = [
            domain_to_dict(data["Complemento"].Payments[0].RelatedDocuments[0])
        ]
        data["Complemento"].Payments = [domain_to_dict(data["Complemento"].Payments[0])]
        data["Complemento"] = domain_to_dict(data["Complemento"])
        fact_resp = requests.post(url=url, headers=self.headers, json=data)
        if fact_resp.status_code == 201:
            _rmp = fact_resp.json()
            _rmp["Result"] = json.dumps(_rmp)
            _rmp["Date"] = datetime.strptime(_rmp["Date"], "%Y-%m-%dT%H:%M:%S")
            _rmp["Receiver"] = Customer(**_rmp["Receiver"])
            _rmp["Issuer"] = InternalIssuer(**_rmp["Issuer"])
            resp_taxes_list = []
            for taxes in _rmp["Taxes"]:
                resp_taxes_list.append(SatTaxes(**taxes))
            _rmp["Taxes"] = resp_taxes_list
            resp_items_list = []
            for item in _rmp["Items"]:
                resp_taxes_list.append(Item(**item))
            _rmp["Items"] = resp_items_list
            _rmp["Complement"]["TaxStamp"] = TaxStamp(**_rmp["Complement"]["TaxStamp"])
            _rmp["Complement"] = Complement(**_rmp["Complement"])
            invoice_resp = NewInternalInvoiceResponse(**_rmp)
            return {
                "status": "ok",
                "status_code": fact_resp.status_code,
                "data": invoice_resp,
            }
        else:
            logger.warning(fact_resp.content.decode("utf-8"))
            return {
                "status": "error",
                "status_code": fact_resp.status_code,
                "msg": fact_resp.content.decode("utf-8"),
            }

    async def new_3rd_party_invoice_complement(
        self, invoice_complement: FacturamaInvoiceComplement
    ) -> Dict[Any, Any]:
        url = self.url_base.format(endpoint=FacturamaEndpoints.POST_CFDI.value)
        data = domain_to_dict(invoice_complement)
        data["Receiver"] = domain_to_dict(
            invoice_complement.Receiver,
            skip=["Email", "Id", "TaxResidence", "NumRegIdTrib", "Address"],
        )
        data["Issuer"] = domain_to_dict(invoice_complement.Issuer)
        data["Complemento"].Payments[0].RelatedDocuments = [
            domain_to_dict(RelatedDocumentsToInvoice)
            for RelatedDocumentsToInvoice in data["Complemento"]
            .Payments[0]
            .RelatedDocuments
        ]
        data["Complemento"].Payments = [domain_to_dict(data["Complemento"].Payments[0])]
        data["Complemento"] = domain_to_dict(data["Complemento"])
        fact_resp = requests.post(url=url, headers=self.headers, json=data)
        if fact_resp.status_code == 201:
            _rmp = fact_resp.json()
            _rmp["Result"] = json.dumps(_rmp)
            _rmp["Date"] = datetime.strptime(_rmp["Date"], "%Y-%m-%dT%H:%M:%S")
            _rmp["Receiver"] = Customer(**_rmp["Receiver"])
            _rmp["Issuer"] = Issuer(**_rmp["Issuer"])
            resp_taxes_list = []
            for taxes in _rmp["Taxes"]:
                resp_taxes_list.append(SatTaxes(**taxes))
            _rmp["Taxes"] = resp_taxes_list
            resp_items_list = []
            for item in _rmp["Items"]:
                resp_taxes_list.append(Item(**item))
            _rmp["Items"] = resp_items_list
            _rmp["Complement"]["TaxStamp"] = TaxStamp(**_rmp["Complement"]["TaxStamp"])
            _rmp["Complement"] = Complement(**_rmp["Complement"])
            invoice_resp = NewInvoiceResponse(**_rmp)
            return {
                "status": "ok",
                "status_code": fact_resp.status_code,
                "data": invoice_resp,
            }
        else:
            logger.warning(fact_resp.content.decode("utf-8"))
            return {
                "status": "error",
                "status_code": fact_resp.status_code,
                "msg": fact_resp.content.decode("utf-8"),
            }
