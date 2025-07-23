import os
import threading
from typing import Dict, List, Tuple, Optional
from itertools import product

import click
import dearpygui.dearpygui as dpg
import mujoco
import mujoco.viewer

from humanoid_retargeting import PARAMETERS_PATH
from humanoid_retargeting.aligner import Aligner
from humanoid_retargeting.utils.retarget_params import RetargetParams, FootParams, HipParams, TrackerConfig
from humanoid_retargeting import BVH_DATA_PATH

SOURCE_FILE_PATH = os.path.join(BVH_DATA_PATH, "Reallusion", "Folk Artistry - Ba Jia Jiang", '1_BJJ_General_03.bvh')

# Global mutable state – mirrors GUI widgets
retarget_params = RetargetParams()

aligner: Aligner | None = None
lock = threading.Lock()

# Containers used only for GUI
body_ratio_dict: Dict[str, str | None] = {}
body_rotate_dict: Dict[str, str | None] = {}
body_ratio_count: int = 0
body_rotate_count: int = 0
tracker_ui_groups: List[str] = []


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


def simulation_loop():
    """Continuously push retarget_params into MuJoCo viewer while it is open."""
    assert aligner and all([aligner.data, aligner.model, aligner.viewer])
    while aligner.viewer.is_running():
        with lock:
            aligner.retarget_params = retarget_params
            aligner.load_cali_qpos()
            aligner.viewer.sync()


# Generic GUI‑building primitives & callbacks

def update_height_callback(sender, app_data, user_data):
    """Slider callback for foot / hip height."""
    target = getattr(retarget_params, user_data)
    target.offset = app_data


def update_foot_name_callback(sender, app_data, user_data):
    robot_or_human, left_or_right = user_data.split("_")
    foot_params : FootParams = getattr(retarget_params, f"{robot_or_human}_foot")
    setattr(foot_params, f"{left_or_right}_name", strip_prefix(app_data))


def update_hip_name_callback(sender, app_data, user_data):
    robot_or_human, left_or_right = user_data.split("_")
    hip_params: HipParams = getattr(retarget_params, f"{robot_or_human}_hip")
    setattr(hip_params, f"{left_or_right}_name", strip_prefix(app_data))


def update_base_shift_callback(sender, app_data, user_data):
    setattr(retarget_params, user_data, app_data)


def refresh_human_model_callback(sender, app_data, user_data):
    """Re-build MJCF after body ratio scaling changes, preserving viewer window."""
    global retarget_params
    with lock:
        aligner.viewer.close()
        aligner.load_mujoco(retarget_params=retarget_params)
        aligner.load_cali_qpos()
        aligner.viewer.sync()


def show_body_tree_callback(sender, app_data, kind):
    """Display a scrollable window with the body tree (robot or human)."""
    tree_str = aligner.human_generator.body_tree_str if kind == "human" else aligner.robot_generator.body_tree_str
    with dpg.window(height=300, width=300, horizontal_scrollbar=True, label=f"{kind} body tree"):
        dpg.add_text(tree_str)

# Common slider factory

def create_three_slider(*, prefix: str = "", labels: Tuple[str, str, str] = ("x", "y", "z"), user_data=None, **kwargs):
    """Add three aligned sliders (x, y, z)."""
    for axis, label in enumerate(labels):
        dpg.add_slider_float(label=f"{prefix}{label}", user_data={"group_id": user_data, "axis": axis}, **kwargs)

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

    def update_name(sender, app_data, user_data):
        target_dict[user_data] = strip_prefix(app_data)
        getattr(retarget_params, retarget_key)[strip_prefix(app_data)] = [default_value] * 3

    def update_value(sender, app_data, meta):
        body = target_dict[meta["group_id"]]
        if body is not None:
            getattr(retarget_params, retarget_key)[body][meta["axis"]] = app_data

    def remove_component(sender, app_data, tag):
        if tag in target_dict:
            name = target_dict[tag]
            if name in getattr(retarget_params, retarget_key):
                del getattr(retarget_params, retarget_key)[name]
            del target_dict[tag]
        dpg.delete_item(tag)

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

# Tracker GUI – bespoke because of complex structure

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

    def add_body_tracker(sender, app_data, user_data):
        for entity in ["human", "robot"]:
            idx = len(getattr(retarget_params.tracker_dict[part_name], entity))
            dpg.add_combo(
                items=getattr(aligner, f"{entity}_generator").all_body_names,
                callback=update_body,
                user_data={"kind": entity, "idx": idx},
                parent=human_body_group if entity == "human" else robot_body_group
            )
            getattr(retarget_params.tracker_dict[part_name], entity).append(None)

    with dpg.group(parent="tracker_dict_group", tag=group_id):
        with dpg.group(horizontal=True):
            dpg.add_text(f"[{part_name}]")
            dpg.add_button(label="Remove Tracker Group", callback=remove_tracker, user_data=group_id)
            dpg.add_button(label="Add Human & Robot Tracker", callback=add_body_tracker)

        dpg.add_text("Human bodies:")
        human_body_group = dpg.add_group()

        dpg.add_text("Robot bodies:")
        robot_body_group = dpg.add_group()

        add_body_tracker(None, None, None)

        dpg.add_slider_float(label="Position Cost", default_value=100,
                             min_value=0, max_value=2000,
                             callback=update_cost, user_data="position_cost")
        dpg.add_slider_float(label="Orientation Cost", default_value=50,
                             min_value=0, max_value=1000,
                             callback=update_cost, user_data="orientation_cost")

    print(f"[INFO] Added tracker part: {part_name}")

