from gqlapi.endpoints.alima_account.account import (
    AlimaAccountMutation,
    AlimaAccountQuery,
)
from gqlapi.endpoints.alima_account.billing import (
    AlimaBillingMutation,
    AlimaBillingQuery,
)
from gqlapi.endpoints.b2bcommerce.ecommerce_user import (
    B2BEcommerceSellerMutation,
    B2BEcommerceSellerQuery,
    B2BEcommerceUserMutation,
    B2BEcommerceUserQuery,
)
from gqlapi.endpoints.core.category import CategoryMutation, CategoryQuery
from gqlapi.endpoints.core.invoice import MxInvoiceMutation, MxInvoiceQuery
from gqlapi.endpoints.core.orden import OrdenQuery, OrdenMutation
from gqlapi.endpoints.core.product import (
    ProductFamilyMutation,
    ProductFamilyQuery,
    ProductMutation,
    ProductQuery,
)
from gqlapi.endpoints.restaurant.restaurant_branch import (
    RestaurantBranchMutation,
    RestaurantBranchQuery,
)
from gqlapi.endpoints.restaurant.restaurant_suppliers import (
    RestaurantSuppliersMutation,
    RestaurantSuppliersQuery,
)
from gqlapi.endpoints.services.authos import (
    AuthosEcommercePwdRestoreMutation,
    AuthosEcommerceSessionQuery,
    AuthosEcommerceUserMutation,
    AuthosEcommerceUserQuery,
)
from gqlapi.endpoints.services.image import ImageMutation, ImageQuery
from gqlapi.endpoints.supplier.supplier_business import (
    SupplierBusinessMutation,
    SupplierBusinessQuery,
)
from gqlapi.endpoints.restaurant.restaurant_user import (
    RestaurantEmployeeMutation,
    RestaurantUserMutation,
    RestaurantUserPermissionQuery,
    RestaurantUserQuery,
)
from gqlapi.endpoints.restaurant.restaurant_business import (
    RestaurantBusinessMutation,
    RestaurantBusinessQuery,
)
from gqlapi.endpoints.supplier.supplier_invoice import (
    SupplierInvoiceMutation,
    SupplierInvoiceQuery,
)
from gqlapi.endpoints.supplier.supplier_price_list import (
    SupplierPriceListMutation,
    SupplierPriceListQuery,
)
from gqlapi.endpoints.supplier.supplier_product import (
    SupplierProductMutation,
    SupplierProductQuery,
)
from gqlapi.endpoints.supplier.supplier_restaurants import (
    SupplierRestaurantsMutation,
    SupplierRestaurantsQuery,
)
from gqlapi.endpoints.supplier.supplier_unit import (
    SupplierUnitMutation,
    SupplierUnitQuery,
)
from gqlapi.endpoints.supplier.supplier_user import (
    SupplierEmployeeMutation,
    SupplierUserMutation,
    SupplierUserPermissionQuery,
    SupplierUserQuery,
)

# ------------------
# Core Schema
# ------------------


class CoreMutation(
    CategoryMutation,
    ProductFamilyMutation,
    ProductMutation,
    OrdenMutation,
    MxInvoiceMutation,
):
    pass


class CoreQuery(
    CategoryQuery,
    ProductFamilyQuery,
    ProductQuery,
    OrdenQuery,
    MxInvoiceQuery,
):
    pass


# ------------------
# Restaurant Schema
# ------------------


class RestaurantMutation(
    RestaurantUserMutation,
    RestaurantBusinessMutation,
    RestaurantBranchMutation,
    RestaurantEmployeeMutation,
    RestaurantSuppliersMutation,
):
    pass


class RestaurantQuery(
    RestaurantUserQuery,
    RestaurantUserPermissionQuery,
    RestaurantBusinessQuery,
    RestaurantBranchQuery,
    RestaurantSuppliersQuery,
):
    pass


# ------------------
# Supplier Schema
# ------------------


class SupplierMutation(
    SupplierUserMutation,
    SupplierEmployeeMutation,
    SupplierBusinessMutation,
    SupplierUnitMutation,
    SupplierProductMutation,
    SupplierPriceListMutation,
    SupplierRestaurantsMutation,
    SupplierInvoiceMutation,
):
    pass


class SupplierQuery(
    SupplierUserQuery,
    SupplierUserPermissionQuery,
    SupplierBusinessQuery,
    SupplierUnitQuery,
    SupplierProductQuery,
    SupplierPriceListQuery,
    SupplierRestaurantsQuery,
    SupplierInvoiceQuery,
):
    pass


# ------------------
# Alima Services Schema
# ------------------


class ServicesMutation(
    ImageMutation,
    AuthosEcommerceUserMutation,
    AuthosEcommercePwdRestoreMutation,
    B2BEcommerceUserMutation,
    B2BEcommerceSellerMutation,
):
    pass


class ServicesQuery(
    ImageQuery,
    AuthosEcommerceSessionQuery,
    AuthosEcommerceUserQuery,
    B2BEcommerceUserQuery,
    B2BEcommerceSellerQuery,
):
    pass


# ------------------
# Alima Account Schema
# ------------------


class AlimaQuery(AlimaAccountQuery, AlimaBillingQuery):
    pass


class AlimaMutation(AlimaAccountMutation, AlimaBillingMutation):
    pass
