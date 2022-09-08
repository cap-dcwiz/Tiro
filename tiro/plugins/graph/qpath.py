from pathlib import Path
from typing import Optional, Iterable

import yaml

from tiro.core.model import DataPointInfo
from tiro.core.utils import PATH_SEP


class QueryPath:
    def __init__(self, name: Optional[str], parent: Optional["QueryPath"] = None):
        self.name: Optional[str] = name
        self.parent: Optional[QueryPath] = parent
        self.children: dict[str, QueryPath] = {}
        self.data_points: dict[str, Optional[dict]] = {}
        self.aux_data_points: set[str] = set()
        self.name_constraint: Optional[str] = None

    @property
    def path_items(self) -> list[str]:
        if self.parent:
            return self.parent.path_items + [self.name]
        else:
            if self.name is None:
                return []
            else:
                return [self.name]

    @property
    def path_str(self) -> str:
        if self.parent and self.parent.path_str:
            return self.parent.path_str + PATH_SEP + self.name
        else:
            if self.name is None:
                return ""
            else:
                return self.name

    def _parse_dict(self, use_dict: dict) -> "QueryPath":
        self.data_points = {}
        self.children = {}
        for k, v in use_dict.items():
            if isinstance(v, dict) and any(not _k.startswith("$") for _k in v):
                self.children[k] = QueryPath(k, self)._parse_dict(v)
            else:
                if k == "$name_match":
                    self.name_constraint = f'"{v}"'
                else:
                    if k.startswith("_"):
                        k = k.lstrip("_")
                        self.aux_data_points.add(k)
                    self.data_points[k] = v and {_k[1:]: _v for _k, _v in v.items()}
        return self

    def traverse(self, exclude_intermediate: bool = False) -> Iterable["QueryPath"]:
        if not exclude_intermediate or self.data_points:
            yield self
        for child in self.children.values():
            yield from child.traverse()

    @classmethod
    def parse(cls, uses: dict | str | Path):
        if isinstance(uses, str):
            uses = yaml.safe_load(uses)
        if isinstance(uses, Path):
            uses = yaml.safe_load(uses.open())
        return cls(None)._parse_dict(uses)

    def all_fields(self) -> dict[str, list[str]]:
        result = {}
        if self.data_points:
            result[self.path_str] = list(self.data_points.keys())
        for child in self.children.values():
            result |= child.all_fields()
        return result

    def all_path_str(self, exclude_intermediate: bool = False):
        return [
            path.path_str
            for path in self.traverse(exclude_intermediate=exclude_intermediate)
        ]

    def prune_statement(self) -> str:
        prune_rules = []
        filter_rules = []
        all_paths = []
        for path in self.traverse(exclude_intermediate=True):
            if path.name_constraint is not None:
                path_str = path.path_str
                prune_rules.append(
                    f'(v.path == "{path_str}" AND (!(v.name =~ {path.name_constraint})))'
                )
                filter_rules.append(
                    f'FILTER v.path == "{path_str}" ? (v.name =~ {path.name_constraint}) : true'
                )
                all_paths.append(path_str)
        if prune_rules:
            prune_statement = (
                "PRUNE v.path NOT IN all_fields\n       OR "
                + "\n       OR ".join(prune_rules)
            )
        else:
            prune_statement = "PRUNE v.path NOT IN all_fields"
        if filter_rules:
            filter_statement = "\n    ".join(filter_rules)
        else:
            filter_statement = ""
        filter_path_statement = f"FILTER v.path in KEYS(fields)"
        return """
    {prune_statement}
    {filter_statement}
    {filter_path_statement}""".format(
            prune_statement=prune_statement,
            filter_statement=filter_statement,
            filter_path_statement=filter_path_statement,
        ).strip(
            "\n"
        )

    def _filter_condition(self, var: str, cond_def: dict) -> str:
        cmp_op_maps = dict(
            gt=">",
            ge=">=",
            lt=">",
            le="<=",
        )
        str_op_maps = dict(
            match="=~",
            not_match="!~",
        )
        conds = []
        for k, v in cond_def.items():
            if k in cmp_op_maps:
                conds.append(f"({var} {cmp_op_maps[k]} {v})")
            elif k in str_op_maps:
                conds.append(f'({var} {str_op_maps[k]} "{v}")')
        return " && ".join(conds)

    def filter_statement(self) -> str:
        rules = []
        for path in self.traverse(exclude_intermediate=True):
            cond = " && ".join(
                f'({self._filter_condition(f"doc.{k}.value", v)})'
                for k, v in path.data_points.items()
                if v is not None
            )
            if cond:
                rules.append(f'v.path == "{path.path_str}" ? {cond} : true')
        if rules:
            return "    FILTER " + "\n    FILTER ".join(rules)
        else:
            return ""

    def post_cleanup(self, doc):
        for k in self.data_points.keys():
            for dp_type in DataPointInfo.SUB_CLASS_NAMES:
                if dp_type in doc and k in self.aux_data_points:
                    del doc[dp_type][k]
        result = {
            k: v for k, v in doc.items() if k in DataPointInfo.SUB_CLASS_NAMES and v
        }
        for name, child in self.children.items():
            if name in doc:
                for k in doc[name]:
                    v = child.post_cleanup(doc[name][k])
                    if v:
                        result[name] = result.get(name, {})
                        result[name][k] = v
        return result
