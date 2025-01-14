import datetime
from typing import Any, Dict
from uuid import UUID
import json

from gqlapi.scripts.personalized.supplier.load_orden_payment_to_stripe import (
    new_orden_la_casa_del_queso,
)
from gqlapi.scripts.services.get_error_mails_of_sendgrid import (
    send_mail_of_error_when_sending_emails_from_sendgrid,
)
from starlette.background import BackgroundTasks
from starlette.endpoints import HTTPEndpoint
from starlette.responses import JSONResponse
from starlette.requests import Request

from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.repository.scripts.scripts_execution import ScriptExecutionRepository
from gqlapi.scripts.personalized.supplier.send_consolidated_to_provider import (
    send_supplier_consolidated_to_provider,
)
from gqlapi.scripts.automation.run_daily_3rd_party_invoices import (
    run_daily_3rd_party_invoices,
)
from gqlapi.scripts.billing.create_daily_alima_invoice_v2 import (
    send_create_supplier_billing_invoice_v2,
)
from gqlapi.scripts.billing.create_daily_alima_invoice_v3 import (
    send_create_supplier_billing_invoices_v3,
)
from gqlapi.scripts.billing.send_reminder_alima_billing import (
    send_reminders as send_billing_reminders,
)
from gqlapi.scripts.monitor.invoice_execution import invoice_monitor
from gqlapi.scripts.monitor.script_execution import scripts_monitor

from gqlapi.scripts.orden.convert_orden_confirm import confirm_orden_status
from gqlapi.scripts.product.expiration_list_warning import (
    send_warning as send_expiration_list_warning,
)
# from gqlapi.scripts.core.upsert_algolia_index import run_upsert_algolia_index
from gqlapi.scripts.tests.get_scorpion_orden_status import update_orden_scorpion
from gqlapi.scripts.tests.new_orden_scorpion import new_orden_scorpion
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.db import database as SQLDatabase
from gqlapi.mongo import mongo_db as MongoDatabase

logger = get_logger(get_app())

scripts_map = {
    # Automation
    "confirm_orden_status": confirm_orden_status,
    "send_billing_alima_reminder": send_billing_reminders,
    "expiration_supplier_product_list_warning": send_expiration_list_warning,
    # Daily executions
    "run_daily_3rd_party_invoices": run_daily_3rd_party_invoices,
    "run_daily_alima_invoices_v2": send_create_supplier_billing_invoice_v2,
    "run_daily_alima_invoices_v3": send_create_supplier_billing_invoices_v3,
    # "run_daily_algolia_index": run_upsert_algolia_index,
    # Monitors
    "invoice_monitor": invoice_monitor,
    "script_monitor": scripts_monitor,
    # 3rd party integrations
    "run_scorpion_status_check": update_orden_scorpion,
    "new_orden_scorpion": new_orden_scorpion,
    # supplier personalization
    "send_bruma_consolidated_to_provider": send_supplier_consolidated_to_provider,
    "new_orden_la_casa_del_queso": new_orden_la_casa_del_queso,
    "send_report_of_error_mails": send_mail_of_error_when_sending_emails_from_sendgrid,
}


class RetoolWorkflowJob(HTTPEndpoint):
    """[summary]

    Parameters
    ----------
    request : starlette.requests.Request

    Returns
    -------
    starlette.responses.JSONResponse
    """

    async def post(self, request: Request) -> JSONResponse:
        """Post method to execute a script as a background task

            - Get Id
            - Get script_name
            - Get script_args
            - Create record in DB
            - Execute script as background task
            - Update record in DB with result
            - Return response

        Args:
            request (Request)

        Raises:
            Exception

        Returns:
            JSONResponse
        """
        try:
            resp = await request.body()
            resp_decode = resp.decode("utf-8").replace("'", '"')
            request_args = json.loads(resp_decode)
            # 1. Create registro en DB de inicio de script
            script_exec_rep = ScriptExecutionRepository(SQLDatabase)
            validate_data(request_args)
            e_id = await script_exec_rep.add(
                script_name=request_args["script_name"], status="running"
            )
            if not e_id:
                raise Exception("Error al crear registro en DB")
            tasks = BackgroundTasks()
            tasks.add_task(
                script_execution_wrapper,
                exec_id=e_id,
                repo=script_exec_rep,
                request_args=request_args,
            )
            return JSONResponse({"status": "ok", "id": str(e_id)}, background=tasks)
        except Exception as e:
            logger.error(e)
            return JSONResponse({"status": "error", "error": str(e)})


async def script_execution_wrapper(
    exec_id: UUID, repo: ScriptExecutionRepository, request_args: Dict[Any, Any]
):
    # 3. Dentro del Background task: ejecutar script as a background task
    # 4. Dentro del Background task: Actualizar registro en DB con resultado de script
    try:
        _info = InjectedStrawberryInfo(
            db=SQLDatabase,
            mongo=MongoDatabase,
        )
        if "args" not in request_args:
            result_data = await scripts_map[request_args["script_name"]](_info)
        else:
            result_data = await scripts_map[request_args["script_name"]](
                _info, **request_args["args"]
            )
        result = {"status": "ok", "data": result_data}
    except Exception as e:
        logger.warning(f"Error en script_execution_wrapper: {exec_id}")
        logger.error(e)
        result = {"status": "error", "error": str(e)}
    try:
        # [TODO] validate if result ok
        await repo.edit(
            id=exec_id,
            status="finished" if result["status"] == "ok" else "error",
            script_end=datetime.datetime.utcnow(),
            data=json.dumps(result),
        )
    except Exception as e:
        logger.warning(f"Error al actualizar registro en DB: {exec_id}")
        logger.error(e)


def validate_data(request: Dict[Any, Any]):
    if "script_name" not in request:
        raise Exception("Param script_name not in request")
