from datetime import datetime
from pathlib import Path
from typing import Optional

from arango import ArangoClient

from tiro.core import Scenario
from tiro.core.utils import PATH_SEP, insert_data_point_to_dict, split_path
from tiro.core.model import Entity

QUERY_AQL = """
FOR v, e, p IN 1..10 OUTBOUND @start_vertex GRAPH @graph_name
    FILTER CONCAT_SEPARATOR(".", p.edges[*].next_category) IN @patterns
    RETURN {
        path:INTERLEAVE(p.edges[*].next_category, SLICE(p.vertices[*]._key, 1, -1)),
        type:v.type,
        value:v.value,
        unit:v.unit,
        timestamp:v.timestamp
    }
"""

QUERY_DP_PATHS = """
FOR v, e, p IN 1..100 OUTBOUND @start_vertex GRAPH @graph_name
    FILTER HAS(v, "value")
    LET categories = SLICE(p.edges[*].next_category, 0, -1)
    LET keys = SLICE(p.vertices[*]._key, 1, -1)
    LET raw_path = APPEND(INTERLEAVE(categories, keys), [v.type, v.name])
    RETURN CONCAT_SEPARATOR(".", raw_path)
"""

QUERY_COMPLEX_FILTER = """
LET fields = {
    "Room.Rack": ["BackTemperature"],
    "Room.Rack.Server": ["CPUTemperature", "MemoryTemperature"]
}

FOR v, e, p IN 1..1000 OUTBOUND "Scenario/000" GRAPH "scenario"

    PRUNE (v.path == "Room.Rack" && (!(v.name =~ "8a")))
       OR (v.path == "Room.Rack.Server" && (!(v.name =~"290")))
       
    FILTER v.path == "Room.Rack"? v.name =~ "8a": true
    FILTER v.path == "Room.Rack.Server"? v.name =~ "290": true
    
    FILTER v.path IN ["Room.Rack", "Room.Rack.Server"]
    LET doc = MERGE((
        FOR v0, e0, p0 in 1..1 OUTBOUND v GRAPH "scenario"
            FILTER v0.name in fields[v.path]
            RETURN {
                [v0.name]:{
                    path:APPEND(INTERLEAVE(p.edges[*].next_category, SLICE(p.vertices[*]._key, 1)), v0.name),
                    type:v0.type,
                    value:v0.value,
                    unit:v0.unit,
                    timestamp:v0.timestamp,
                    aa: v.path
                }
            }
    ))
    
    FILTER v.path == "Room.Rack.Server"? doc.MemoryTemperature.value > 10 : true

    RETURN VALUES(doc)
"""


def encode_key(key: str) -> str:
    return key.replace(" ", ":$:")


def decode_key(key: str) -> str:
    return key.replace(":$:", " ")


