import json
from xml.dom.minidom import parseString

def convert_connections(nodes: list, connections: list):
    converted_data = []
    for node in nodes:
        for connection in connections:
            if connection["start_id"] == node["uuid"]:
                if not "connection" in node:
                    node["connections"] = {}
                    node["connections"]["start_id"] = []
                    node["connections"]["end_id"] = []
                    node["connections"]["start_pin"] = []
                    node["connections"]["end_pin"] = []
                node["connections"]["start_id"].append(connection["start_id"])
                node["connections"]["end_id"].append(connection["end_id"])
                node["connections"]["start_pin"].append(connection["start_pin"])
                node["connections"]["end_pin"].append(connection["end_pin"])
    converted_data=nodes
    print(json.dumps(converted_data,indent=4))
    return converted_data

a = {
    "nodes": [
        {
            "type": "start_Node",
            "x": 4571,
            "y": 4897,
            "uuid": "5254dc4a-da3a-4f64-a5d0-f43d57f6e084",
            "internal-data": {}
        },
        {
            "type": "choice_Node",
            "x": 5155,
            "y": 4866,
            "uuid": "2228cbfa-8029-478c-9d62-dc4685a866ae",
            "internal-data": {}
        },
        {
            "type": "event_Node",
            "x": 4814,
            "y": 4920,
            "uuid": "23e4b45c-461f-4a65-a112-5af01b77df81",
            "internal-data": {
                "text": "example",
                "isunique": True
            }
        },
        {
            "type": "text_Node",
            "x": 4973,
            "y": 4869,
            "uuid": "a0e8222a-ff19-498f-8c29-93e2f4257e2b",
            "internal-data": {
                "text": "A zoltan ship hails you"
            }
        },
        {
            "type": "text_Node",
            "x": 5380,
            "y": 4778,
            "uuid": "70ca10c1-dbe8-4673-9e5c-3dce08666aa6",
            "internal-data": {
                "text": "Tell them about your mission and ask for supplies"
            }
        },
        {
            "type": "text_Node",
            "x": 5353,
            "y": 4952,
            "uuid": "11e6b28e-0473-487f-8480-0069fd412c47",
            "internal-data": {
                "text": "attack!"
            }
        },
        {
            "type": "playsound_Node",
            "x": 5514,
            "y": 4927,
            "uuid": "a3e094c7-a188-443e-8a72-b4dd6199f1eb",
            "internal-data": {}
        },
        {
            "type": "loadsound_Node",
            "x": 5348,
            "y": 5098,
            "uuid": "bf6b87c6-1d23-4a20-b5a8-34ccd36ffdf1",
            "internal-data": {
                "filepath": ""
            }
        },
        {
            "type": "loadship_Node",
            "x": 5699,
            "y": 4947,
            "uuid": "b73ad069-3b0f-49ee-aca9-9af33beee56c",
            "internal-data": {
                "text": "enemy-zoltan",
                "ishostile": True,
                "autoblueprint": ""
            }
        },
        {
            "type": "text_Node",
            "x": 5551,
            "y": 4751,
            "uuid": "4142a167-4f62-469a-967a-6814ca3c4fc3",
            "internal-data": {
                "text": "They give you some supplies to help you on your quest"
            }
        },
        {
            "type": "Reward_Node",
            "x": 5734,
            "y": 4725,
            "uuid": "468cf1dc-4d15-46a9-958f-1b27b7353820",
            "internal-data": {
                "amount": 20,
                "index": 0
            }
        }
    ],
    "connections": [
        {
            "start_id": "5254dc4a-da3a-4f64-a5d0-f43d57f6e084",
            "end_id": "23e4b45c-461f-4a65-a112-5af01b77df81",
            "start_pin": "output",
            "end_pin": "Start Node Connection"
        },
        {
            "start_id": "4142a167-4f62-469a-967a-6814ca3c4fc3",
            "end_id": "468cf1dc-4d15-46a9-958f-1b27b7353820",
            "start_pin": "Ex Out",
            "end_pin": "Input"
        },
        {
            "start_id": "a3e094c7-a188-443e-8a72-b4dd6199f1eb",
            "end_id": "b73ad069-3b0f-49ee-aca9-9af33beee56c",
            "start_pin": "Ex Out",
            "end_pin": "Ex In"
        },
        {
            "start_id": "bf6b87c6-1d23-4a20-b5a8-34ccd36ffdf1",
            "end_id": "a3e094c7-a188-443e-8a72-b4dd6199f1eb",
            "start_pin": "Audio",
            "end_pin": "AudioFile"
        },
        {
            "start_id": "11e6b28e-0473-487f-8480-0069fd412c47",
            "end_id": "a3e094c7-a188-443e-8a72-b4dd6199f1eb",
            "start_pin": "Ex Out",
            "end_pin": "Ex In"
        },
        {
            "start_id": "70ca10c1-dbe8-4673-9e5c-3dce08666aa6",
            "end_id": "4142a167-4f62-469a-967a-6814ca3c4fc3",
            "start_pin": "Ex Out",
            "end_pin": "Ex In"
        },
        {
            "start_id": "23e4b45c-461f-4a65-a112-5af01b77df81",
            "end_id": "a0e8222a-ff19-498f-8c29-93e2f4257e2b",
            "start_pin": "event_contain",
            "end_pin": "Ex In"
        },
        {
            "start_id": "a0e8222a-ff19-498f-8c29-93e2f4257e2b",
            "end_id": "2228cbfa-8029-478c-9d62-dc4685a866ae",
            "start_pin": "Ex Out",
            "end_pin": "Ex In"
        },
        {
            "start_id": "2228cbfa-8029-478c-9d62-dc4685a866ae",
            "end_id": "70ca10c1-dbe8-4673-9e5c-3dce08666aa6",
            "start_pin": "Choice Output0",
            "end_pin": "Ex In"
        },
        {
            "start_id": "2228cbfa-8029-478c-9d62-dc4685a866ae",
            "end_id": "11e6b28e-0473-487f-8480-0069fd412c47",
            "start_pin": "Choice Output1",
            "end_pin": "Ex In"
        }
    ]
}

