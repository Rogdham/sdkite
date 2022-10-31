from typing import Optional, get_type_hints


class Client:
    def __init__(
        self,
    ) -> None:
        self._parent: Optional[Client] = None

        # auto-init sub-clients
        cls = type(self)
        for attr_name, attr_type in get_type_hints(cls).items():
            if not hasattr(cls, attr_name) and issubclass(attr_type, Client):
                if attr_type.__init__ is not Client.__init__:
                    raise TypeError(
                        f"Class {attr_type.__name__} used as {cls.__name__}.{attr_name}"
                        " defines a custom __init__"
                    )
                try:
                    client = attr_type()
                except RecursionError as ex:
                    raise TypeError(
                        "Clients refer each other (found for"
                        f" {attr_type.__name__} used as {cls.__name__}.{attr_name})"
                    ) from ex
                client._parent = self
                setattr(self, attr_name, client)
