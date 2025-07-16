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

# Containers used only for GUI
body_ratio_dict: Dict[str, str | None] = {}
body_rotate_dict: Dict[str, str | None] = {}
body_ratio_count: int = 0
body_rotate_count: int = 0
tracker_ui_groups: List[str] = []

json_name = "params_test"
json_path = None

# -----------------------------------------------------------------------------
# Utility helpers
# -----------------------------------------------------------------------------

def strip_prefix(value, prefixes: Tuple[str, ...] = ("human_", "robot_")):
    """Remove any of the *prefixes* from *value* (str/list/dict)."""
    if isinstance(value, str):
        for p in prefixes:
            if value.startswith(p):
                return value[len(p):]
        return value
    if isinstance(value, list):
        return [strip_prefix(v, prefixes) for v in value]
    if isinstance(value, dict):
        return {k: strip_prefix(v, prefixes) for k, v in value.items()}
    return value


# -----------------------------------------------------------------------------
# Simulation loop (background thread)
# -----------------------------------------------------------------------------

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


def create_three_slider(*, prefix: str = "", labels: Tuple[str, str, str] = ("x", "y", "z"), user_data=None, **kwargs):
    """Add three aligned sliders (x, y, z)."""
    for axis, lbl in enumerate(labels):
        dpg.add_slider_float(label=f"{prefix}{lbl}", user_data={"group_id": user_data, "axis": axis}, **kwargs)

# Higher‑order builder for 3‑axis editors

def add_three_axis_editor_callback(
    *,
    group_prefix: str,
    target_dict: Dict[str, Optional[str]],
    retarget_key: str,
    all_body_names: List[str],
    slider_range: Tuple[float, float],
    default_value: float,
    slider_prefix: str,
    parent_group_tag: str,
    counter: int
):
    """Factory that creates either a *ratio* or *rotation* editor section."""
    group_id = f"{group_prefix}_{counter}"
    target_dict[group_id] = None  # placeholder until body chosen

    # -- Inner callbacks --
    def update_name(sender, app_data, user_data):
        retarget_params["body_ratio_dict"][user_data]["name"] = app_data

    def update_value(sender, app_data, user_data):
        g_id, idx = user_data["user_data"], user_data["idx"]
        retarget_params["body_ratio_dict"][g_id]["values"][idx] = app_data

    def remove_component(sender, app_data, tag):
        if tag in target_dict:
            name = target_dict[tag]
            if name in getattr(retarget_params, retarget_key):
                del getattr(retarget_params, retarget_key)[name]
            del target_dict[tag]
        dpg.delete_item(tag)

    # -- Build UI --
    with dpg.group(parent=parent_group_tag, tag=group_id):
        with dpg.group(horizontal=True):
            dpg.add_combo(items=all_body_names, callback=update_name, user_data=group_id)
            dpg.add_button(label="Remove", callback=remove_component, user_data=group_id)
        create_three_slider(
            prefix=slider_prefix,
            callback=update_value,
            user_data=group_id,
            min_value=slider_range[0],
            max_value=slider_range[1],
            default_value=default_value,
        )


# Convenience wrappers ---------------------------------------------------------
def add_body_ratio_callback(sender, app_data, names):
    global body_ratio_count
    add_three_axis_editor_callback(
        group_prefix="body_ratio", target_dict=body_ratio_dict, retarget_key="relative_body_ratio_dict",
        all_body_names=names, slider_range=(0.5, 2.5), default_value=1.0, slider_prefix="", parent_group_tag="body_ratio_group",
        counter=body_ratio_count
    )
    body_ratio_count += 1
    
def add_body_rotate_callback(sender, app_data, names):
    global body_rotate_count
    add_three_axis_editor_callback(
        group_prefix="body_rotate", target_dict=body_rotate_dict, retarget_key="body_rotate_dict",
        all_body_names=names, slider_range=(-180, 180), default_value=0.0, slider_prefix="rot_", parent_group_tag="body_rotate_group",
        counter=body_rotate_count
    )
    body_rotate_count += 1

# -----------------------------------------------------------------------------
# 6. Tracker GUI – bespoke because of complex structure
# -----------------------------------------------------------------------------

def add_tracker_callback(sender, app_data, input_tag):
    part_name = dpg.get_value(input_tag).strip()
    if not part_name:
        print("[Warning] Part name is empty.")
        return
    if part_name in retarget_params.tracker_dict:
        print(f"[Warning] Part '{part_name}' already exists.")
        return

    retarget_params.tracker_dict[part_name] = TrackerConfig(
        human=[],
        robot=[],
        position_cost=100,
        orientation_cost=50
    )

    group_id = f"tracker_part_{part_name}"
    tracker_ui_groups.append(group_id)

    def update_body(sender, app_data, meta):
        body_list = getattr(retarget_params.tracker_dict[part_name], meta["kind"])
        if meta["idx"] < len(body_list):
            body_list[meta["idx"]] = strip_prefix(app_data)
        else:
            body_list.append(strip_prefix(app_data))

    def update_cost(sender, app_data, kind):
        setattr(retarget_params.tracker_dict[part_name], kind, app_data)

    def remove_tracker(sender, app_data, user_data):
        dpg.configure_item(user_data, show=False)
        dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: dpg.delete_item(user_data))
        del retarget_params.tracker_dict[part_name]
        tracker_ui_groups.remove(user_data)

    def add_body_selector(kind, parent_group):
        idx = len(getattr(retarget_params.tracker_dict[part_name], kind))
        dpg.add_combo(
            items=(aligner.human_generator.all_body_names if kind == "human" else aligner.robot_generator.all_body_names),
            callback=update_body,
            user_data={"kind": kind, "idx": idx},
            parent=parent_group
        )
        getattr(retarget_params.tracker_dict[part_name], kind).append(None)

    with dpg.group(parent="tracker_dict_group", tag=group_id):
        with dpg.group(horizontal=True):
            dpg.add_text(f"[{part_name}]")
            dpg.add_button(label="Remove", callback=remove_tracker, user_data=group_id)

        dpg.add_text("Human bodies:")
        human_body_group = dpg.add_group()
        dpg.add_button(label="Add Human Body", callback=lambda: add_body_selector("human", human_body_group))

        dpg.add_text("Robot bodies:")
        robot_body_group = dpg.add_group()
        dpg.add_button(label="Add Robot Body", callback=lambda: add_body_selector("robot", robot_body_group))

        for _ in range(2):
            add_body_selector("human", human_body_group)
            add_body_selector("robot", robot_body_group)

        dpg.add_slider_float(label="Position Cost", default_value=100,
                             min_value=0, max_value=2000,
                             callback=update_cost, user_data="position_cost")
        dpg.add_slider_float(label="Orientation Cost", default_value=50,
                             min_value=0, max_value=1000,
                             callback=update_cost, user_data="orientation_cost")

    print(f"[INFO] Added tracker part: {part_name}")

# Export json file callback 

def export_json_callback(sender, app_data, user_data):
    global json_path, json_name
    json_path = dpg.get_value("file_path_input").strip()
    if json_path:
        json_filename = os.path.basename(json_path)     # e.g. 'params.json'
        json_name = os.path.splitext(json_filename)[0]
    else:
        dpg.set_value(user_data, "[Error] Path is empty!")
        return
    try:
        retarget_params.to_json(json_path)
        dpg.set_value(user_data, f"[OK] Saved to {json_path}")
    except Exception as e:
        dpg.set_value(user_data, f"[Error] {e}")

# -----------------------------------------------------------------------------
# 7. GUI Construction (static layout)
# -----------------------------------------------------------------------------

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
