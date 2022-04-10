from collections import deque
from copy import copy
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Type, Optional

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ValidationError

from tiro.vocabulary import Entity


@dataclass
class ValidationResult:
    start: datetime
    end: datetime
    valid: bool
    exception: Optional[ValidationError]

    def __str__(self):
        msg = f"Validation Period: {self.start} -- {self.end}\n"
        if self.valid:
            msg += "Successful!"
        else:
            msg += f"Failed!\n{str(self.exception)}"
        return msg


class Validator:
    def __init__(self,
                 entity: Entity,
                 retention: int = 0,
                 log: bool = True,
                 log_size: int = 100
                 ):
        self.model: Type[BaseModel] = entity.model()
        self._data = {}
        self.retention: Optional[timedelta] = timedelta(seconds=retention) if retention > 0 else None
        self.data_create_time: datetime = datetime.now()
        self.log: Optional[deque[ValidationResult]] = deque(maxlen=log_size) if log else None

    def reset_data(self):
        self._data = {}
        if self.retention:
            self.data_create_time = datetime.now()

    def __enter__(self):
        self.reset_data()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.reset_data()

    def validate_retention(self):
        if self.retention is not None and \
                datetime.now() - self.data_create_time > self.retention:
            self.validate()
            self.reset_data()

    def collect(self, path: str, value: Any):
        self.validate_retention()
        self._insert_data(self._data, path.split("."), value)

    @classmethod
    def _insert_data(cls, data: dict, path: list[str], value: Any):
        component = path.pop(0)
        if not path:
            data[component] = copy(value)
        else:
            if component not in data:
                data[component] = {}
            cls._insert_data(data[component], path, value)

    def validate(self) -> ValidationResult:
        period_start = self.data_create_time
        period_end = datetime.now()
        if period_end - period_start > self.retention:
            period_end = period_start + self.retention
        try:
            self.model.parse_obj(self._data)
            res = ValidationResult(period_start, period_end, True, None)
        except ValidationError as e:
            res = ValidationResult(period_start, period_end, False, e)
        if self.log is not None:
            print([(str(x.start), str(x.end)) for x in self.log], period_start)
            if self.log and self.log[0].start == period_start:
                self.log[0] = res
            else:
                self.log.appendleft(res)
        return res


class ValidationApp(FastAPI):
    def __init__(self, validator: Validator, *args, **kwargs):
        super(ValidationApp, self).__init__(*args, **kwargs)
        self.validator: Validator = validator

        @self.post("/points/{path}")
        def collect_data(path: str, value: dict):
            self.validator.collect(path, value)

        @self.get("/results", response_class=PlainTextResponse)
        def check_result():
            self.validator.validate()
            msg = "\n\n".join([str(x) for x in self.validator.log])
            return msg
