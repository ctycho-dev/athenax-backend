# File Content Guide

Use this as a simple reference for what to put in common backend files.

## `model.py`
- database table or entity definitions
- fields, types, and relationships
- ORM-specific settings

## `schema.py`
- request schemas
- response schemas
- validation rules
- use `CamelModel` when you want snake_case fields in Python but camelCase JSON output, like `class UserCreateSchema(CamelModel):`

## `repository.py`
- database queries
- CRUD operations
- lookup and filter methods
- small `try/except` blocks around database calls when you want to convert low-level errors into custom errors

## `service.py`
- business logic
- permission checks
- workflow/orchestration logic

## `exceptions.py`
- custom exception classes for the app
- one place to define errors like `NotFoundError`, `ValidationError`, `DatabaseError`, or `ExternalServiceError`
- FastAPI exception handlers that convert those errors into proper HTTP responses
- this simplifies the rest of the code because routes and services can raise clear errors instead of handling HTTP responses everywhere

## API route files
- endpoint definitions
- request and response handling
- dependency injection
- service calls, not raw business logic