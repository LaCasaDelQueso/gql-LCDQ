from typing import AsyncIterator, TypeVar
from strawberry.types import Info as StrawberryInfo
from strawberry.extensions import SchemaExtension

T = TypeVar("T")


# @not_used: to implement later
class AccessLevelExtension(SchemaExtension):
    """GraphQL extension to check access level of user.

    GraphQL order of execution:
      - Start Operation
        - Start and End Parsing
        - Start and End Validation
        - Start and End Execution
      - End Operation
    """

    def resolve(self, _next, root, info: StrawberryInfo, *args, **kwargs):
        """This method is called before each field resolver."""
        return _next(root, info, *args, **kwargs)

    async def on_operation(self) -> AsyncIterator[None]:
        """This method is called before each operation (query/mutation)."""
        print("GraphQL operation start")
        # print("query", self.execution_context.query)
        # print("operation_name", self.execution_context.operation_name)
        # print("schema", self.execution_context.schema)
        # print("context", self.execution_context.context)
        # print("root_value", self.execution_context.root_value)
        # print("variables", self.execution_context.variables)
        yield
        # print("operation_type", self.execution_context.operation_type)
        # print("graphql_document", self.execution_context.graphql_document)
        # print("errors", self.execution_context.errors)
        # print("result", self.execution_context.result)
        print("GraphQL operation end")

    async def on_parse(self) -> AsyncIterator[None]:
        """This method is called before each query is parsed."""
        print("GraphQL parsing start")
        yield
        print("GraphQL parsing end")

    async def on_validate(self) -> AsyncIterator[None]:
        """This method is called before each query is validated."""
        print("GraphQL validation start")
        yield
        print("GraphQL validation end")

    async def on_execute(self) -> AsyncIterator[None]:
        """This method is called before each query is executed."""
        print("GraphQL execution start")
        yield
        print("GraphQL execution end")
