import os
import threading
from typing import Dict, List, Tuple, Optional, Callable

import click
import dearpygui.dearpygui as dpg

from humanoid_retargeting import PARAMETERS_PATH
from humanoid_retargeting.aligner import Aligner
from humanoid_retargeting.utils.retarget_params import RetargetParams, FootParams, HipParams, TrackerConfig
from humanoid_retargeting import BVH_DATA_PATH

SOURCE_FILE_PATH = os.path.join(BVH_DATA_PATH, "Reallusion", "Folk Artistry - Ba Jia Jiang", '1_BJJ_General_03.bvh')

# Global mutable state – mirrors GUI widgets
retarget_params = RetargetParams()

aligner: Aligner | None = None
lock = threading.Lock()

SAVE_DIR = None
ROBOT = None

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
    target.offset = round(app_data, 4)


def update_foot_name_callback(sender, app_data, user_data):
    robot_or_human, left_or_right = user_data.split("_")
    foot_params : FootParams = getattr(retarget_params, f"{robot_or_human}_foot")
    setattr(foot_params, f"{left_or_right}_name", strip_prefix(app_data))


def update_hip_name_callback(sender, app_data, user_data):
    robot_or_human, left_or_right = user_data.split("_")
    hip_params: HipParams = getattr(retarget_params, f"{robot_or_human}_hip")
    setattr(hip_params, f"{left_or_right}_name", strip_prefix(app_data))


def update_base_shift_callback(sender, app_data, user_data):
    setattr(retarget_params, user_data, round(app_data, 4))


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
    axis_count = 0
    for axis, label in enumerate(labels):
        dpg.add_slider_float(label=f"{prefix}{label}", user_data={"group_id": user_data, "axis": axis}, 
                             tag=f"{user_data}_slider_{axis_count}", **kwargs)
        axis_count += 1

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
            getattr(retarget_params, retarget_key)[body][meta["axis"]] = round(app_data, 4)

    def remove_component(sender, app_data, tag):
        if tag in target_dict:
            name = target_dict[tag]
            if name in getattr(retarget_params, retarget_key):
                del getattr(retarget_params, retarget_key)[name]
            del target_dict[tag]
        dpg.delete_item(tag)

    with dpg.group(parent=parent_group_tag, tag=group_id):
        with dpg.group(horizontal=True):
            dpg.add_combo(items=all_body_names, callback=update_name, user_data=group_id, tag=f"{group_id}_combo")
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

def add_tracker_callback(sender, app_data, part):
    part_name = part.strip()
    if not part_name:
        print("[Warning] Part name is empty.")
        return

    # Initialization is only performed when the part_name does not exist in tracker_dict
    if part_name not in retarget_params.tracker_dict:
        retarget_params.tracker_dict[part_name] = TrackerConfig(
            human=[],
            robot=[],
            position_cost=100,
            orientation_cost=50
        )
        print(f"[Info] Initialized tracker_dict for part '{part_name}'.")
    else:
        print(f"[Info] Part '{part_name}' already exists. Skip initialization.")

    group_id = f"tracker_part_{part_name}"
    tracker_ui_groups.append(group_id)

    def update_body(sender, app_data, meta):
        body_list = getattr(retarget_params.tracker_dict[part_name], meta["kind"])
        if meta["idx"] < len(body_list):
            body_list[meta["idx"]] = strip_prefix(app_data)
        else:
            body_list.append(strip_prefix(app_data))

    def update_cost(sender, app_data, kind):
        setattr(retarget_params.tracker_dict[part_name], kind, round(app_data, 4))

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
    
    def delete_latest_tracker(part_name: str, human_group_tag: str, robot_group_tag: str):
        for kind, group_tag in [("human", human_group_tag), ("robot", robot_group_tag)]:
            body_list = getattr(retarget_params.tracker_dict[part_name], kind)
            if not body_list:
                continue  # nothing to delete
            body_list.pop()  # remove last entry from data
            children = dpg.get_item_children(group_tag, 1)
            if children:
                dpg.delete_item(children[-1])

    with dpg.group(parent="tracker_dict_group", tag=group_id):
        with dpg.group(horizontal=True):
            dpg.add_text(f"[{part_name}]")
            dpg.add_button(label="Remove Tracker Group", callback=remove_tracker, user_data=group_id)
            dpg.add_button(label="Add Human & Robot Tracker", callback=add_body_tracker)
            dpg.add_button(label="Delete Latest Tracker", callback=lambda s, a: delete_latest_tracker(part_name, human_body_group, robot_body_group))

        dpg.add_text("Human bodies:")
        human_body_group = dpg.add_group(tag=f"{group_id}_human_body_group")

        dpg.add_text("Robot bodies:")
        robot_body_group = dpg.add_group(tag=f"{group_id}_robot_body_group")

        dpg.add_slider_float(label="Position Cost", default_value=100,
                             min_value=0, max_value=2000,
                             callback=update_cost, user_data="position_cost")
        dpg.add_slider_float(label="Orientation Cost", default_value=50,
                             min_value=0, max_value=1000,
                             callback=update_cost, user_data="orientation_cost")

    print(f"[INFO] Added tracker part: {part_name}")

