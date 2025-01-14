query_test_new_normal_orden = """mutation newOrdenNormal(
        $cartProds: [CartProductInput!]!,
        $deliveryDate: DateTime!,
        $deliveryTime: DeliveryTimeWindowInput!,
        $supBId: UUID!,
        $restaurantBranchId: UUID!,
        $comms: String) {
    newOrden(
      cartProducts: $cartProds
      ordenType: NORMAL
      restaurantBranchId: $restaurantBranchId
      deliveryDate: $deliveryDate
      deliveryTime: $deliveryTime
      paystatus: UNKNOWN
      status: SUBMITTED
      supplierBusinessId: $supBId
      paymentMethod: TBD
      comments: $comms
    ) {
      ... on OrdenGQL {
        id
        status {
          status
          id
        }
        details {
          version
          id
          cartId
          restaurantBranchId
        }
        paystatus {
          id
        }
        cart {
          cartId
        }
        supplier {
          supplierBusiness {
            name
            id
          }
      }
      }
      ... on OrdenError {
        code
        msg
      }
    }
  }"""

query_test_get_active_ordens_by_branch = """query getActiveOrdenesByBranch(
        $fromDate: Date!,
        $branchId: UUID!) {
    getOrdenes(fromDate: $fromDate, restaurantBranchId: $branchId) {
      ... on OrdenGQL {
        id
        cart {
          subtotal
          quantity
        }
        details {
          approvedBy
          ordenId
          version
          subtotal
          total
          paymentMethod
          deliveryDate
          createdAt
          deliveryTime {
            end
            start
          }
          createdBy
          restaurantBranchId
        }
        status {
          status
          createdAt
        }
        ordenType
        paystatus {
          status
          createdAt
        }
        supplier {
          supplierBusiness {
            name
          }
        }
      }
      ... on OrdenError {
        code
      }
    }
  }"""

query_test_get_orden_details = """query getOrdenDetails($ordenId: UUID!) {
    getOrdenes(
          ordenId: $ordenId
    ) {
      ... on OrdenGQL {
        id
        cart {
          unitPrice
          subtotal
          sellUnit
          quantity
          supplierProductPriceId
          suppProd {
            id
            sellUnit
            sku
            description
            minQuantity
            unitMultiple
            estimatedWeight
          }
        }
        details {
          cartId
          approvedBy
          ordenId
          version
          total
          tax
          subtotalWithoutTax
          subtotal
          shippingCost
          serviceFee
          paymentMethod
          packagingCost
          discount
          deliveryDate
          createdAt
          deliveryTime {
            end
            start
          }
          comments
          createdBy
          restaurantBranchId
        }
        status {
          status
          createdAt
        }
        ordenType
        paystatus {
          status
          createdAt
        }
        supplier {
          supplierBusinessAccount {
            supplierBusinessId
            legalRepName
            email
            phoneNumber
          }
          supplierBusiness {
            name
          }
        }
      }
      ... on OrdenError {
        code
      }
    }
  }"""

query_test_get_historic_orden_by_branch = """query getHistoricOrdenesByBranch(
    $fromDate: Date!,
    $toDate: Date!,
    $branchId: UUID!,
    $supBId: UUID) {
  getOrdenes(
    fromDate: $fromDate
    toDate: $toDate
    restaurantBranchId: $branchId
    supplierBusinessId: $supBId
  ) {
    ... on OrdenGQL {
      id
      cart {
        subtotal
        quantity
      }
      details {
        approvedBy
        ordenId
        version
        subtotal
        total
        paymentMethod
        deliveryDate
        createdAt
        deliveryTime {
          end
          start
        }
        createdBy
        restaurantBranchId
      }
      status {
        status
        createdAt
      }
      ordenType
      paystatus {
        status
        createdAt
      }
      supplier {
        supplierBusiness {
          name
          id
        }
      }
    }
    ... on OrdenError {
      code
      msg
    }
  }
}"""

query_test_edit_orden = """mutation updateOrden(
    $ordenId: UUID!,
    $cart: [CartProductInput!]!,
    $packaging: Float,
    $shipping: Float,
    $service: Float,
    $comments: String,
    $delivDate: Date) {
  updateOrden(
    ordenId: $ordenId
    cartProducts: $cart
    packagingCost: $packaging
    shippingCost: $shipping
    serviceFee: $service
    comments: $comments
    deliveryDate: $delivDate
  ) {
    ... on OrdenGQL {
      id
      status {
        status
      }
      details {
        version
      }
    }
    ... on OrdenError {
      code
      msg
    }
  }
}"""

query_test_cancel_orden = """mutation cancelOrden($ordenId: UUID!) {
  updateOrden(ordenId: $ordenId, status: CANCELED, ordenType: NORMAL) {
    ... on OrdenGQL {
      id
      status {
        status
        createdAt
      }
      ordenType
    }
    ... on OrdenError {
      code
      msg
    }
  }
}"""
