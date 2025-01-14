from abc import ABC
import datetime
from enum import Enum
import json
import unicodedata
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from typing import Any, Dict, List, Literal, Optional

import requests
from strawberry import type as strawberry_type

from gqlapi.utils.domain_mapper import domain_to_dict

logger = get_logger(get_app())


@strawberry_type
class VercelGitRepository(ABC):
    repo: str
    type: Literal["github", "gitlab", "bitbucket"]


@strawberry_type
class VercelEnvironmentVariables(ABC):
    # gitBranch: Optional[str] = None
    key: str
    target: List[Literal["production", "development", "preview"]]
    type: Optional[Literal["system", "secret", "encrypted", "plain", "sensitive"]] = (
        None
    )
    value: str


@strawberry_type
class VercelResponse(ABC):
    status: str
    status_code: int
    msg: str
    result: Optional[str] = None
    value: Optional[str] = None


class VercelEndpoints(Enum):
    FIND_PROJECTS = "v9/projects/{idOrName}?teamId={teamId}"
    FIND_DOMAINS = "v9/projects/{idOrName}/domains"
    NEW_PROJECT = "v10/projects?teamId={teamId}"
    NEW_DOMAIN = "v10/projects/{idOrName}/domains?teamId={teamId}"
    RETRIVE_ENV_VARS = "v9/projects/{idOrName}/env"
    RETRIVE_DECRYPTED_ENV_VAR = "v1/projects/{idOrName}/env/{id}"
    NEW_DEPLOYMENT = "v13/deployments"


class VercelUtils:
    @staticmethod
    def build_project_name(name: str) -> str:
        normalized_string = unicodedata.normalize("NFKD", name)
        result_string = "".join(
            [char for char in normalized_string if not unicodedata.combining(char)]
        )
        return (
            (result_string.replace(" ", "-").lower() + "-commerce")
            .replace("_", "-")
            .replace(".", "")
        )

    @staticmethod
    def build_domain_name(name: str, subdomain_alima: str) -> str:
        normalized_string = unicodedata.normalize("NFKD", name)
        result_string = "".join(
            [char for char in normalized_string if not unicodedata.combining(char)]
        )
        return (
            result_string.replace(" ", "-")
            .lower()
            .replace(".", "")
            .replace(",", "")
            .replace("_", "-")
            + "."
            + subdomain_alima
        )