# Export json file callback 

def export_json_callback(sender, app_data, user_data):
    filename = dpg.get_value("file_name_input").strip()

    if not filename:
        dpg.set_value(user_data, "[Error] Filename is empty!")
        return

    # Make sure there is a .json suffix
    if not filename.endswith(".json"):
        filename += ".json"

    # Concatenate the full path
    os.makedirs(SAVE_DIR, exist_ok=True)  # Make sure the directory exists
    json_path = os.path.join(SAVE_DIR, filename)

    try:
        retarget_params.to_json(json_path)
        dpg.set_value(user_data, f"[OK] Saved to {json_path}")
    except Exception as e:
        dpg.set_value(user_data, f"[Error] {e}")

# -----------------------------------------------------------------------------
# Module for importing json files
# -----------------------------------------------------------------------------

def sync_body_editors_from_dict(
        *,
        retarget_key: str,
        target_dict: Dict[str, Optional[str]],
        add_callback: Callable,
        all_body_names: List[str]
    ):
    """
    Synchronizes the body_ratio_dict or body_rotate_dict GUI with the values in retarget_params.
    Will clear the existing GUI and rebuild the combo and sliders.
    """
    # Clearing old GUI elements
    for group in list(target_dict):
        dpg.delete_item(group)
    target_dict.clear()

    # Counter reset
    if retarget_key == "relative_body_ratio_dict":
        global body_ratio_count
        body_ratio_count = 0
    elif retarget_key == "body_rotate_dict":
        global body_rotate_count
        body_rotate_count = 0

    data_dict = getattr(retarget_params, retarget_key)

    # Rebuild GUI item by item
    for body_name, values in data_dict.items():
        add_callback(None, None, all_body_names)
        key = list(target_dict)[-1]  # Most recently joined group_id
        target_dict[key] = body_name

        # Update the value of combo
        combo_id = f"{key}_combo"
        dpg.set_value(combo_id, body_name)

        # Update the values of the 3 sliders
        for i in range(3):
            slider_tag = f"{key}_slider_{i}"
            dpg.set_value(slider_tag, values[i])

def sync_trackers_from_params():
    """Synchronize the GUI with the contents of retarget_params.tracker_dict"""
    # Clear the existing GUI
    for group in list(tracker_ui_groups):
        dpg.delete_item(group)
    tracker_ui_groups.clear()

    for part_name, tracker_cfg in retarget_params.tracker_dict.items():
        # Temporarily use UUID to input part_name, trigger add_tracker_callback to create GUI structure
        add_tracker_callback(None, None, part_name)
        
        group_id = f"tracker_part_{part_name}"

        # Find the group of human and robot combos
        human_group = f"{group_id}_human_body_group"
        robot_group = f"{group_id}_robot_body_group"

        # Add human combo box
        for i, human_body in enumerate(tracker_cfg.human):
            print("Current tracker_cfg.human:", tracker_cfg.human)
            dpg.add_combo(
                items=aligner.human_generator.all_body_names,
                default_value=human_body,
                callback=lambda s, a, idx=i: tracker_cfg.human.__setitem__(idx, strip_prefix(a)),
                user_data={"kind": "human", "idx": i},
                parent=human_group
            )

        # Add robot combo box
        for i, robot_body in enumerate(tracker_cfg.robot):
            dpg.add_combo(
                items=aligner.robot_generator.all_body_names,
                default_value=robot_body,
                callback=lambda s, a, idx=i: tracker_cfg.robot.__setitem__(idx, strip_prefix(a)),
                user_data={"kind": "robot", "idx": i},
                parent=robot_group
            )

        # Set up the cost sliders (these two sliders are the last two children in the group by default)
        sliders = dpg.get_item_children(group_id, 1)[-2:] 
        if len(sliders) == 2:
            dpg.set_value(sliders[0], tracker_cfg.position_cost)
            dpg.set_value(sliders[1], tracker_cfg.orientation_cost)

def sync_gui_with_params():
    """Sync GUI widgets to match values from retarget_params."""

    # Update foot/hip name and height
    for entity in ["robot", "human"]:
        for side in ["left", "right"]:
            foot: FootParams = getattr(retarget_params, f"{entity}_foot")
            dpg.set_value(f"{entity}_{side}_foot_combo", foot.__dict__[f"{side}_name"])
        dpg.set_value(f"{entity}_foot_height_slider", foot.offset)

        hip: HipParams = getattr(retarget_params, f"{entity}_hip")
        for side in ["left", "right"]:
            dpg.set_value(f"{entity}_{side}_hip_combo", hip.__dict__[f"{side}_name"])
        dpg.set_value(f"{entity}_hip_height_slider", hip.offset)

    # Update base shift
    dpg.set_value("base_x_shift_slider", retarget_params.base_x_shift)
    dpg.set_value("base_y_shift_slider", retarget_params.base_y_shift)
    
    sync_body_editors_from_dict(
        retarget_key="relative_body_ratio_dict", target_dict=body_ratio_dict, 
        add_callback=add_body_ratio_callback, all_body_names=aligner.human_generator.all_body_names
    )

    sync_body_editors_from_dict(
        retarget_key="body_rotate_dict", target_dict=body_rotate_dict,
        add_callback=add_body_rotate_callback, all_body_names=aligner.human_generator.all_body_names
    )

    sync_trackers_from_params()

