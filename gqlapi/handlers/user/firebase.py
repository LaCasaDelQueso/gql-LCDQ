from gqlapi.domain.interfaces.v2.user import (
    FirebaseTokenHandlerInterface,
    TokenValidity,
    FirebaseTokenRepositoryInterface
)


class FirebaseTokenHandler(FirebaseTokenHandlerInterface):
    def __init__(
        self,
        firebase_token_repo: FirebaseTokenRepositoryInterface
    ):
        self.repository = firebase_token_repo

    def verify(self, token: str) -> TokenValidity:
        # validate token
        _valid = self.repository.verify_token(token)
        # build response
        return TokenValidity(
            token=token,
            valid=_valid['is_valid'],
            valid_until=_valid['valid_until'],
            info=_valid['info']
        )


class MockFirebaseTokenHandler(FirebaseTokenHandlerInterface):
    def __init__(
        self,
        firebase_token_repo: FirebaseTokenRepositoryInterface
    ):
        self.repository = firebase_token_repo

    def verify(self, token: str) -> TokenValidity:
        # validate token
        _valid = self.repository.verify_token(token)
        # build response
        return TokenValidity(
            token=token,
            valid=_valid['is_valid'],
            valid_until=_valid['valid_until'],
            info=_valid['info']
        )
