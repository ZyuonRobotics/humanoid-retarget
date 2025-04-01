import os
import threading
from typing import Optional

import mujoco
import mujoco.viewer
import click
import dearpygui.dearpygui as dpg
from hurodes.mjcf_generator.generator_base import MJCFGeneratorComposite
from hurodes.mjcf_generator.unified_generator import UnifiedMJCFGenerator
from hurodes import ROBOTS_PATH

from humanoid_retargeting.mjcf_generator import RetargetingMJCFGenerator, BVH2MJCFGenerator, SMPL2MJCFGenerator

retarget_params = {
    "robot":{
        "left_foot": None,
        "right_foot": None,
        "foot_height": 0.05,
    },
    "human": {
        "left_foot": None,
        "right_foot": None,
        "foot_height": 0,
    },
    "whole_body_ratio": 1.0,
    "body_ratio_dict": {}
}
model: Optional[mujoco.MjModel] = None
data: Optional[mujoco.MjData] = None
viewer: Optional[mujoco.viewer.Handle] = None
human_generator: Optional[RetargetingMJCFGenerator] = None
robot_generator: Optional[UnifiedMJCFGenerator] = None

def check_and_update_base_pose(target):
    global retarget_params, data, model, human_generator, robot_generator

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

def create_gui():
    global retarget_params, data, model, viewer, human_generator, robot_generator
    robot_all_body_names = robot_generator.all_body_names
    human_all_body_names = human_generator.all_body_names


    dpg.create_context()
    with dpg.window(label="main", width=500, height=400):


        dpg.add_text("Robot info")
        dpg.add_button(label="show robot body tree", callback=show_body_tree_callback, user_data="robot")
        dpg.add_combo(label="left foot name", items=robot_all_body_names, callback=update_foot_name_callback, user_data="robot_left")
        dpg.add_combo(label="right foot name", items=robot_all_body_names, callback=update_foot_name_callback, user_data="robot_right")
        dpg.add_slider_float(label="foot height", callback=update_height_callback, user_data="robot", max_value=0.2)

        dpg.add_text("Human info")
        dpg.add_button(label="show robot body tree", callback=show_body_tree_callback, user_data="human")
        dpg.add_combo(label="left foot name", items=human_all_body_names, callback=update_foot_name_callback, user_data="human_left")
        dpg.add_combo(label="right foot name", items=human_all_body_names, callback=update_foot_name_callback, user_data="human_right")
        dpg.add_slider_float(label="foot height", callback=update_height_callback, user_data="human", max_value=0.2)

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
    global retarget_params, data, model, viewer, human_generator, robot_generator

    if motion_type.lower() == "bvh":
        human_generator_class = BVH2MJCFGenerator
    elif motion_type.lower() == "amass":
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