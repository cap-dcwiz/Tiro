import json
from copy import copy
from datetime import datetime, timedelta
from typing import Any, Type, Optional

from fastapi import FastAPI
from pydantic import BaseModel, ValidationError

from tiro.vocabulary import Entity


class Validator:
    def __init__(self, entity: Entity, retention: int = 0):
        self.model: Type[BaseModel] = entity.model()
        self._data = {}
        self.retention: Optional[timedelta] = timedelta(seconds=retention) if retention > 0 else None
        self.data_create_time: datetime = datetime.now()

    def reset_data(self):
        self._data = {}
        if self.retention:
            self.data_create_time = datetime.now()

    def __enter__(self):
        self.reset_data()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.reset_data()

    def collect(self, path: str, value: Any):
        if self.retention is not None and \
                datetime.now() - self.data_create_time > self.retention:
            self.reset_data()
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

    def validate(self, clear_after_validation: bool = False, verbose: bool = False) -> tuple[bool, list[dict]]:
        if verbose:
            print(f"Validation Period: {self.data_create_time} to {datetime.now()}")
        try:
            self.model.parse_obj(self._data)
            if verbose:
                print("Validation Successful!")
            return True, []
        except ValidationError as e:
            if verbose:
                print(e)
            return False, e.errors()


class ValidationApp(FastAPI):
    def __init__(self, *args, **kwargs):
        super(ValidationApp, self).__init__(*args, **kwargs)
        self.validator: Optional[Validator] = None

    def init(self, validator: Validator):
        self.validator = validator

        @self.post("/point/{path}")
        def collect_data(path: str, value: str):
            self.validator.collect(path, json.loads(value))

        @self.get("/result/")
        def check_result():
            result, errors = self.validator.validate()
            return dict(
                result=result,
                errors=errors
            )
