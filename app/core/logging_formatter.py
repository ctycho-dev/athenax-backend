import logging


class ReadableFormatter(logging.Formatter):
    """Compact console formatter optimized for scanning local logs."""

    default_time_format = "%Y-%m-%d %H:%M:%S"

    RESET = "\033[0m"
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    METHOD_COLORS = {
        "GET": "\033[36m",
        "POST": "\033[32m",
        "PUT": "\033[33m",
        "PATCH": "\033[35m",
        "DELETE": "\033[31m",
    }

    def __init__(self, *args, use_colors: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_colors = use_colors

    def _colorize(self, text: str, levelname: str) -> str:
        if not self.use_colors:
            return text
        color = self.COLORS.get(levelname)
        if not color:
            return text
        return f"{color}{text}{self.RESET}"

    def _compact_request_id(self, request_id: str | None) -> str | None:
        if not request_id or request_id == "-":
            return None
        return request_id.split("-")[0]

    def _compact_user(self, user_email: str | None) -> str | None:
        if not user_email or user_email == "anonymous":
            return None
        if "@" in user_email:
            user_email = user_email.split("@", 1)[0]
        if len(user_email) > 18:
            return f"{user_email[:15]}..."
        return user_email

    def _color_method(self, method: str | None) -> str | None:
        if not method:
            return None
        if not self.use_colors:
            return method
        color = self.METHOD_COLORS.get(method.upper(), "\033[37m")
        return f"{color}{method}{self.RESET}"

    def _color_status(self, status_code: int | None) -> str | None:
        if status_code is None:
            return None
        text = str(status_code)
        if not self.use_colors:
            return text
        if status_code >= 500:
            color = "\033[31m"
        elif status_code >= 400:
            color = "\033[33m"
        elif status_code >= 300:
            color = "\033[34m"
        else:
            color = "\033[32m"
        return f"{color}{text}{self.RESET}"

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, self.datefmt).split(" ", 1)[-1]
        levelname = self._colorize(f"{record.levelname:<7}", record.levelname)
        method = getattr(record, "method", None)
        path = getattr(record, "path", None)
        status_code = getattr(record, "status_code", None)
        latency_s = getattr(record, "latency_s", None)
        detail = getattr(record, "detail", None)
        request_id = self._compact_request_id(getattr(record, "request_id", None))
        user_email = self._compact_user(getattr(record, "user_email", None))

        if method or path:
            route = " ".join(part for part in [self._color_method(method), path] if part)
            parts = [timestamp, levelname, route]
            colored_status = self._color_status(status_code)
            if colored_status is not None:
                parts.append(colored_status)
            if latency_s is not None:
                parts.append(f"{int(latency_s * 1000)}ms")
            if user_email:
                parts.append(f"user={user_email}")
            if request_id:
                parts.append(f"req={request_id}")
            if detail:
                parts.append(f"detail={detail}")
            message = " | ".join(parts)
        else:
            message = f"{timestamp} | {levelname} | {record.getMessage()}"
            if detail:
                message = f"{message} | detail={detail}"
            if request_id and record.levelno >= logging.WARNING:
                message = f"{message} | req={request_id}"
            if user_email and record.levelno >= logging.WARNING:
                message = f"{message} | user={user_email}"

        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"

        return message
