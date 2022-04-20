from rich import print_json

from rich import print_json

from tiro.assets.data_hall import ServerBase, RackBase, RoomBase
from tiro.core.model import EntityList


class Server(ServerBase):
    pass


class Rack(RackBase):
    # Entities
    Server: EntityList(Server, faking_number=lambda: randint(2, 20))


class Room(RoomBase):
    # Entities
    Rack: EntityList(Rack, faking_number=10)
    Server: EntityList(Server, faking_number=5)


# models = {}
# for item in walk_packages(assets.__path__):
#     spec = item.module_finder.find_spec(item.name)
#     module = module_from_spec(spec)
#     spec.loader.exec_module(module)
#     for k, v in module.__dict__.items():
#         if isinstance(v, type) and \
#                 issubclass(v, Entity) and \
#                 v is not Entity:
#             telemetry_names = tuple(k for k, v in v.data_point_info.items() if isinstance(v, Telemetry))
#             attribute_names = tuple(k for k, v in v.data_point_info.items() if isinstance(v, Attribute))
#             model_kwargs = dict(name=k)
#             if telemetry_names:
#                 model_kwargs["telemetry"] = list[Literal[telemetry_names]], Field([], unique_items=True)
#             if attribute_names:
#                 model_kwargs["attribute"] = list[Literal[attribute_names]], Field([], unique_items=True)
#             models[k] = create_model(k, **model_kwargs)
#
# top_model = create_model("Uses", assets=(list[Union[tuple(models.values())]], ...))
#
# print_json(top_model.schema_json())

print_json(Room.use_selection_model().schema_json())
