import strawberry

from gqlapi.endpoints import (
    AlimaMutation,
    AlimaQuery,
    CoreMutation,
    CoreQuery,
    RestaurantMutation,
    RestaurantQuery,
    ServicesMutation,
    ServicesQuery,
    SupplierMutation,
    SupplierQuery,
)


@strawberry.type
class Query(CoreQuery, RestaurantQuery, SupplierQuery, AlimaQuery, ServicesQuery):
    pass


@strawberry.type
class Mutation(
    CoreMutation, RestaurantMutation, SupplierMutation, AlimaMutation, ServicesMutation
):
    pass


# --------------
# Schema
# --------------

schema = strawberry.Schema(query=Query, mutation=Mutation)
