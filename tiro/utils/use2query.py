import yaml


def _convert_yaml(yaml_list):
    result = {}
    for item in yaml_list:
        if isinstance(item, dict):
            for key, value in item.items():
                result[key] = _convert_yaml(value)
        else:
            result[item] = {}
    return result


def use2query(uses_path, query_path=None):
    with open(uses_path) as f:
        uses = yaml.safe_load(f)
    query = yaml.dump(_convert_yaml(uses)).replace("{}", "")
    if query_path:
        with open(query_path, "w") as f:
            f.write(query)
    else:
        return query
