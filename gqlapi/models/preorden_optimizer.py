import logging
from types import NoneType
from typing import Any, Dict, List
from uuid import UUID
from gqlapi.domain.interfaces.v2.orden.cart import CartProductGQL

from gqlapi.domain.interfaces.v2.orden.orden import OrdenGQL, OrdenSupplierGQL
from gqlapi.domain.interfaces.v2.restaurant.restaurant_suppliers import (
    RestaurantSupplierCreationGQL,
    SupplierProductCreation,
)
from gqlapi.domain.models.v2.supplier import SupplierProduct
from gqlapi.domain.models.v2.utils import OrdenType, UOMType
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.utils.helpers import serialize_product_description


class PreOrdenOptimizer:
    def __init__(
        self, preordenes: List[OrdenGQL], suppliers: List[RestaurantSupplierCreationGQL]
    ):
        """PreOrden Optimizer
            - Optimize preordenes by assigning the best supplier to each product
            - Current version returns the best price for each product minimizing the total cost
            - Future versions will consider other factors such as:
                - Delivery time
                - Supplier rating
                - Supplier AOV

        Parameters
        ----------
        preordenes : List[OrdenGQL]
        suppliers : List[RestaurantSupplierCreationGQL]
        """
        self.preordenes = preordenes
        # validate suppliers
        _sups = [s for s in suppliers if s.products]
        if len(_sups) == 0:
            raise GQLApiException(
                msg="No supplier products found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        self.suppliers = _sups
        # algorithm vars
        self.supplier_prods_idx: Dict[str, List[SupplierProductCreation]] = {}
        self.reduced_prods: List[
            Dict[str, Any]
        ] = []  # Dict -> CartProductGQL.dict + idx_key
        # initialize idxs
        self._build_supplier_products_index()

    def _find_supplier(
        self, supplier_product: SupplierProduct
    ) -> RestaurantSupplierCreationGQL | NoneType:
        """Find supplier
        - Find supplier by supplier product
        """
        for s in self.suppliers:
            if s.supplier_business.id == supplier_product.supplier_business_id:  # type: ignore
                return s
        return None

    def _build_supplier_products_index(self):
        """Build supplier products index
        - Create a dictionary of supplier products indexed by
            serialized product description + sell_unit
        """
        for s in self.suppliers:
            if not s.products:
                continue
            for p in s.products:
                p_idx = serialize_product_description(
                    p.product.description,
                    UOMType(p.product.sell_unit)
                    if isinstance(p.product.sell_unit, str)
                    else p.product.sell_unit,
                )
                if p_idx in self.supplier_prods_idx:
                    self.supplier_prods_idx[p_idx].append(p)
                else:
                    self.supplier_prods_idx[p_idx] = [p]

    def _build_preordenes_products_idx(self) -> Dict[str, List[CartProductGQL]]:
        """Build preordenes products index
        - Create a dictionary of preordenes' products
            indexed by serialized product description + sell_unit
        """
        _prods_idx = {}
        for po in self.preordenes:
            if not po.cart:
                continue
            for cp in po.cart:
                if not cp.supp_prod:
                    continue
                p_idx = serialize_product_description(
                    cp.supp_prod.description,
                    UOMType(cp.supp_prod.sell_unit)
                    if isinstance(cp.supp_prod.sell_unit, str)
                    else cp.supp_prod.sell_unit,
                )
                if p_idx in _prods_idx:
                    _prods_idx[p_idx].append(cp)
                else:
                    _prods_idx[p_idx] = [cp]
        return _prods_idx

    def _reduce_sum_quantities(
        self, p_idxs: Dict[str, List[CartProductGQL]]
    ) -> List[Dict[str, Any]]:
        """Reduce sum quantities"""
        reduced_prods = []
        for p_idx, cps in p_idxs.items():
            prod = cps[0].__dict__
            prod["idx_key"] = p_idx
            for cp in cps[1:]:
                prod["quantity"] += cp.quantity
                prod["subtotal"] = prod["quantity"] * prod["unit_price"]
            reduced_prods.append(prod)
        return reduced_prods

    def _set_best_supplier_to_product(
        self, cprod: Dict[str, Any], assigned_supplier: SupplierProductCreation
    ) -> CartProductGQL:
        # build cart product
        d = cprod.copy()
        del d["idx_key"]
        d["supp_prod"] = assigned_supplier.product
        d["supplier_product_id"] = assigned_supplier.product.id
        d["supplier_product_price_id"] = (
            assigned_supplier.price.id if assigned_supplier.price else None
        )
        d["unit_price"] = (
            assigned_supplier.price.price if assigned_supplier.price else None
        )
        d["subtotal"] = d["unit_price"] * d["quantity"] if d["unit_price"] else None
        return CartProductGQL(**d)

    def reduce_preordenes_products(self):
        """Reduce preordenes product
        -> CartProductGQL serialized + idx_key
        """
        # generate idx
        prods_idx = self._build_preordenes_products_idx()
        # reduce quantitie per idx
        self.reduced_prods = self._reduce_sum_quantities(prods_idx)

    def assign_supplier_to_product(
        self, cprods: List[Dict[str, Any]]
    ) -> List[CartProductGQL]:
        """Assign best supplier to product"""
        supplier_cart_products: List[CartProductGQL] = []
        # build supplier indexes with all assigned products
        for c in cprods:
            # sort suppliers by price in ascending order
            _supps = sorted(
                self.supplier_prods_idx.get(c["idx_key"], []),
                key=lambda x: x.price.price if x.price else float("inf"),
                reverse=False,
            )
            # if not supplier found with such product keep it as Alima Supplier
            if not _supps:
                d = c.copy()
                del d["idx_key"]
                supplier_cart_products.append(CartProductGQL(**d))
                continue
            # get the best supplier
            _best = _supps[0]  # criteria: supplier with best price
            cart_prod_w_best = self._set_best_supplier_to_product(c, _best)
            supplier_cart_products.append(cart_prod_w_best)
        # return product
        return supplier_cart_products

    def build_temp_ordenes(
        self, supplier_cart_products: List[CartProductGQL], template_orden: OrdenGQL
    ) -> List[OrdenGQL]:
        """Build temp ordenes"""
        # group by suppliers
        grouped_suppliers: Dict[UUID, List[CartProductGQL]] = {}
        for cp in supplier_cart_products:
            if not cp.supp_prod:
                logging.warning("No supplier product found for cart product: %s", cp)
                continue
            if cp.supp_prod.supplier_business_id in grouped_suppliers:
                grouped_suppliers[cp.supp_prod.supplier_business_id].append(cp)
            else:
                grouped_suppliers[cp.supp_prod.supplier_business_id] = [cp]
        # build temp ordenes
        tmp_ordenes = []
        # build temp ordenes
        for cart_prods in grouped_suppliers.values():
            # build temp orden
            tmp_orden = OrdenGQL(**template_orden.__dict__)  # deep copy
            tmp_orden.orden_type = OrdenType.NORMAL
            # add cart products
            tmp_orden.cart = cart_prods
            # compute total
            _total = sum([cp.subtotal for cp in cart_prods if cp.subtotal])
            tmp_orden.details.subtotal = _total  # type: ignore
            tmp_orden.details.total = _total  # type: ignore
            # add supplier
            _supplier = self._find_supplier(cart_prods[0].supp_prod)  # type: ignore
            if (
                not _supplier
                or not _supplier.supplier_business
                or not _supplier.supplier_business_account
            ):
                logging.warning("No supplier found for cart product: %s", cart_prods[0])
                raise GQLApiException(
                    msg="No supplier found for cart product",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            tmp_orden.supplier = OrdenSupplierGQL(
                supplier_business=_supplier.supplier_business,
                supplier_business_account=_supplier.supplier_business_account,
            )
            # add temp orden to list
            tmp_ordenes.append(tmp_orden)
        # return temp ordenes
        return tmp_ordenes

    def optimize(self) -> List[OrdenGQL]:
        """Optimize PreOrdenes
        - Yield the most suitable combination of preordenes and suppliers
        """
        # reduce all products from all preordenes by key idx
        self.reduce_preordenes_products()
        # Assign each product to the best supplier
        best_suppliers = self.assign_supplier_to_product(self.reduced_prods)
        # build temp ordenes with the best supplier
        tmp_ordenes = self.build_temp_ordenes(best_suppliers, self.preordenes[0])
        # return optimized preordenes
        return tmp_ordenes
