class NotFoundError(Exception):
    """Raised when a resource is not found."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ValidationError(Exception):
    """Raised when input validation fails."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class RepositoryError(Exception):
    """Raised when an error occurs in the repository."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class DatabaseError(Exception):
    """Exception raised for database-related errors."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
