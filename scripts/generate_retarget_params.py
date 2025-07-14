import os
import threading
from typing import Optional

import click
import dearpygui.dearpygui as dpg
import mujoco
import mujoco.viewer
from hurodes import ROBOTS_PATH
from hurodes.mjcf_generator.generator_base import MJCFGeneratorComposite
from hurodes.mjcf_generator.unified_generator import UnifiedMJCFGenerator

from humanoid_retargeting.mjcf_generator import RetargetingMJCFGeneratorBase, BVH2MJCFGenerator, SMPL2MJCFGenerator

retarget_params = {
    "robot": {
        "left_foot": None,
        "right_foot": None,
        "foot_height": 0.05,
    },
    "human": {
        "left_foot": None,
        "right_foot": None,
        "foot_height": 0,
    },
    "whole_body_ratio": [1., 1., 1.],
    "body_ratio_dict": {},
    "body_rotate_dict": {}
}
model: Optional[mujoco.MjModel] = None
data: Optional[mujoco.MjData] = None
viewer: Optional[mujoco.viewer.Handle] = None
human_generator: Optional[RetargetingMJCFGeneratorBase] = None
robot_generator: Optional[UnifiedMJCFGenerator] = None
generator: Optional[MJCFGeneratorComposite] = None

lock = threading.Lock()

body_ratio_groups = []


def check_and_update_base_pose(target):
    global retarget_params, data, model, human_generator, robot_generator
    # import pdb; pdb.set_trace()

    if target == "human":
        base_name = human_generator.all_body_names[0]
    elif target == "robot":
        base_name = robot_generator.all_body_names[0]
    else:
        raise ValueError("Invalid target")
    joint = data.joint(model.body(base_name).jntadr[0])
    assert len(joint.qpos) == 7, "joint must be free"

    if all([v is not None for v in retarget_params[target].values()]):
        left_foot_pos = data.body(retarget_params[target]["left_foot"]).xpos
        right_foot_pos = data.body(retarget_params[target]["right_foot"]).xpos
        foot_height = retarget_params[target]["foot_height"]
        foot_pos_z = (left_foot_pos[2] + right_foot_pos[2]) / 2 - foot_height
        joint.qpos[2] -= foot_pos_z


def simulation_loop():
    global retarget_params, data, model, viewer
    assert None not in [data, model, viewer]
    while viewer.is_running():
        with lock:
            check_and_update_base_pose("robot")
            check_and_update_base_pose("human")
            mujoco.mj_forward(model, data)
            viewer.sync()


def update_height_callback(sender, app_data, user_data):
    global retarget_params
    retarget_params[user_data]["foot_height"] = app_data


def update_foot_name_callback(sender, app_data, user_data):
    global retarget_params
    robot_or_human, left_or_right = user_data.split("_")
    retarget_params[robot_or_human][f"{left_or_right}_foot"] = app_data


def update_body_ratio_callback(sender, app_data, user_data):
    global retarget_params
    retarget_params["whole_body_ratio"][user_data["idx"]] = app_data


def refresh_human_model_callback(sender, app_data, user_data):
    global retarget_params, data, model, human_generator, robot_generator, generator, viewer
    human_generator.whole_body_ratio = retarget_params["whole_body_ratio"]
    generator.build()
    with lock:
        model = mujoco.MjModel.from_xml_string(generator.mjcf_str)
        data = mujoco.MjData(model)
        viewer.close()
        viewer = mujoco.viewer.launch_passive(model, data)


def show_body_tree_callback(sender, app_data, user_data):
    global human_generator, robot_generator
    if user_data == "human":
        text = human_generator.body_tree_str
    elif user_data == "robot":
        text = robot_generator.body_tree_str
    else:
        raise ValueError("Invalid user_data")

    with dpg.window(height=300, width=300, horizontal_scrollbar=True, label=f"{user_data} body tree"):
        dpg.add_text(text)


def create_three_slider(prefix_label="", labels=("x", "y", "z"), user_data=None, **kwargs):
    for i, label in enumerate(labels):
        dpg.add_slider_float(label=f"{prefix_label}{label}", **kwargs, user_data={
            "idx": i, "name": prefix_label, "user_data": user_data
        })