class ArangoAgent:
    def __init__(self,
                 scenario: Scenario = None,
                 db_name: str = "tiro",
                 graph_name: str = "scenario",
                 auth_info: dict = None,
                 hosts: str = "http://localhost:8529",
                 client: ArangoClient = None,
                 ):
        self.scenario: Scenario = scenario
        self.entity: Entity = scenario.root if scenario else None
        self.db_name = db_name
        self.graph_name = graph_name
        self.client: ArangoClient = client or ArangoClient(hosts=hosts)
        self.graph = None
        self.auth_info = auth_info

    def set_scenario(self, scenario: Scenario):
        self.scenario = scenario
        self.entity = scenario.root

    def db(self, create: bool = False, clear: bool = False):
        sys_db = self.client.db("_system", **self.auth_info or {})
        if clear:
            sys_db.delete_graph(self.db_name, ignore_missing=True)
        if not sys_db.has_database(self.db_name) and create:
            sys_db.create_database(self.db_name)
        db = self.client.db(self.db_name, **self.auth_info or {})
        return db

    def create_graph(self,
                     clear_existing: bool = True,
                     clear_database: bool = False):

        db = self.db(create=True, clear=clear_database)
        if db.has_graph(self.graph_name) and clear_existing:
            db.delete_graph(self.graph_name)
        if not db.has_graph(self.graph_name):
            db.create_graph(self.graph_name)
        self.graph = db.graph(self.graph_name)

        edges_info = dict()
        vertices_info = set()
        for e_type, f_type, t_type in self.entity.all_required_edges():
            e_info = edges_info.get(e_type, dict(from_set=set(), to_set=set()))
            e_info["from_set"].add(f_type)
            e_info["to_set"].add(t_type)
            edges_info[e_type] = e_info
            vertices_info.add(f_type)
            vertices_info.add(t_type)

        for v_type in vertices_info:
            if not self.graph.has_vertex_collection(v_type):
                self.graph.create_vertex_collection(v_type)

        for e_type, e_info in edges_info.items():
            if self.graph.has_edge_definition(e_type):
                self.graph.replace_edge_definition(e_type, list(e_info["from_set"]), list(e_info["to_set"]))
            else:
                self.graph.create_edge_definition(e_type, list(e_info["from_set"]), list(e_info["to_set"]))

        return self

    def insert_vertices_and_edges(self, vertices=None, edges=None, replace=False, insert_default_dp=False):
        vertices = vertices or {}
        edges = edges or []
        for v_type, v_value in vertices.items():
            v_collection = self.graph.vertex_collection(v_type)
            if not v_collection.has(v_value["_key"]):
                v_collection.insert(v_value)
                if insert_default_dp and "value" not in v_value:
                    self.create_default_data_points(v_type, v_value["_key"], v_value["path"])
            elif replace:
                v_collection.update(v_value)
        for e_type, e_key, e_from, e_to, e_data in edges:
            e_collection = self.graph.edge_collection(e_type)
            if not e_collection.has(e_key):
                e_collection.insert(dict(_key=e_key, _from=e_from, _to=e_to) | e_data)

    def create_default_data_points(self, parent_type, parent_id, path):
        edges = []
        vertices = {}
        path = split_path(path)
        defaults = self.entity.default_values(path)
        for key, item in defaults.items():
            dp_id = f"{parent_id}-{key}"
            edges.append((f"has_data_point",
                          f"{parent_id}_{dp_id}",
                          f"{parent_type}/{parent_id}",
                          f"{item['type']}/{dp_id}",
                          dict(next_category=key)))
            vertices[item["type"]] = {"_key": dp_id, "name": key} | item
        self.insert_vertices_and_edges(vertices, edges, replace=False)

    def parse_doc_to_graph_components(self, doc: dict):
        path = doc["path"].split(PATH_SEP)
        root_name = self.entity.name
        path.insert(0, root_name)
        edges = []
        vertices = {}
        for i in range(len(path) - 1):
            entity_type = path[i]
            if entity_type == root_name:
                name = "000"
            else:
                name = doc[entity_type]
            entity_id = encode_key(name)
            vertices[entity_type] = {
                "_key": entity_id,
                "name": name,
                "path": PATH_SEP.join(path[1:i + 1]),
            }
            if i != len(path) - 2:
                next_type = path[i + 1]
                next_id = encode_key(doc[path[i + 1]])
                edges.append((
                    f"is_parent_of",
                    f"{entity_id}_{next_id}",
                    f"{entity_type}/{entity_id}",
                    f"{next_type}/{next_id}",
                    dict(next_category=next_type)
                ))
        final_entity_type = path[-2]
        if final_entity_type == root_name:
            final_entity_id = "000"
        else:
            final_entity_id = encode_key(doc[final_entity_type])
        dp_name = path[-1]
        dp_type = doc['type']
        dp_id = f"{final_entity_id}-{dp_name}"
        timestamp = doc["timestamp"]
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        edges.append((
            f"has_data_point",
            f"{final_entity_id}_{dp_id}",
            f"{final_entity_type}/{final_entity_id}",
            f"{dp_type}/{dp_id}",
            dict(next_category=dp_name)
        ))
        vertices[dp_type] = {
            "_key": dp_id,
            "type": dp_type,
            "name": dp_name,
            "value": doc["value"],
            "unit": doc.get("unit", None),
            "timestamp": timestamp,
        }
        return {
            "vertices": vertices,
            "edges": edges,
        }

    def collect_raw(self, path: str, data: dict):
        for item in Scenario.decompose_data(path, data):
            self.update(item)

    def update(self, item: dict):
        g_info = self.parse_doc_to_graph_components(item)
        self.insert_vertices_and_edges(g_info["vertices"], g_info["edges"],
                                       replace=False,
                                       insert_default_dp=True)

    def capture_status(self,
                       pattern_or_uses: Optional[str | dict | Path] = None,
                       paths: Optional[list[str]] = None,
                       flatten: bool = False,
                       fill_with_default: bool = False,
                       skip_telemetry_in_tsdb: bool = False):
        if paths:
            if pattern_or_uses:
                paths.extend(self.entity.match_data_points(pattern_or_uses))
        else:
            if pattern_or_uses:
                paths = list(self.entity.match_data_points(pattern_or_uses))
            else:
                paths = list(self.entity.uses)
        db = self.db(create=False)
        start_vertex = f"{self.entity.name}/000"
        cursor = db.aql.execute(QUERY_AQL,
                                bind_vars=dict(
                                    start_vertex=start_vertex,
                                    graph_name=self.graph_name,
                                    patterns=paths
                                ))
        data = {}
        for item in cursor:
            path = [decode_key(p) for p in item.pop("path")]
            dp_type = item.pop("type")
            path.insert(-1, dp_type)
            if skip_telemetry_in_tsdb and dp_type == "Telemetry":
                continue
            if flatten:
                data[PATH_SEP.join(path)] = item
            else:
                insert_data_point_to_dict(path, item, data)
        if fill_with_default:
            missing_paths = self.scenario.guess_missing_paths(
                existing_paths=self.all_data_points(),
                pattern_or_uses=pattern_or_uses)
            for path in missing_paths:
                default_value = self.scenario.query_data_point_info(
                    self.scenario.data_point_path_to_path(path)
                ).default_object()
                if default_value:
                    if flatten:
                        data[path] = default_value
                    else:
                        insert_data_point_to_dict(path, default_value, data)
        return data

    def all_data_points(self):
        db = self.db(create=False)
        start_vertex = f"{self.entity.name}/000"
        cursor = db.aql.execute(QUERY_DP_PATHS,
                                bind_vars=dict(
                                    start_vertex=start_vertex,
                                    graph_name=self.graph_name,
                                ))
        return [decode_key(x) for x in cursor]
