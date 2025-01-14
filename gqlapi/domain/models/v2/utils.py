from enum import Enum
from types import NoneType
from typing import Union
import strawberry


class T:
    """Generic placeholder data type"""

    def __init__(self, *args) -> None:  # noqa: F841 F401 F403
        pass


@strawberry.enum
class OrdenType(Enum):
    NORMAL = "normal"
    DRAFT = "draft"
    REPLACEMENT = "replacement"


@strawberry.enum
class OrdenSourceType(Enum):
    AUTOMATION = "automation"
    MARKETPLACE = "marketplace"
    ECOMMERCE = "ecommerce"


@strawberry.enum
class OrdenStatusType(Enum):
    SUBMITTED = 0
    ACCEPTED = 1
    PICKING = 2
    SHIPPING = 3
    ARRIVED = 4
    DELIVERED = 5
    CANCELED = 6


@strawberry.enum
class InvoiceType(Enum):
    PUE = "PUE"
    PPD = "PPD"


@strawberry.enum
class DeliveryStatusType(Enum):
    PENDING = 0
    ASSIGNED = 1
    ON_ROUTE = 2
    ARRIVED = 3
    DELIVERED = 4
    RE_SCHEDULED = 5
    CANCELED = 6


@strawberry.enum
class PayStatusType(Enum):
    PAID = 0
    UNPAID = 1
    UNKNOWN = 2
    PARTIALLY_PAID = 3


# @deprecated
@strawberry.enum
class DeliveryRegion(Enum):
    CDMX_CENTRO = "cdmx_centro"
    CDMX_SUR = "cdmx_sur"
    CDMX_NORTE = "cdmx_norte"
    CDMX_ORIENTE = "cdmx_oriente"
    CDMX_PONIENTE = "cdmx_poniente"
    CDMX_INTERLOMAS__SANTA_FE = "cdmx_interlomas__santa_fe"


@strawberry.enum
class PayMethodType(Enum):
    CASH = "cash"
    TRANSFER = "transfer"
    CARD = "card"
    CREDIT = "credit"
    MONEY_ORDER = "money_order"
    TBD = "to_be_determined"