# Export json file callback 

def export_json_callback(sender, app_data, user_data):
    global json_path, params_name
    json_path = dpg.get_value("file_path_input").strip()
    if json_path:
        json_filename = os.path.basename(json_path)     # e.g. 'params.json'
        params_name = os.path.splitext(json_filename)[0]
    else:
        dpg.set_value(user_data, "[Error] Path is empty!")
        return
    try:
        retarget_params.to_json(json_path)
        dpg.set_value(user_data, f"[OK] Saved to {json_path}")
    except Exception as e:
        dpg.set_value(user_data, f"[Error] {e}")

# -----------------------------------------------------------------------------
# GUI Construction (static layout)
# -----------------------------------------------------------------------------

def create_gui():
    """Instantiate DearPyGui widgets and enter its main loop."""
    global params_name
    names = {
        "robot": aligner.robot_generator.all_body_names,
        "human": aligner.human_generator.all_body_names
    }

    dpg.create_context()
    with dpg.window(label="main", width=500, height=400):
        # Show body tree
        with dpg.group():
            dpg.add_text("Show Body Tree")
            dpg.add_button(label="Show Robot Body Tree", callback=show_body_tree_callback, user_data="robot")
            dpg.add_button(label="Show Human Body Tree", callback=show_body_tree_callback, user_data="human")
        dpg.add_separator()

        # Foot and hip info
        with dpg.group():
            for entity in ["robot", "human"]:
                dpg.add_text(f"{entity.capitalize()} Feet Name and Height")
                for side in ("left", "right"):
                    dpg.add_combo(label=f"{side} foot name", items=names[entity], callback=update_foot_name_callback,
                                user_data=f"{entity}_{side}")
                dpg.add_slider_float(label="foot height", min_value=-0.2, max_value=0.2, default_value=0.0,
                                    callback=update_height_callback, user_data=f"{entity}_foot")
        dpg.add_separator()

        # Human base shift
        with dpg.group():
            dpg.add_text(f"Human Base Shift")
            dpg.add_slider_float(label="base x shift", min_value=-0.2, max_value=0.2, default_value=0.0,
                                 callback=update_base_shift_callback, user_data="base_x_shift")
            dpg.add_slider_float(label="base y shift", min_value=-0.2, max_value=0.2, default_value=0.0,
                                 callback=update_base_shift_callback, user_data="base_y_shift")
        dpg.add_separator()

        # Human body ratio
        with dpg.group(tag="body_ratio_group"):
            dpg.add_text("Human Body Ratio")
            dpg.add_button(label="Refresh MuJoCo", callback=refresh_human_model_callback)
            for entity in ["robot", "human"]:
                dpg.add_text(f"{entity.capitalize()} Hip Name and Height")
                for side in ("left", "right"):
                    dpg.add_combo(label=f"{side} hip name", items=names[entity], callback=update_hip_name_callback,
                                user_data=f"{entity}_{side}")
                dpg.add_slider_float(label="hip height", min_value=-0.2, max_value=0.2, default_value=0.0, 
                                        callback=update_height_callback, user_data=f"{entity}_hip")
            dpg.add_button(label="Add Relative Body Ratio Component", callback=add_body_ratio_callback, user_data=names["human"])
        dpg.add_separator()

        # Human body rotation
        with dpg.group(tag="body_rotate_group"):
            dpg.add_text("Human Body Rotation")
            dpg.add_button(label="Add Rotation Component", callback=add_body_rotate_callback, user_data=names["human"])
        dpg.add_separator()

        # Tracker dict
        with dpg.group(tag="tracker_dict_group"):
            dpg.add_text("Retargeting Tracker")
            with dpg.group(horizontal=True):
                text_id = dpg.generate_uuid()
                dpg.add_input_text(tag=text_id, hint="Enter tracker group name")
                dpg.add_button(label="Add Tracker Group", callback=add_tracker_callback, user_data=text_id)
        dpg.add_separator()
        
        # Export json file
        with dpg.group(tag="export_json"):
            dpg.add_text("Click 'Export' to export retarget_params into .json file")
            dpg.add_input_text(label="File path", tag="file_path_input", hint="e.g. params", width=300)
            status_id = dpg.add_text("")  
            dpg.add_button(label="Export", callback=export_json_callback, user_data=status_id)
        dpg.add_separator()

    # Launch DearPyGui
    dpg.create_viewport(title="MuJoCo Control", width=800, height=600)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

@click.command()
@click.option('--source-file-path', default=SOURCE_FILE_PATH, help='Path to the BVH file.', prompt="Path to the BVH file")
@click.option('--robot-name', default='unitree_g1', help='Name of the robot.', prompt="Name of the robot")
@click.option('--generator-type', default='bvh', help='Type of generator.', prompt="Type of generator")
@click.option('--params-name', default=None, help='Name of parameters.', prompt="Name of parameters")
def main(source_file_path: str, robot_name: str, generator_type: str, params_name: str):
    """CLI wrapper - sets up *Aligner*, starts sim thread, launches GUI."""
    global aligner, json_path
    json_path = os.path.join(PARAMETERS_PATH, robot_name, generator_type, f"{params_name}.json")
    
    aligner = Aligner(source_file_path=source_file_path, robot_name=robot_name, generator_type=generator_type)
    # aligner.set_base_rotation()

    threading.Thread(target=simulation_loop, daemon=True).start()

    create_gui()

    aligner.viewer.close()
    print(retarget_params)
    
if __name__ == "__main__":
    main()