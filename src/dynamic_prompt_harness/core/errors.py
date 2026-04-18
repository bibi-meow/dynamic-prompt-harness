class DPHError(Exception):
    def __init__(self, message: str, *, code: str = "", detail: dict | None = None):
        super().__init__(message)
        self.code = code
        self.detail = detail or {}


class RegistryError(DPHError):
    pass


class ExecutionError(DPHError):
    pass


class SchemaError(DPHError):
    pass


class AdapterError(DPHError):
    pass
