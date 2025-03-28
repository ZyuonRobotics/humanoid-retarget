import os

import xml.etree.ElementTree as ET

import numpy as np

from humanoid_retargeting import ASSETS_PATH, KUAVO_S40_XML_PATH, KUAVO_S42_XML_PATH
from humanoid_retargeting.constant import TRACKER_DICT


def traverse_body(parent_index, parent_element, body_tree, bodies_data):
    for child_body in parent_element.findall('body'):
        body_index = len(bodies_data)
        name = child_body.get('name', '')  # Default to empty string if not present
        pos = child_body.get('pos', '0 0 0')  # Default to empty string if not present
        joint_list = [joint.attrib for joint in child_body.findall('joint')]
        geom_list = [geom.attrib for geom in child_body.findall('geom') if geom.get('type') == 'mesh']
        inertial_list = [inertial.attrib for inertial in child_body.findall('inertial')]

        if parent_index == -1:
            if len(joint_list) == 0:
                joint_list = [{'name': name, 'type': 'free'}]
        assert len(joint_list) == 1, f"joint_list: {joint_list} of body {name}"
        assert len(geom_list) == 1, f"geom_list: {geom_list} of body {name}"
        assert len(inertial_list) == 1, f"inertial_list: {inertial_list} of body {name}"

        bodies_data.append({
            'name': name,
            'pos': pos,
            'joint': joint_list[0],
            'geom': geom_list[0],
            "inertial": inertial_list[0]
        })
        body_tree.append([parent_index, body_index])
        traverse_body(body_index, child_body, body_tree, bodies_data)


def parse_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    worldbody = root.find('worldbody')
    body_tree = []
    bodies_data = []
    traverse_body(-1, worldbody, body_tree, bodies_data)
    return body_tree, bodies_data


def generate_body_xml(parent, body_tree, bodies_data, current_index, tracker_qpos_list=None):
    for pair in body_tree:
        if pair[0] == current_index:
            child_index = pair[1]
            body_attrs = bodies_data[child_index]
            body_elem = ET.SubElement(parent, 'body')
            if body_attrs['name']:
                body_elem.set('name', body_attrs['name'])
            if body_attrs['pos']:
                body_elem.set('pos', body_attrs['pos'])
            joint_elem = ET.SubElement(body_elem, 'joint', attrib=body_attrs['joint'])
            geom_elem = ET.SubElement(body_elem, 'geom', attrib=body_attrs['geom'])
            inertial_elem = ET.SubElement(body_elem, 'inertial', attrib=body_attrs['inertial'])
            if tracker_qpos_list is not None:
                for name, qpos_list in tracker_qpos_list.items():
                    for smpl_name, robot_name, qpos in zip(
                            TRACKER_DICT[name]["smpl"], TRACKER_DICT[name]["robot"], qpos_list):
                        if body_attrs['name'] == robot_name:
                            site_elem = ET.SubElement(body_elem, 'site', attrib={
                                "name": f"{robot_name}_{smpl_name}_track",
                                "pos": " ".join(map(str, qpos[:3].tolist())),
                                "quat": " ".join(map(str, qpos[3:].tolist()))
                            })
            generate_body_xml(body_elem, body_tree, bodies_data, child_index, tracker_qpos_list=tracker_qpos_list)


def generate_xml(
        body_tree,
        bodies_data,
        robot_name="kuavo_s40",
        smpl_root=None,
        tracker_qpos_list=None,
        add_ground=True
):
    new_root = ET.Element('mujoco')

    compiler_elem = ET.SubElement(new_root, 'compiler', attrib={
        "angle": "radian",
        "autolimits": "true",
        "meshdir": os.path.join(ASSETS_PATH, robot_name, "meshes")
    })
    if smpl_root is not None:
        for ele in smpl_root:
            new_root.append(ele)

    visual_elem = ET.SubElement(new_root, 'visual')
    headlight_elem = ET.SubElement(visual_elem, 'headlight',
                                   attrib={"diffuse": "0.6 0.6 0.6", "ambient": "0.3 0.3 0.3", "specular": "0 0 0"})
    rgba_elem = ET.SubElement(visual_elem, 'rgba', attrib={"haze": "0.15 0.25 0.35 1"})
    global_elem = ET.SubElement(visual_elem, 'global', attrib={"azimuth": "160", "elevation": "-20"})

    asset_elem = ET.SubElement(new_root, 'asset')
    if add_ground:
        ET.SubElement(asset_elem, "texture",
                      attrib={"type": "skybox", "builtin": "gradient", "rgb1": "0.3 0.5 0.7", "rgb2": "0 0 0",
                              "width": "512", "height": "3072"})
        ET.SubElement(asset_elem, "texture",
                      attrib={"type": "2d", "name": "groundplane", "builtin": "checker", "mark": "edge",
                              "rgb1": "0.2 0.3 0.4", "rgb2": "0.1 0.2 0.3", "markrgb": "0.8 0.8 0.8", "width": "300",
                              "height": "300"})
        ET.SubElement(asset_elem, "material",
                      attrib={"name": "groundplane", "texture": "groundplane", "texuniform": "true", "texrepeat": "5 5",
                              "reflectance": "0.2"})
    for body_data in bodies_data:
        mesh_name = body_data["geom"]["mesh"]
        mesh_elem = ET.SubElement(asset_elem, 'mesh', attrib={"name": mesh_name, "file": f"{mesh_name}.STL"})

    world_body = ET.SubElement(new_root, 'worldbody')
    if add_ground:
        light_elem = ET.SubElement(world_body, "light",
                                   attrib={"pos": "0 0 3.5", "dir": "0 0 -1", "directional": "true"})
        geom_elem = ET.SubElement(world_body, "geom", attrib={"name": "floor", "size": "0 0 0.05", "type": "plane",
                                                              "material": "groundplane", "condim": "3",
                                                              "conaffinity": "15"})
    generate_body_xml(world_body, body_tree, bodies_data, -1, tracker_qpos_list=tracker_qpos_list)

    xml_string = ET.tostring(new_root, encoding='unicode', method='xml')
    return xml_string


if __name__ == '__main__':
    from humanoid_retargeting import XML_PATH_DICT
    from humanoid_retargeting.constant import ROBOT_DATA_DICT

    robot_name = "kuavo_s45"

    body_tree, bodies_data = parse_xml(XML_PATH_DICT[robot_name])
    print(body_tree)
    print(bodies_data)

    # robot_data = ROBOT_DATA_DICT[robot_name]
    # tracker_pos_list = np.zeros([sum([len(d["smpl"]) for d in TRACKER_DICT.values()]), 3])
    # tracker_quat_list = np.zeros([sum([len(d["smpl"]) for d in TRACKER_DICT.values()]), 4])
    # print(tracker_pos_list.shape)
    # generate_xml(
    #     robot_data["body_tree"], robot_data["bodies_data"], robot_name="kuavo_s42",
    #     tracker_pos_list=tracker_pos_list, tracker_quat_list=tracker_quat_list
    # )