class VercelClientApi:
    def __init__(self, env: str, vercel_token: str, team_id: str) -> None:
        """_summary_

        Args:
            env (str): environment
            vercel_token (str): unique token for vercel
            team_id (str): team of vercel

        Raises:
            ValueError: _description_
        """
        if not vercel_token or not team_id or not env:
            raise ValueError("Vercel ENV VARS are not defined")
        self.team_id = team_id
        self.headers = {
            "Authorization": "Bearer " + vercel_token,
            "content-type": "application/json",
        }
        self.url_base = (
            "https://api.vercel.com/{endpoint}"
            if env.lower() == "prod"
            else "https://api.vercel.com/{endpoint}"
        )

    def find_project(self, project_name: str) -> VercelResponse:
        try:
            url = self.url_base.format(
                endpoint=VercelEndpoints.FIND_PROJECTS.value.format(
                    idOrName=project_name, teamId=self.team_id
                )
            )
            fact_resp = requests.get(url=url, headers=self.headers)
            if fact_resp.status_code == 200:
                return VercelResponse(
                    status="ok",
                    status_code=fact_resp.status_code,
                    result=json.dumps(fact_resp.json()),
                    msg="ok",
                )
            return VercelResponse(
                status="error",
                status_code=fact_resp.status_code,
                msg=fact_resp.content.decode("utf-8"),
            )
        except Exception as e:
            logger.error(f"VERCEL Error: {e}")
            return VercelResponse(
                status="error",
                status_code=500,
                msg=str(e),
            )

    def new_domain(
        self,
        project_name: str,
        domain_url: str,
        redirect: Optional[str] = None,
        redirect_status_code: Optional[int] = None,
    ) -> VercelResponse:
        try:
            url = self.url_base.format(
                endpoint=VercelEndpoints.NEW_DOMAIN.value.format(
                    idOrName=project_name, teamId=self.team_id
                )
            )
            data: Dict[Any, Any] = {
                "name": domain_url,
            }
            # if git_branch:
            #     data["gitBranch"] = git_branch
            if redirect:
                data["redirect"] = redirect
            if redirect_status_code:
                data["redirectStatusCode"] = redirect_status_code
            fact_resp = requests.post(url=url, headers=self.headers, json=data)
            if fact_resp.status_code == 200:
                return VercelResponse(
                    status="ok",
                    status_code=fact_resp.status_code,
                    value=fact_resp.json(),
                    msg="ok",
                )
            return VercelResponse(
                status="error",
                status_code=fact_resp.status_code,
                msg=fact_resp.content.decode("utf-8"),
            )
        except Exception as e:
            logger.error(f"VERCEL Error: {e}")
            return VercelResponse(
                status="error",
                status_code=500,
                msg=str(e),
            )

    def new_project(
        self,
        project_name: str,
        root_directory: str = "apps/commerce-template",
        framework: str = "nextjs",
        environment_variables: Optional[List[VercelEnvironmentVariables]] = None,
        build_command: Optional[str] = None,
        command_for_ignoring_build_step: Optional[str] = None,
        dev_command: Optional[str] = None,
        git_repository: Optional[VercelGitRepository] = None,
        install_command: Optional[str] = None,
        output_directory: Optional[str] = None,
        public_source: Optional[bool] = None,
        serverless_function_region: Optional[str] = None,
    ) -> VercelResponse:
        try:
            url = self.url_base.format(
                endpoint=VercelEndpoints.NEW_PROJECT.value.format(
                    idOrName=project_name, teamId=self.team_id
                )
            )
            data: Dict[Any, Any] = {
                "name": project_name,
            }
            if build_command:
                data["buildCommand"] = build_command
            if command_for_ignoring_build_step:
                data["commandForIgnoringBuildStep"] = command_for_ignoring_build_step
            if framework:
                data["framework"] = framework
            if dev_command:
                data["devCommand"] = dev_command
            if install_command:
                data["installCommand"] = install_command
            if output_directory:
                data["outputDirectory"] = output_directory
            if public_source:
                data["publicSource"] = public_source
            if root_directory:
                data["rootDirectory"] = root_directory
            if serverless_function_region:
                data["serverlessFunctionRegion"] = serverless_function_region
            if git_repository:
                data["gitRepository"] = domain_to_dict(git_repository)
            if environment_variables:
                data["environmentVariables"] = [
                    domain_to_dict(env) for env in environment_variables
                ]
            fact_resp = requests.post(url=url, headers=self.headers, json=data)
            if fact_resp.status_code == 200:
                return VercelResponse(
                    status="ok",
                    status_code=fact_resp.status_code,
                    result=fact_resp.json(),
                    msg=fact_resp.content.decode("utf-8"),
                )
            return VercelResponse(
                status="error",
                status_code=fact_resp.status_code,
                msg=fact_resp.content.decode("utf-8"),
            )
        except Exception as e:
            logger.error(f"VERCEL Error: {e}")
            return VercelResponse(
                status="error",
                status_code=500,
                msg=str(e),
            )

    def new_deployment(
        self,
        project_name: str,
        repo_id: str,
        github_branch: str = "main",
        framework: str = "nextjs",
    ) -> VercelResponse:
        try:
            url = self.url_base.format(endpoint=VercelEndpoints.NEW_DEPLOYMENT.value)
            data: Dict[Any, Any] = {
                "gitSource": {
                    "ref": github_branch,
                    "repoId": repo_id,
                    "type": "github",
                },
                "name": project_name,
                "projectSettings": {"framework": framework},
            }

            fact_resp = requests.post(url=url, headers=self.headers, json=data)
            if fact_resp.status_code == 200:
                return VercelResponse(
                    status="ok",
                    status_code=fact_resp.status_code,
                    msg=fact_resp.content.decode("utf-8"),
                )
            return VercelResponse(
                status="error",
                status_code=fact_resp.status_code,
                msg=fact_resp.content.decode("utf-8"),
            )
        except Exception as e:
            logger.error(f"VERCEL Error: {e}")
            return VercelResponse(
                status="error",
                status_code=500,
                msg=str(e),
            )

    def retrieve_the_environment_variables_of_a_project_by_id_or_name(
        self, project_name: str
    ) -> VercelResponse:
        try:
            url = self.url_base.format(
                endpoint=VercelEndpoints.RETRIVE_ENV_VARS.value.format(
                    idOrName=project_name
                )
            )
            fact_resp = requests.get(url=url, headers=self.headers)
            if fact_resp.status_code == 200:
                return VercelResponse(
                    status="ok",
                    status_code=fact_resp.status_code,
                    result=json.dumps(fact_resp.json()),
                    msg=fact_resp.content.decode("utf-8"),
                )
            return VercelResponse(
                status="error",
                status_code=fact_resp.status_code,
                msg=fact_resp.content.decode("utf-8"),
            )
        except Exception as e:
            logger.error(f"VERCEL Error: {e}")
            return VercelResponse(
                status="error",
                status_code=500,
                msg=str(e),
            )

    def retrieve_decrypted_the_environment_variables_of_a_project_by_id_or_name(
        self, project_name: str, env_id: str
    ) -> VercelResponse:
        try:
            url = self.url_base.format(
                endpoint=VercelEndpoints.RETRIVE_DECRYPTED_ENV_VAR.value.format(
                    idOrName=project_name, id=env_id
                )
            )
            fact_resp = requests.get(url=url, headers=self.headers)
            if fact_resp.status_code == 200:
                return VercelResponse(
                    status="ok",
                    status_code=fact_resp.status_code,
                    result=json.dumps(fact_resp.json()),
                    msg=fact_resp.content.decode("utf-8"),
                )
            return VercelResponse(
                status="error",
                status_code=fact_resp.status_code,
                msg=fact_resp.content.decode("utf-8"),
            )
        except Exception as e:
            logger.error(f"VERCEL Error: {e}")
            return VercelResponse(
                status="error",
                status_code=500,
                msg=str(e),
            )

    # NOT TESTED
    def find_domain(
        self,
        project_name: str,
        git_branch: Optional[str] = None,
        limit: Optional[int] = None,
        order: Optional[str] = None,
        production: Optional[str] = None,
        redirect: Optional[str] = None,
        redirects: Optional[bool] = None,
        since: Optional[datetime.datetime] = None,
        until: Optional[datetime.datetime] = None,
        verified: Optional[bool] = None,
        teamId: Optional[str] = None,
    ) -> VercelResponse:
        url = self.url_base.format(
            endpoint=VercelEndpoints.FIND_DOMAINS.value.format(idOrName=project_name)
        )
        if git_branch:
            url += f"?gitBranch={git_branch}"
        if limit:
            url += f"&limit={str(limit)}"
        if order:
            url += f"&order={order}"
        if production:
            url += f"&production={str(production)}"
        if redirect:
            url += f"&redirect={redirect}"
        if redirects:
            url += f"&redirects={str(redirects)}"
        if since:
            url += f"&since={str(int(since.timestamp() * 1000))}"
        if until:
            url += f"&until={str(int(until.timestamp() * 1000))}"
        if verified:
            url += f"&verified={str(verified)}"
        if teamId:
            url += f"&teamId={teamId}"
        fact_resp = requests.get(url=url, headers=self.headers)
        if fact_resp.status_code == 200:
            return VercelResponse(
                status="ok",
                status_code=fact_resp.status_code,
                result=fact_resp.json(),
                msg="ok",
            )
        return VercelResponse(
            status="error",
            status_code=fact_resp.status_code,
            msg=fact_resp.content.decode("utf-8"),
        )