def import_json_callback(sender, app_data, user_data):
    path = dpg.get_value("import_file_input").strip()
    if not path or not os.path.isfile(path):
        dpg.set_value(user_data, f"[Error] Invalid path: {path}")
        return

    try:
        global retarget_params
        new_params = RetargetParams.from_json(path)
        print(new_params)
        retarget_params = new_params
        sync_gui_with_params()
        dpg.set_value(user_data, f"[OK] Loaded from {path}")
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
    with dpg.window(label="main", width=600, height=500):
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
                                user_data=f"{entity}_{side}", tag=f"{entity}_{side}_foot_combo")
                dpg.add_slider_float(label="foot height", min_value=-0.2, max_value=0.2, default_value=0.0,
                                    callback=update_height_callback, user_data=f"{entity}_foot", tag=f"{entity}_foot_height_slider")
        dpg.add_separator()

        # Human base shift
        with dpg.group():
            dpg.add_text(f"Human Base Shift")
            dpg.add_slider_float(label="base x shift", min_value=-0.2, max_value=0.2, default_value=0.0,
                                 callback=update_base_shift_callback, user_data="base_x_shift", tag="base_x_shift_slider")
            dpg.add_slider_float(label="base y shift", min_value=-0.2, max_value=0.2, default_value=0.0,
                                 callback=update_base_shift_callback, user_data="base_y_shift", tag="base_y_shift_slider")
        dpg.add_separator()

        # Human body ratio
        with dpg.group(tag="body_ratio_group"):
            dpg.add_text("Human Body Ratio")
            dpg.add_button(label="Refresh MuJoCo", callback=refresh_human_model_callback)
            for entity in ["robot", "human"]:
                dpg.add_text(f"{entity.capitalize()} Hip Name and Height")
                for side in ("left", "right"):
                    dpg.add_combo(label=f"{side} hip name", items=names[entity], callback=update_hip_name_callback,
                                user_data=f"{entity}_{side}", tag=f"{entity}_{side}_hip_combo")
                dpg.add_slider_float(label="hip height", min_value=-0.2, max_value=0.2, default_value=0.0, 
                                        callback=update_height_callback, user_data=f"{entity}_hip", tag=f"{entity}_hip_height_slider")
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
                dpg.add_button(label="Add Tracker Group", callback=lambda s, a: add_tracker_callback(s, a, dpg.get_value(text_id)))
        dpg.add_separator()
        
        # Export json file
        with dpg.group(tag="export_json"):
            dpg.add_text("Click 'Export' to save retarget_params in .json file")
            dpg.add_input_text(label="File name", tag="file_name_input", hint="e.g. params", width=300)
            status_id = dpg.add_text("")  
            dpg.add_button(label="Export", callback=export_json_callback, user_data=status_id)
        dpg.add_separator()

        
        # Import json file
        with dpg.group(tag="import_json"):
            dpg.add_text("Import retarget_params from .json file")
            dpg.add_input_text(label="File path", tag="import_file_input", hint="e.g. params.json", width=300)
            import_status_id = dpg.add_text("")
            dpg.add_button(label="Import", callback=import_json_callback, user_data=import_status_id)
        dpg.add_separator()
        
    # Launch DearPyGui
    dpg.create_viewport(title="MuJoCo Control", width=800, height=600)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

@click.command()
@click.option('--source-file-path', default=SOURCE_FILE_PATH, help='Path to the BVH file.')
@click.option('--robot-name', default='zhaplin_v0', help='Name of the robot.')
@click.option('--generator-type', default='bvh', help='Type of generator.')
@click.option('--params-name', default=None, help='Name of parameters.')
def main(source_file_path: str, robot_name: str, generator_type: str, params_name: str):
    """CLI wrapper - sets up *Aligner*, starts sim thread, launches GUI."""
    global aligner, json_path, SAVE_DIR, ROBOT
    ROBOT = robot_name
    SAVE_DIR = os.path.join(PARAMETERS_PATH, ROBOT, generator_type)
    json_path = os.path.join(PARAMETERS_PATH, robot_name, generator_type, f"{params_name}.json")
    
    aligner = Aligner(source_file_path=source_file_path, robot_name=robot_name, generator_type=generator_type)
    # aligner.set_base_rotation()

    threading.Thread(target=simulation_loop, daemon=True).start()

    create_gui()

    aligner.viewer.close()
    print(retarget_params)
    
if __name__ == "__main__":
    main()