import json
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Type, Optional

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from jsonschema import validate, ValidationError as JSONSchemaValidatorError
from pydantic import BaseModel, ValidationError as PydanticValidationError

from .model import Entity
from .utils import insert_data_point_to_dict


@dataclass
class ValidationResult:
    start: datetime
    end: datetime
    valid: bool
    exception: Optional[JSONSchemaValidatorError | PydanticValidationError]

    def __str__(self):
        msg = f"Validation Period: {self.start} -- {self.end}\n"
        if self.valid:
            msg += "Successful!"
        else:
            msg += f"Failed!\n{str(self.exception)}"
        return msg

    def json(self) -> str:
        return json.dumps(self.info())

    def info(self) -> dict:
        return dict(
            start=self.start.isoformat(),
            end=self.end.isoformat(),
            valid=self.valid,
            exception=self.serialise_exception()
        )

    def serialise_exception(self) -> Optional[dict]:
        if self.exception is None:
            return None
        elif isinstance(self.exception, PydanticValidationError):
            return self.exception.errors()
        elif isinstance(self.exception, JSONSchemaValidatorError):
            return dict(message=self.exception.message,
                        path=self.exception.json_path,
                        description=str(self.exception)
                        )


class Validator:
    """
    Validator receives data points and
    validate the JSON combined from all received data points in a short period
    against the given scenario or JSON schema.
    """

    def __init__(self,
                 entity: Entity = None,
                 schema: dict = None,
                 retention: int = 0,
                 log: bool = True,
                 log_size: int = 100,
                 validate_path_only: bool = False,
                 require_all_children: bool = True,
                 ):
        if entity:
            self.model: Type[BaseModel] = entity.model(hide_dp_values=validate_path_only,
                                                       require_all_children=require_all_children)
            self.schema = None
        else:
            self.model = None
            self.schema = schema
        self._data = {}
        self.retention: Optional[timedelta] = timedelta(seconds=retention if retention > 0 else 1e9)
        self.data_create_time: datetime = datetime.now()
        self.log: deque[ValidationResult] = deque(maxlen=log_size if log else 1)
        self._collect_count = 0

    def reset_data(self) -> None:
        self._collect_count = 0
        self._data = {}
        if self.retention:
            self.data_create_time = datetime.now()

    def __enter__(self):
        self.reset_data()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.reset_data()

    def validate_retention(self):
        if datetime.now() - self.data_create_time > self.retention:
            self.validate()
            self.reset_data()

    def collect(self, path: str, value: Any):
        self.validate_retention()
        insert_data_point_to_dict(path, value, self._data)
        self._collect_count += 1

    def validate(self) -> ValidationResult:
        period_start = self.data_create_time
        period_end = datetime.now()
        if period_end - period_start > self.retention:
            period_end = period_start + self.retention
        try:
            if self.model:
                self.model.parse_obj(self._data)
            elif self.schema:
                validate(instance=self._data, schema=self.schema)
            res = ValidationResult(period_start, period_end, True, None)
        except Exception as e:
            res = ValidationResult(period_start, period_end, False, e)
        if self.log and self.log[0].start == period_start:
            self.log[0] = res
        else:
            self.log.appendleft(res)
        return res

    def validate_dict(self, content: dict):
        self._data = content
        return self.validate()

    @property
    def last_validation_start_time(self):
        if self.log:
            return self.log[0].start
        else:
            return datetime.min

    @property
    def last_result(self):
        if self.log:
            return self.log[0]
        else:
            return None

    @property
    def current_collection_size(self):
        return self._collect_count


class RestfulValidationApp(FastAPI):
    def __init__(self, validator: Validator, *args, **kwargs):
        super(RestfulValidationApp, self).__init__(*args, **kwargs)
        self.validator: Validator = validator

        @self.post("/points/{path}")
        def collect_data(path: str, value: dict):
            self.validator.collect(path, value)

        @self.get("/results", response_class=PlainTextResponse)
        def check_result():
            self.validator.validate()
            msg = "\n\n".join([str(x) for x in self.validator.log])
            return msg
