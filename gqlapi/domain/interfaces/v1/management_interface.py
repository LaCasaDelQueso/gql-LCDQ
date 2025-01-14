from abc import ABC, abstractmethod


class ManagementInterface(ABC):
    """
    Define the Service here. (functionality, input and output)
    """
    # TODO: add typing
    @abstractmethod
    def get_by_id(id):
        raise NotImplementedError

    @abstractmethod
    def update_product(id, images, priceType) -> bool:
        raise NotImplementedError