@strawberry.enum
class ExecutionStatusType(Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@strawberry.enum
class PayProviderType(Enum):
    CARD_STRIPE = "stripe"
    TRANSFER_BBVA = "spei_bbva"
    TRANSFER_STRIPE = "spei_stripe"


@strawberry.enum
class InvoiceTriggerTime(Enum):
    AT_PURCHASE = "at_purchase"
    AT_DAY_CLOSE = "at_day_close"
    AT_DELIVERY = "at_delivery"
    DEACTIVATED = "deactivated"


@strawberry.enum
class InvoiceConsolidation(Enum):
    ONE_PER_PURCHASE = "one per purchase"
    ONE_PER_WEEK = "one per week"
    ONE_PER_MOUTH = "one per month"


@strawberry.enum
class SellingOption(Enum):
    SCHEDULED_DELIVERY = "scheduled_delivery"
    NEXT_DAY_DELIVERY = "nextday_delivery"
    SAME_DAY_DELIVERY = "sameday_delivery"
    PICKUP = "pickup"


@strawberry.enum
class InvoiceStatusType(Enum):
    ACTIVE = 1
    CANCELED = 0


@strawberry.enum
class UOMType(Enum):
    KG = "kg"
    UNIT = "unit"
    DOME = "dome"
    LITER = "liter"
    PACK = "pack"
    DOZEN = "dozens"


@strawberry.enum
class OrderSize(Enum):
    PRODUCTS = "products"
    KG = "Kg"
    PESOS = "$"


@strawberry.enum
class CategoryType(Enum):
    PRODUCT = "product"
    SUPPLIER = "supplier"
    RESTAURANT = "restaurant"


@strawberry.enum
class AlimaCustomerType(Enum):
    DEMAND = "demand"
    SUPPLY = "supply"
    LOGISTICS = "logistics"
    INTERNAL_USER = "internal"
    B2B_ECOMMERCE = "b2b_ecommerce"


@strawberry.enum
class ChargeType(Enum):
    SAAS_FEE = "saas"
    MARKETPLACE_COMMISSION = "marketplace_commission"
    FINANCE_FEE = "finance"
    REPORTS = "reports"
    INVOICE_FOLIO = "invoice_folio"
    ECOMMERCE = "ecommerce"
    PAYMENTS = "payments"


@strawberry.enum
class DiscountChargeType(Enum):
    SAAS_TEMPORAL = "saas_temporal"
    SAAS_YEARLY = "saas_yearly"
    FINANCE_TEMPORAL = "finance_temporal"
    ECOMMERCE_TEMPORAL = "ecommerce_temporal"


@strawberry.enum
class DriverStatusType(Enum):
    CONNECTED = "connected"
    ON_ROUTE = "on_route"
    DISCONNECTED = "disconnected"


@strawberry.enum
class NotificationChannelType(Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"


@strawberry.enum
class BusinessType(Enum):
    PHYSICAL_PERSON = "physical_person"
    SAS = "SAS"
    MORAL_PERSON = "moral_person"


@strawberry.enum
class RestaurantBusinessType(Enum):
    RESTAURANT = "restaurant"
    HOTEL = "hotel"
    CAFE = "cafe"
    SCHOOL = "school"
    BAR = "bar"
    DINNER = "dinner"
    CATERING = "catering"
    DARK_KITCHEN = "dark_kitchen"


@strawberry.enum
class SupplierBusinessType(Enum):
    PRODUCER = "producer"
    DISTRIBUTOR = "distributor"
    CPG = "cpg"
    PRODUCER_DISTRIBUTOR = "producer_distributor"


@strawberry.enum
class CurrencyType(Enum):
    MXN = "MXN"  # mexican peso
    COP = "COP"  # colombian peso
    USD = "USD"  # USA dollar
    CLP = "CLP"  # chilean peso
    BRL = "BRL"  # brazilian real
    PEN = "PEN"  # peruvian sol
    ARS = "ARS"  # argentinian peso


@strawberry.enum
class SupplierRestaurantStatusType(Enum):
    PROSPECT = 0
    LEAD = 1
    IN_REVIEW = 2
    APPROVED = 3
    CUSTOMER = 4


@strawberry.enum
class AlimaCustomerStatusType(Enum):
    PROSPECT = 0
    LEAD = 1
    IN_REVIEW = 2
    APPROVED = 3
    CUSTOMER = 4


@strawberry.enum
class CFDIUse(Enum):
    # Régimen 626: Simplificado de Confianza
    G01 = 0
    G02 = 1
    G03 = 2
    I01 = 3
    I02 = 4
    I03 = 5
    I04 = 6
    I05 = 7
    I06 = 8
    I07 = 9
    I08 = 10
    # Régimen 605: Sueldos y salarios e ingresos asimilados a salarios
    D01 = 11
    D02 = 12
    D03 = 13
    D04 = 14
    D05 = 15
    D06 = 16
    D07 = 17
    D08 = 18
    D09 = 19
    D10 = 20
    S01 = 21
    CP01 = 22
    CN01 = 23


class CFDIType(Enum):
    INGRESO = "I"
    EGRESO = "E"
    PAGO = "P"


@strawberry.enum
class RegimenSat(Enum):
    REG_601 = 601
    REG_603 = 603
    REG_605 = 605
    REG_606 = 606
    REG_607 = 607
    REG_608 = 608
    REG_610 = 610
    REG_612 = 612
    REG_614 = 614
    REG_615 = 615
    REG_616 = 616
    REG_620 = 620
    REG_621 = 621
    REG_622 = 622
    REG_623 = 623
    REG_624 = 624
    REG_625 = 625
    REG_626 = 626


@strawberry.enum
class VehicleType(Enum):
    SEDAN = "sedan"
    VAN = "van"
    PICKUP = "pickup"
    TRUCK = "truck"


@strawberry.type
class ServiceDay:
    dow: int  # 0 - 6 (monday - sunday)
    start: int  # 0 - 22 (0:00 - 22:00)
    end: int  # 1 - 23 (0:00 - 23:00)


@strawberry.type
class DeliveryTimeWindow:
    start: int
    end: int

    def __init__(self, start: int, end: int) -> None:
        if end < start:
            raise Exception("Unvalid delivery time window: Start must be before end")
        self.start = start
        self.end = end

    @property
    def size(self) -> int:
        """Delivery Time Window size in hours

        Returns
        -------
        int
            Duration (hrs)
        """
        return self.end - self.start

    def __str__(self) -> str:
        return f"{self.start} - {self.end}"

    @staticmethod
    def parse(value: str) -> "DeliveryTimeWindow":
        return DeliveryTimeWindow(*[int(v) for v in value.split(" - ")])


@strawberry.type
class Location:
    def __init__(
        self, name: str, lat: float = 0.0, lng: float = 0.0, full_address: str = ""
    ) -> None:
        if not any([lat and lng, full_address]):
            raise Exception("Missing Location params: (lat,lng) or (full_address)")
        self.name = name
        self.lat = lat
        self.lng = lng
        self.full_address = full_address


class DataTypeTraslate:
    @staticmethod
    def get_uomtype_decode(uom: str, lang: str = "es") -> Union[str, NoneType]:
        """Traslate UOM type

        Parameters
        ----------
        uom : str
            uom from interface

        Returns
        -------
        str
            UOMType
        """
        oum_value = {
            "kg": "kg",
            "pieza": "unit",
            "docena": "dozens",
            "paquete": "pack",
            "litro": "liter",
            "domo": "dome",
        }.get(uom, None)
        UOMType(oum_value)  # value validation
        return oum_value

    @staticmethod
    def get_uomtype_encode(uom_type: str, lang: str = "es") -> str:
        """Traslate UOM type

        Parameters
        ----------
        uom_type : str
            uom type

        Returns
        -------
        str
            UOMType
        """
        UOMType(uom_type)  # value validation
        oum_value = {
            "kg": "kg",
            "unit": "pieza",
            "dozens": "docena",
            "pack": "paquete",
            "liter": "litro",
            "dome": "domo",
        }.get(uom_type, "")
        return oum_value

    @staticmethod
    def get_orden_status_encode(status: int) -> Union[str, NoneType]:
        """Get Orden Status key name

        Parameters
        ----------
        status : OrdenStatusType
            Orden Status

        Returns
        -------
        str
            Orden Status key
        """
        OrdenStatusType(status)  # value validation
        return {
            0: "Enviado",
            1: "Confirmado",
            2: "Empacado",
            3: "En Camino",
            4: "En Destino",
            5: "Entregado",
            6: "Cancelado",
        }.get(status, None)

    @staticmethod
    def get_pay_status_encode(status: int) -> Union[str, NoneType]:
        """Get Orden Pay Status key name

        Parameters
        ----------
        status : PayStatusType
            Orden Pay Status

        Returns
        -------
        str
            Orden Status key
        """
        PayStatusType(status)  # value validation
        return {
            0: "Pagado",
            1: "Sin Pagar",
            2: "Por Definir",
            3: "Parcialmente pagado",
        }.get(status, None)

    @staticmethod
    def get_pay_method_encode(pmethod: str) -> Union[str, NoneType]:
        """Get Pay Method key name

        Parameters
        ----------
        pmethod : PayMethodType
            Payment method

        Returns
        -------
        str
            Orden Status key
        """
        PayMethodType(pmethod)  # value validation
        return {
            "cash": "Efectivo",
            "card": "Tarjeta",
            "transfer": "Transferencia",
            "credit": "Crédito",
            "money_order": "Cheque",
            "to_be_determined": "Por Definir",
        }.get(pmethod, None)


class DataTypeDecoder:
    @staticmethod
    def get_orden_paystatus_key(status: int) -> Union[str, NoneType]:
        """Get Orden PayStatus key name

        Parameters
        ----------
        status : PayStatusType
            Orden PayStatus

        Returns
        -------
        str
            Orden PayStatus key
        """
        PayStatusType(status)  # value validation
        return {
            0: "paid",
            1: "unpaid",
            2: "unknown",
            3: "partially_paid",
        }.get(status, None)

    @staticmethod
    def get_orden_paystatus_value(status: str) -> Union[int, NoneType]:
        """Get Orden PayStatus value

        Parameters
        ----------
        status : str
            Delivery PayStatus str

        Returns
        -------
        str
            Delivery PayStatus value
        """
        paystatus_value = {
            "paid": 0,
            "unpaid": 1,
            "unknown": 2,
            "partially_paid": 3,
        }.get(status, None)
        PayStatusType(paystatus_value)  # value validation
        return paystatus_value

    @staticmethod
    def get_orden_status_key(status: int) -> Union[str, NoneType]:
        """Get Orden Status key name

        Parameters
        ----------
        status : OrdenStatusType
            Orden Status

        Returns
        -------
        str
            Orden Status key
        """
        OrdenStatusType(status)  # value validation
        return {
            0: "submitted",
            1: "accepted",
            2: "picking",
            3: "shipping",
            4: "arrived",
            5: "delivered",
            6: "canceled",
        }.get(status, None)

    @staticmethod
    def get_orden_status_value(status: str) -> Union[int, NoneType]:
        """Get Orden Status value

        Parameters
        ----------
        status : str
            Delivery Status str

        Returns
        -------
        str
            Delivery Status value
        """
        status_value = {
            "submitted": 0,
            "accepted": 1,
            "picking": 2,
            "shipping": 3,
            "arrived": 4,
            "delivered": 5,
            "canceled": 6,
        }.get(status, None)
        OrdenStatusType(status_value)  # value validation
        return status_value

    @staticmethod
    def get_delivery_status_key(status: int) -> Union[str, NoneType]:
        """Get Delivery Status key name

        Parameters
        ----------
        status : DeliveryStatus.value
            Delivery Status

        Returns
        -------
        int
            Delivery Status key
        """
        DeliveryStatusType(status)  # value validation
        return {
            0: "pending",
            1: "assigned",
            2: "on_route",
            3: "arrived",
            4: "delivered",
            5: "re_scheduled",
            6: "canceled",
        }.get(status, None)

    @staticmethod
    def get_delivery_status_value(status: str) -> Union[int, NoneType]:
        """Get Delivery Status value

        Parameters
        ----------
        status : str
            Delivery Status str

        Returns
        -------
        int
            Delivery Status value
        """
        status_value = {
            "pending": 0,
            "assigned": 1,
            "on_route": 2,
            "arrived": 3,
            "delivered": 4,
            "re_scheduled": 5,
            "canceled": 6,
        }.get(status, None)
        DeliveryStatusType(status_value)  # value validation
        return status_value

    @staticmethod
    def get_supplier_restaurant_rel_status_key(status: int) -> Union[str, NoneType]:
        """Get Supplier-Restaurant Relation Status key name

        Parameters
        ----------
        status : SupplierRestaurantStatusType.value
            Supplier-Restaurant Relation Status

        Returns
        -------
        str
            Supplier-Restaurant Relation Status key
        """
        SupplierRestaurantStatusType(status)  # value validation
        return {
            0: "prospect",
            1: "lead",
            2: "in_review",
            3: "approved",
            4: "customer",
        }.get(status, None)

    @staticmethod
    def get_sat_regimen_status_key(status: int) -> Union[str, None]:
        """Get Alima-Customer Relation Status key name

        Parameters
        ----------
        status : RegimenSat.value
            Sat regimen code

        Returns
        -------
        str
            Sat regimen meaning
        """
        RegimenSat(status)  # value validation
        return {
            601: "General de Ley Personas Morales",
            603: "Personas Morales con Fines no Lucrativos",
            605: "Sueldos y salarios e ingresos asimilados a salarios",
            606: "Régimen de Arrendamiento",
            607: "Enajenación de bienes",
            608: "Demás ingresos",
            610: "Residentes en el Extranjero sin Establecimiento Permanente en México",
            612: "Régimen de Actividades Empresariales y Profesionales",
            614: "Intereses",
            615: "Obtención de premio",
            616: "Sin obligaciones fiscales",
            620: "Sociedades Cooperativas de Producción que optan por diferir sus ingresos",
            621: "Régimen de Incorporación Fiscal",
            622: "Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras",
            623: "Opcional para Grupos de Sociedades",
            624: "Coordinados",
            625: "Régimen de Actividades Empresariales con ingresos a través de Plataformas Tecnológicas",
            626: "Régimen Simplificado de Confianza",
        }.get(status, None)

    @staticmethod
    def get_sat_regimen_status_value(status: str) -> Union[int, None]:
        """Get Alima-Customer Relation Status value name

        Parameters
        ----------
        status : RegimenSat.string

        Returns
        -------
        int
            Sat regimen value
        """

        status_value = {
            "General de Ley Personas Morales": 601,
            "Personas Morales con Fines no Lucrativos": 603,
            "Sueldos y salarios e ingresos asimilados a salarios": 605,
            "Régimen de Arrendamiento": 606,
            "Enajenación de bienes": 607,
            "Demás ingresos": 608,
            "Residentes en el Extranjero sin Establecimiento Permanente en México": 610,
            "Régimen de Actividades Empresariales y Profesionales": 612,
            "Intereses": 614,
            "Obtención de premio": 615,
            "Sin obligaciones fiscales": 616,
            "Sociedades Cooperativas de Producción que optan por diferir sus ingresos": 620,
            "Régimen de Incorporación Fiscal": 621,
            "Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras": 622,
            "Opcional para Grupos de Sociedades": 623,
            "Coordinados": 624,
            "Régimen de Actividades Empresariales con ingresos a través de Plataformas Tecnológicas": 625,
            "Régimen Simplificado de Confianza": 626,
        }.get(status, None)
        RegimenSat(status_value)  # value validation
        return status_value

    @staticmethod
    def get_cfdi_use_status_key(status: int) -> Union[str, None]:
        """Get Alima-Customer Relation Status key name

        Parameters
        ----------
        status : CFDIUse.value
           CFDIUse 4.0

        Returns
        -------
        str
            CFDIUser Relation Status key
        """
        CFDIUse(status)  # value validation
        return {
            0: "Adquisición de mercancías",
            1: "Devoluciones, descuentos o bonificaciones",
            2: "Gastos en general",
            3: "Construcciones",
            4: "Mobilario y equipo de oficina por inversiones",
            5: "Equipo de transporte",
            6: "Equipo de computo y accesorios",
            7: "Dados, troqueles, moldes, matrices y herramental",
            8: "Comunicaciones telefónicas",
            9: "Comunicaciones satelitales",
            10: "Otra maquinaria y equipo",
            11: "Honorarios médicos, dentales y gastos hospitalarios.",
            12: "Gastos médicos por incapacidad o discapacidad",
            13: "Gastos funerales.",
            14: "Donativos.",
            15: "Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación).",
            16: "Aportaciones voluntarias al SAR.",
            17: "Primas por seguros de gastos médicos.",
            18: "Gastos de transportación escolar obligatoria.",
            19: "Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones.",
            20: "Pagos por servicios educativos (colegiaturas)",
            21: "Sin efectos fiscales.",
            22: "Pagos",
            23: "Nómina",
        }.get(status, None)

    @staticmethod
    def get_cfdi_use_status_value(value: str) -> Union[int, None]:
        """Get Alima-Customer Relation Status value name

        Parameters
        ----------
        status : CFDIUse.string

        Returns
        -------
        int
            CFDIUser Relation Status value
        """

        status_value = {
            "Adquisición de mercancías": 0,
            "Devoluciones, descuentos o bonificaciones": 1,
            "Gastos en general": 2,
            "Construcciones": 3,
            "Mobilario y equipo de oficina por inversiones": 4,
            "Equipo de transporte": 5,
            "Equipo de computo y accesorios": 6,
            "Dados, troqueles, moldes, matrices y herramental": 7,
            "Comunicaciones telefónicas": 8,
            "Comunicaciones satelitales": 9,
            "Otra maquinaria y equipo": 10,
            "Honorarios médicos, dentales y gastos hospitalarios.": 11,
            "Gastos médicos por incapacidad o discapacidad": 12,
            "Gastos funerales.": 13,
            "Donativos.": 14,
            "Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación).": 15,
            "Aportaciones voluntarias al SAR.": 16,
            "Primas por seguros de gastos médicos.": 17,
            "Gastos de transportación escolar obligatoria.": 18,
            "Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones.": 19,
            "Pagos por servicios educativos (colegiaturas)": 20,
            "Sin efectos fiscales.": 21,
            "Pagos": 22,
            "Nómina": 23,
        }.get(value, None)
        CFDIUse(status_value)
        return status_value

    @staticmethod
    def get_alima_customer_rel_status_key(status: int) -> Union[str, None]:
        """Get Alima-Customer Relation Status key name

        Parameters
        ----------
        status : AlimaCustomerStatusType.value
            Alima-Customer Relation Status

        Returns
        -------
        str
            Alima-Customer Relation Status key
        """
        AlimaCustomerStatusType(status)  # value validation
        return {
            0: "prospect",
            1: "lead",
            2: "in_review",
            3: "approved",
            4: "customer",
        }.get(status, None)

    @staticmethod
    def get_mxinvoice_status_key(status: int) -> Union[str, NoneType]:
        """Get Mx Invoice Status key name

        Parameters
        ----------
        status : InvoiceStatusType
            Invoice Status

        Returns
        -------
        str
            Invoice Status key
        """
        InvoiceStatusType(status)  # value validation
        return {
            0: "canceled",
            1: "active",
        }.get(status, None)

    @staticmethod
    def get_mxinvoice_status_value(status: str) -> Union[int, NoneType]:
        """Get Mx Invoice Status value name

        Parameters
        ----------
        status : InvoiceStatusType
            Invoice Status

        Returns
        -------
        str
            Invoice Status key
        """
        val = {
            "canceled": 0,
            "active": 1,
        }.get(status, None)
        InvoiceStatusType(val)  # value validation
        return val

    @staticmethod
    # type: ignore
    def get_uom_str(uom: str, lang: str = "es") -> Union[str, NoneType]:
        """Get Unit of Measure (UOM) string

        Parameters
        ----------
        uom : UOM.value
            _description_
        lang : str
            Language (es, en, etc.)

        Returns
        -------
        str
            Unit of measure text description
        """
        return (
            {
                "es": {"kg": "Kg", "unit": "Unidad(es)", "dome": "Domo"},
                "en": {"kg": "Kg", "unit": "Unit(s)", "dome": "Dome"},
            }
            .get(lang, {})
            .get(uom, None)
        )

    @staticmethod
    def get_sat_unit_code(uom_type: str) -> str:
        UOMType(uom_type)  # value validation
        oum_value = {
            "kg": "KGM",
            "unit": "H87",
            "dozens": "DPC",
            "pack": "XPK",
            "liter": "LTR",
            "dome": "H87",
        }.get(uom_type, "")
        return oum_value
