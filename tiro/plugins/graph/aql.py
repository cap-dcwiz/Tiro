QUERY_ATTR_AQL = """
FOR v, e, p IN 1..10 OUTBOUND @start_vertex GRAPH @graph_name
    FILTER CONCAT_SEPARATOR(".", p.edges[*].next_category) IN @patterns
    FILTER v.type == "Telemetry"?DATE_NOW() - DATE_TIMESTAMP(v.timestamp) < 1000 * @time_diff:true
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

QUERY_BY_QPATH_AQL = """
LET fields = @fields
LET all_fields = @all_paths
LET value_only = @value_only

RETURN MERGE(
FOR v, e, p IN 1..1000 OUTBOUND @start_vertex GRAPH @graph_name
{prune_statement}

    LET doc = MERGE((
        FOR v0, e0, p0 in 1..1 OUTBOUND v GRAPH @graph_name
            FILTER v0.name in fields[v.path]
            FILTER v0.type == "Telemetry"?DATE_NOW() - DATE_TIMESTAMP(v0.timestamp) < 1000 * @time_diff:true

            RETURN {{
                [v0.name]:{{
                    type:v0.type,
                    value:v0.value,
                    unit:v0.unit,
                    timestamp:v0.timestamp,
                }}
            }}
    ))

{filter_statement}

    LET path = CONCAT_SEPARATOR(".", INTERLEAVE(p.edges[*].next_category, SLICE(p.vertices[*].name, 1)))
    LET telemetry_doc = MERGE(
        FOR d IN KEYS(doc)
            FILTER doc[d].type == "Telemetry"
            RETURN {{[d]: value_only?doc[d].value:UNSET(doc[d], "type")}}
        )
    LET attribute_doc = MERGE(
        FOR d IN KEYS(doc)
            FILTER doc[d].type == "Attribute"
            RETURN {{[d]: value_only?doc[d].value:UNSET(doc[d], "type")}}
        )
    RETURN {{
        [path]: MERGE([
                LENGTH(telemetry_doc) > 0 ? {{Telemetry: telemetry_doc}} : {{}},
                LENGTH(attribute_doc) > 0 ? {{Attribute: attribute_doc}} : {{}},
            ])
        }}
)
"""

QUERY_BY_REGEX_AQL = """
LET value_only = @value_only

RETURN MERGE(
FOR v, e, p IN 1..1000 OUTBOUND @start_vertex GRAPH @graph_name
    
    LET doc = MERGE((
        FOR v0, e0, p0 in 1..1 OUTBOUND v GRAPH @graph_name
            LET d_path = CONCAT_SEPARATOR(".", APPEND(p.edges[*].next_category, v0.name))
            FILTER d_path =~ @regex
            FILTER v0.type == "Telemetry"?DATE_NOW() - DATE_TIMESTAMP(v0.timestamp) < 1000 * @time_diff:true
            RETURN {
                [v0.name]: {
                    type:v0.type,
                    value:v0.value,
                    unit:v0.unit,
                    timestamp:v0.timestamp,
                }
            }
    ))
    
    FILTER LENGTH(doc) > 0
    LET path = CONCAT_SEPARATOR(".", INTERLEAVE(p.edges[*].next_category, SLICE(p.vertices[*].name, 1)))
    LET telemetry_doc = MERGE(
        FOR d IN KEYS(doc)
            FILTER doc[d].type == "Telemetry"
            RETURN {[d]: value_only?doc[d].value:UNSET(doc[d], "type")}
        )
    LET attribute_doc = MERGE(
        FOR d IN KEYS(doc)
            FILTER doc[d].type == "Attribute"
            RETURN {[d]: value_only?doc[d].value:UNSET(doc[d], "type")}
        )
    RETURN {
        [path]: MERGE(
            [
                LENGTH(telemetry_doc) > 0 ? {Telemetry: telemetry_doc} : {},
                LENGTH(attribute_doc) > 0 ? {Attribute: attribute_doc} : {},
            ]
        )
        }
)
"""
