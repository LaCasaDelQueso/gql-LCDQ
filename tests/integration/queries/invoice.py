query_test_upload_invoice = """mutation uploadRestoInvoice(
    $pdf: Upload!,
    $xml: Upload!,
    $ordenId: UUID!) {
  uploadInvoice(ordenId: $ordenId, pdfFile: $pdf, xmlFile: $xml) {
    ... on MxInvoiceError {
      code
    }
    ... on MxUploadInvoiceMsg {
      msg
      success
    }
  }
}"""

query_test_get_external_invoice_details = """query getExternalInvoiceDetails($ordenId: UUID!) {
    getInvoiceExternalDetails(ordenId: $ordenId) {
      ... on MxUploadInvoice {
        ordenId
        ordenTotal
        ordenDeliveryDate
        restaurantBranch {
          branchName
        }
        uploadMsg {
          success
          msg
        }
      }
      ... on MxInvoiceError {
        code
      }
    }
  }"""

query_test_invoice_details = """query getInvoiceDetails($ordenId: UUID!) {
    getInvoiceDetails(ordenId: $ordenId) {
      ... on MxInvoiceGQL {
        invoiceNumber
        orden {
          ordenDetailsId
        }
        id
        satInvoiceUuid
        status
        total
        supplier {
          id
          name
        }
      }
      ... on MxInvoiceError {
        code
      }
    }
  }"""