def add_body_ratio_callback(sender, app_data, all_body_names):
    group_id = f"body_ratio_{len(body_ratio_groups)}"

    def update_name(sender, app_data, user_data):
        retarget_params["body_ratio_dict"][user_data]["name"] = app_data

    def update_value(sender, app_data, user_data):
        g_id, idx = user_data["user_data"], user_data["idx"]
        retarget_params["body_ratio_dict"][g_id]["values"][idx] = app_data

    def remove_component(sender, app_data, user_data):
        dpg.delete_item(user_data)
        del retarget_params["body_ratio_dict"][user_data]
        body_ratio_groups.remove(user_data)

    with dpg.group(parent="body_ratio_group", tag=group_id):
        with dpg.group(horizontal=True):
            dpg.add_combo(items=all_body_names, callback=update_name, user_data=group_id)
            dpg.add_button(label="Remove", callback=remove_component, user_data=group_id)
        create_three_slider(callback=update_value, user_data=group_id, min_value=0.5, max_value=1.5, default_value=1.)
        retarget_params["body_ratio_dict"][group_id] = {"name": None, "values": [1.0, 1.0, 1.0]}
        body_ratio_groups.append(group_id)


def create_gui():
    global retarget_params, data, model, viewer, human_generator, robot_generator
    robot_all_body_names = robot_generator.all_body_names
    human_all_body_names = human_generator.all_body_names

    dpg.create_context()
    with dpg.window(label="main", width=500, height=400):
        with dpg.group():
            with dpg.group(horizontal=True):
                dpg.add_text("Retargeting Parameters")
                dpg.add_button(label="show robot body tree", callback=show_body_tree_callback, user_data="robot")
            dpg.add_combo(label="left foot name", items=robot_all_body_names, callback=update_foot_name_callback,
                          user_data="robot_left")
            dpg.add_combo(label="right foot name", items=robot_all_body_names, callback=update_foot_name_callback,
                          user_data="robot_right")
            dpg.add_slider_float(label="foot height", callback=update_height_callback, user_data="robot", min_value=0,
                                 max_value=0.2, default_value=0.)
        dpg.add_separator()
        with dpg.group():
            with dpg.group(horizontal=True):
                dpg.add_text("Human info")
                dpg.add_button(label="show robot body tree", callback=show_body_tree_callback, user_data="human")
            dpg.add_combo(label="left foot name", items=human_all_body_names, callback=update_foot_name_callback,
                          user_data="human_left")
            dpg.add_combo(label="right foot name", items=human_all_body_names, callback=update_foot_name_callback,
                          user_data="human_right")
            dpg.add_slider_float(label="foot height", callback=update_height_callback, user_data="human", min_value=0,
                                 max_value=0.2, default_value=0.)
        dpg.add_separator()
        with dpg.group(tag="body_ratio_group"):
            with dpg.group(horizontal=True):
                dpg.add_text("human body ratio")
                dpg.add_button(label="refresh mujoco", callback=refresh_human_model_callback)
                dpg.add_button(label="Add Component", callback=add_body_ratio_callback, user_data=human_all_body_names)
            dpg.add_text("whole body")
            create_three_slider(callback=update_body_ratio_callback, min_value=0.5, max_value=1.5, default_value=1.)
        dpg.add_separator()

    dpg.create_viewport(title='MuJoCo Control', width=800, height=600)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


@click.command()
@click.option("--robot_name", prompt="Enter the robot name")
@click.option("--motion_type", prompt="Enter the motion type")
@click.option("--motion_path", prompt="Enter the motion path")
def main(robot_name, motion_type, motion_path):
    global retarget_params, data, model, viewer, human_generator, robot_generator, generator

    if motion_type.lower() == "bvh":
        human_generator_class = BVH2MJCFGenerator
    elif motion_type.lower() == "smpl":
        human_generator_class = SMPL2MJCFGenerator
    else:
        raise ValueError("Invalid motion type")

    human_generator = human_generator_class(motion_path)
    robot_generator = UnifiedMJCFGenerator(os.path.join(ROBOTS_PATH, robot_name))

    generator = MJCFGeneratorComposite([human_generator, robot_generator])
    generator.build()

    model = mujoco.MjModel.from_xml_string(generator.mjcf_str)
    data = mujoco.MjData(model)
    viewer = mujoco.viewer.launch_passive(model, data)

    # simulation_loop()
    sim_thread = threading.Thread(target=simulation_loop, daemon=True)
    sim_thread.start()
    #
    create_gui()

    viewer.close()


if __name__ == '__main__':
    main()