def sort_nodes_by_connection_order(nodes):
    # Create a dictionary to store the start pins of each node
    start_pins = {}

    # Iterate through the nodes to collect the start pins
    for node in nodes:
        start_pins[node["uuid"]] = node["connections"]["start_pin"]

    # Sort the nodes based on the order of their connections
    sorted_nodes = sorted(nodes, key=lambda x: start_pins[x["connections"]["end_id"]])

    return sorted_nodes


def convert_node_to_xml(node):
    node_type = node["type"]
    internal_data = node["internal-data"]
    
    if node_type == "choice_Node":
        return "<choice></choice>"
    elif node_type == "event_Node":
        return f"<event name='{internal_data['text']}' unique='{internal_data['isunique']}'></event>"
    elif node_type == "text_Node":
        return f"<text>{internal_data['text']}</text>"
    elif node_type == "playsound_Node":
        return "<playSound></playSound>"
    elif node_type == "quest_Node":
        places = ["RANDOM", "LAST", "NEXT"]
        beacon = places[internal_data["index"]]
        return f"<quest beacon='{beacon}' event='{internal_data['text']}'></quest>"
    elif node_type == "loadship_Node":
        return f"<ship name='{internal_data['text']}' load='{internal_data.get('text')}' auto_blueprint='{internal_data.get('autoblueprint')}' hostile='{internal_data.get('ishostile')}'></ship>"
    elif node_type == "item_modify_Node":
        return "<item_modify></item_modify>"
    elif node_type == "Reward_Node":
        reward_types = ["scrap", "fuel", "drones", "missiles"]
        reward_type = reward_types[internal_data["index"]]
        return f"<item type='{reward_type}' amount='{internal_data['amount']}'></item>"
    elif node_type == "Damage_Node":
        effects = ["random", "all", "fire"]
        effect = effects[internal_data["Effect"]]
        return f"<damage amount='{internal_data['text']}' system='{internal_data['System']}' effect='{effect}'></damage>"
    elif node_type == "giveweapon_Node":
        return f"<weapon name='{internal_data['amount']}'></weapon>"
    elif node_type == "giveaugument_Node":
        return f"<augument name='{internal_data['amount']}'></augument>"
    elif node_type == "status":
        return "<status type='limit' target='player' system='sensors' amount='1'></status>"
    elif node_type == "autoReward":
        return "<autoReward></autoReward>"
    elif node_type == "surrender":
        return "<surrender chance='0' min='3' max='4'></surrender>"
    elif node_type == "store_Node":
        return "<store></store>"
    else:
        return "<unknown></unknown>"



def convert_to_xml(nodes):
    xml_output = "<FTL>"
    
    # Iterate through nodes
    for node in nodes:
        xml_output += convert_node_to_xml(node)

    xml_output += "</FTL>"
    return xml_output

def topological_sort(nodes):
    # Create a dictionary to store the incoming edges count for each node
    incoming_edges_count = {node['uuid']: 0 for node in nodes}

    # Create a dictionary to store the outgoing edges for each node
    outgoing_edges = {node['uuid']: [] for node in nodes}

    # Populate incoming edges count and outgoing edges
    for node in nodes:
        if 'connections' in node:
            for end_id in node['connections'].get('end_id', []):
                incoming_edges_count[end_id] += 1
                outgoing_edges[node['uuid']].append(end_id)

    # Perform topological sorting
    sorted_nodes = []
    queue = [node['uuid'] for node in nodes if incoming_edges_count[node['uuid']] == 0]

    while queue:
        current_node_uuid = queue.pop(0)
        sorted_nodes.append(current_node_uuid)

        for neighbor_uuid in outgoing_edges[current_node_uuid]:
            incoming_edges_count[neighbor_uuid] -= 1
            if incoming_edges_count[neighbor_uuid] == 0:
                queue.append(neighbor_uuid)

    # Check for cyclic dependencies
    if len(sorted_nodes) != len(nodes):
        raise ValueError("The graph contains cycles.")

    # Reorder the nodes based on the sorted order
    sorted_nodes_data = [next(node for node in nodes if node['uuid'] == uuid) for uuid in sorted_nodes]

    return sorted_nodes_data

def sort_nodes_by_connections(nodes):
    sorted_nodes = []
    nextnode = None
    startnodes = []
    uuidmap = {}

    # Create a dictionary to map UUIDs to nodes
    for node in nodes:
        uuidmap[node["uuid"]] = node

    # Find all start nodes
    for node in nodes:
        if node["type"] == "start":
            startnodes.append(node)

    # Define the sort function
    def sort(start, uuidmap):
        if "connections" in start:
            for end_id in start["connections"]["end_id"]:
                nextnode = uuidmap.get(end_id)
                if nextnode:
                    sorted_nodes.append(nextnode)
                    return sort(nextnode)

    # Process each start node
    for start in startnodes:
        sorted_nodes.append(start)
        sorted_nodes.append(sort(start, uuidmap))
        print(sorted_nodes)

    return sorted_nodes

#print("base scene: " + json.dumps(a, indent = 4))
b = convert_connections(a["nodes"], a["connections"])
#print("converted connections: " + json.dumps(b, indent=4))
b = sort_nodes_by_connections(b)
#print("sorted: " + json.dumps(b, indent=4))
b = convert_to_xml(b)
#print("converted to xml: " + parseString(b).toprettyxml())
