import os
import threading
from dataclasses import asdict
from copy import deepcopy
from typing import Dict, List, Tuple

import click
import dearpygui.dearpygui as dpg
import mujoco
import mujoco.viewer

from hurodes.mjcf_generator.generator_composite import MJCFGeneratorComposite
from hurodes.mjcf_generator.unified_generator import UnifiedMJCFGenerator
from hurodes import ROBOTS_PATH

from humanoid_retargeting.mjcf_generator import (
    RetargetingMJCFGeneratorBase, BVH2MJCFGenerator, SMPL2MJCFGenerator  # noqa: F401
)
from humanoid_retargeting.aligner import Aligner
from humanoid_retargeting.utils.rot import euler2quat                       # noqa: F401 – may be used elsewhere
from humanoid_retargeting.utils.retarget_params import (
    RetargetParams, FootParams, HipParams, TrackerConfig,
)

# -----------------------------------------------------------------------------
# Global mutable state – mirrors GUI widgets
# -----------------------------------------------------------------------------
retarget_params: Dict = {
    "robot_foot":  {"left_name": None, "right_name": None, "offset": 0.0},
    "human_foot":  {"left_name": None, "right_name": None, "offset": 0.0},
    "robot_hip":   {"left_name": None, "right_name": None, "offset": 0.0},
    "human_hip":   {"left_name": None, "right_name": None, "offset": 0.0},
    "base_x_shift": 0.0,
    "base_y_shift": 0.0,
    "base_rotation": [90, 0, 90],
    "extra_body_ratio": [1.0, 1.0, 1.0],
    "relative_body_ratio_dict": {},
    "body_rotate_dict": {},
    "tracker_dict": {}
}

aligner: Aligner | None = None
lock = threading.Lock()

# Containers used only for GUI
body_ratio_dict: Dict[str, str | None] = {}
body_rotate_dict: Dict[str, str | None] = {}
tracker_ui_groups: List[str] = []

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


def convert_dict_to_retarget_params(src: Dict) -> RetargetParams:
    """Convert GUI dictionary **src** → immutable ``RetargetParams`` dataclass."""
    data = deepcopy(src)  # avoid mutating caller
    clean: Dict = {}

    # -- Foot / Hip params
    for key in ("robot_foot", "human_foot"):
        if key in data:
            f = data[key]
            clean[key] = FootParams(strip_prefix(f["left_name"]), strip_prefix(f["right_name"]), f["offset"])
    for key in ("robot_hip", "human_hip"):
        if key in data:
            h = data[key]
            clean[key] = HipParams(strip_prefix(h["left_name"]), strip_prefix(h["right_name"]), h["offset"])

    # -- Scalars / vectors
    clean.update({
        "base_x_shift":   data.get("base_x_shift", 0.0),
        "base_y_shift":   data.get("base_y_shift", 0.0),
        "base_rotation":  data.get("base_rotation", [0.0, 0.0, 0.0]),
        "extra_body_ratio": data.get("extra_body_ratio", [1.0, 1.0, 1.0]),
        "relative_body_ratio_dict": {strip_prefix(k): v for k, v in data.get("relative_body_ratio_dict", {}).items()},
        "body_rotate_dict":         {strip_prefix(k): v for k, v in data.get("body_rotate_dict", {}).items()},
    })

    # -- Tracker dict
    track_raw = data.get("tracker_dict", {})
    track_clean: Dict[str, TrackerConfig] = {}
    for part, cfg in track_raw.items():
        track_clean[part] = TrackerConfig(
            human=[strip_prefix(x) for x in cfg["human"]],
            robot=[strip_prefix(x) for x in cfg["robot"]],
            position_cost=cfg.get("position_cost", 100),
            orientation_cost=cfg.get("orientation_cost", 50),
        )
    clean["tracker_dict"] = track_clean

    # -- Fill unspecified fields with defaults
    defaults = RetargetParams()
    for k in asdict(defaults):
        clean.setdefault(k, getattr(defaults, k))

    return RetargetParams(**clean)

# -----------------------------------------------------------------------------
# Simulation loop (background thread)
# -----------------------------------------------------------------------------

def simulation_loop():
    """Continuously push *retarget_params* into MuJoCo viewer while it is open."""
    assert aligner and all([aligner.data, aligner.model, aligner.viewer])
    while aligner.viewer.is_running():
        with lock:
            aligner.retarget_params = convert_dict_to_retarget_params(retarget_params)
            aligner.set_base_pose()
            aligner.set_dof_pos()
            mujoco.mj_forward(aligner.model, aligner.data)
            aligner.viewer.sync()

# -----------------------------------------------------------------------------
# Generic GUI‑building primitives & callbacks
# -----------------------------------------------------------------------------
# These mutate *retarget_params* in response to widget events.

# Simple scalar updates

def update_height_callback(sender, app_data, user_data):
    """Slider callback for foot / hip height."""
    retarget_params[user_data]["offset"] = app_data


def update_foot_name_callback(sender, app_data, user_data):
    robot_or_human, side = user_data.split("_")
    retarget_params[f"{robot_or_human}_foot"][f"{side}_name"] = app_data


def update_hip_name_callback(sender, app_data, user_data):
    robot_or_human, side = user_data.split("_")
    retarget_params[f"{robot_or_human}_hip"][f"{side}_name"] = app_data


def update_body_ratio_callback(sender, app_data, user_data):
    retarget_params["extra_body_ratio"][user_data["idx"]] = app_data


def update_base_shift_callback(sender, app_data, user_data):
    retarget_params[user_data] = app_data

# Model refresh (not finished) 

def refresh_human_model_callback(*_):
    """Re-build MJCF after global scaling changes, preserving viewer window."""
    aligner.human_generator.whole_body_ratio = retarget_params["whole_body_ratio"]
    with lock:
        aligner.generator.build()
        model = mujoco.MjModel.from_xml_string(aligner.generator.mjcf_str)
        data = mujoco.MjData(model)
        viewer.close()
        viewer = mujoco.viewer.launch_passive(model, data)

# Popup tree viewer

def show_body_tree_callback(sender, app_data, kind):
    """Display a scrollable window with the body tree (robot or human)."""
    tree_str = aligner.human_generator.body_tree_str if kind == "human" else aligner.robot_generator.body_tree_str
    with dpg.window(height=300, width=300, horizontal_scrollbar=True, label=f"{kind} body tree"):
        dpg.add_text(tree_str)

# Common slider factory

def create_three_slider(*, prefix: str = "", labels: Tuple[str, str, str] = ("x", "y", "z"), user_data=None, **kwargs):
    """Add three aligned sliders (x, y, z)."""
    for axis, lbl in enumerate(labels):
        dpg.add_slider_float(label=f"{prefix}{lbl}", user_data={"group_id": user_data, "axis": axis}, **kwargs)

# Higher‑order builder for 3‑axis editors

def add_three_axis_editor_callback(
    *,
    group_prefix: str,
    target_dict: Dict[str, str | None],
    retarget_key: str,
    all_body_names: List[str],
    slider_range: Tuple[float, float],
    default_value: float,
    slider_prefix: str,
    parent_group_tag: str,
):
    """Factory that creates either a *ratio* or *rotation* editor section."""
    group_id = f"{group_prefix}_{len(target_dict)}"
    target_dict[group_id] = None  # placeholder until body chosen

    # -- Inner callbacks --
    def update_name(sender, app_data, user_data):
        target_dict[user_data] = app_data
        retarget_params[retarget_key][app_data] = [default_value] * 3

    def update_value(sender, app_data, meta):
        body = target_dict[meta["group_id"]]
        retarget_params[retarget_key][body][meta["axis"]] = app_data

    def remove_component(sender, app_data, tag):
        dpg.delete_item(tag)
        del retarget_params[retarget_key][target_dict[tag]]
        del target_dict[tag]

    # -- Build UI --
    with dpg.group(parent=parent_group_tag, tag=group_id):
        with dpg.group(horizontal=True):
            dpg.add_combo(items=all_body_names, callback=update_name, user_data=group_id)
            dpg.add_button(label="Remove", callback=remove_component, user_data=group_id)
        create_three_slider(prefix=slider_prefix, callback=update_value, user_data=group_id,
                            min_value=slider_range[0], max_value=slider_range[1], default_value=default_value)

# Convenience wrappers ---------------------------------------------------------
add_body_ratio_callback = lambda s, a, names: add_three_axis_editor_callback(
    group_prefix="body_ratio", target_dict=body_ratio_dict, retarget_key="relative_body_ratio_dict",
    all_body_names=names, slider_range=(0.5, 1.5), default_value=1.0, slider_prefix="", parent_group_tag="body_ratio_group"
)
add_body_rotate_callback = lambda s, a, names: add_three_axis_editor_callback(
    group_prefix="body_rotate", target_dict=body_rotate_dict, retarget_key="body_rotate_dict",
    all_body_names=names, slider_range=(-180, 180), default_value=0.0, slider_prefix="rot_", parent_group_tag="body_rotate_group"
)

# -----------------------------------------------------------------------------
# 6. Tracker GUI – bespoke because of complex structure
# -----------------------------------------------------------------------------

def add_tracker_callback(sender, app_data, input_tag):
    part_name = dpg.get_value(input_tag).strip()
    if not part_name:
        print("[Warning] Part name is empty.")
        return
    if part_name in retarget_params["tracker_dict"]:
        print(f"[Warning] Part '{part_name}' already exists.")
        return

    retarget_params["tracker_dict"][part_name] = {
        "human": [],
        "robot": [],
        "position_cost": 100,
        "orientation_cost": 50
    }

    group_id = f"tracker_part_{part_name}"
    tracker_ui_groups.append(group_id)

    def update_body(sender, app_data, meta):
        body_list = retarget_params["tracker_dict"][part_name][meta["kind"]]
        if meta["idx"] < len(body_list):
            body_list[meta["idx"]] = app_data
        else:
            body_list.append(app_data)

    def update_cost(sender, app_data, kind):
        retarget_params["tracker_dict"][part_name][kind] = app_data

    def remove_tracker(sender, app_data, user_data):
        dpg.configure_item(user_data, show=False)
        dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: dpg.delete_item(user_data))
        del retarget_params["tracker_dict"][part_name]
        tracker_ui_groups.remove(user_data)

    def add_body_selector(kind, parent_group):
        idx = len(retarget_params["tracker_dict"][part_name][kind])
        dpg.add_combo(
            items=(aligner.human_generator.all_body_names if kind == "human" else aligner.robot_generator.all_body_names),
            callback=update_body,
            user_data={"kind": kind, "idx": idx},
            parent=parent_group
        )
        retarget_params["tracker_dict"][part_name][kind].append(None)

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


# -----------------------------------------------------------------------------
# 7. GUI Construction (static layout)
# -----------------------------------------------------------------------------

def create_gui():
    """Instantiate DearPyGui widgets and enter its main loop."""
    robot_names = aligner.robot_generator.all_body_names
    human_names = aligner.human_generator.all_body_names

    dpg.create_context()
    with dpg.window(label="main", width=500, height=400):
        # ---- Robot info --------------------------------------------------------
        with dpg.group():
            with dpg.group(horizontal=True):
                dpg.add_text("Robot Info")
                dpg.add_button(label="Show robot body tree", callback=show_body_tree_callback, user_data="robot")
            for side in ("left", "right"):
                dpg.add_combo(label=f"{side} foot name", items=robot_names, callback=update_foot_name_callback,
                              user_data=f"robot_{side}")
            for side in ("left", "right"):
                dpg.add_combo(label=f"{side} hip name", items=robot_names, callback=update_hip_name_callback,
                              user_data=f"robot_{side}")
            dpg.add_slider_float(label="foot height", min_value=-0.2, max_value=0.2, default_value=0.0,
                                 callback=update_height_callback, user_data="robot_foot")
            dpg.add_slider_float(label="hip height", min_value=-0.2, max_value=0.2, default_value=0.0,
                                 callback=update_height_callback, user_data="robot_hip")
        dpg.add_separator()

        # ---- Human info --------------------------------------------------------
        with dpg.group():
            with dpg.group(horizontal=True):
                dpg.add_text("Human Info")
                dpg.add_button(label="Show human body tree", callback=show_body_tree_callback, user_data="human")
            for side in ("left", "right"):
                dpg.add_combo(label=f"{side} foot name", items=human_names, callback=update_foot_name_callback,
                              user_data=f"human_{side}")
            for side in ("left", "right"):
                dpg.add_combo(label=f"{side} hip name", items=human_names, callback=update_hip_name_callback,
                              user_data=f"human_{side}")
            dpg.add_slider_float(label="foot height", min_value=-0.2, max_value=0.2, default_value=0.0,
                                 callback=update_height_callback, user_data="human_foot")
            dpg.add_slider_float(label="hip height", min_value=-0.2, max_value=0.2, default_value=0.0,
                                 callback=update_height_callback, user_data="human_hip")
        dpg.add_separator()

        # ---- Base shift --------------------------------------------------------
        with dpg.group():
            dpg.add_slider_float(label="base x shift", min_value=-0.2, max_value=0.2, default_value=0.0,
                                 callback=update_base_shift_callback, user_data="base_x_shift")
            dpg.add_slider_float(label="base y shift", min_value=-0.2, max_value=0.2, default_value=0.0,
                                 callback=update_base_shift_callback, user_data="base_y_shift")
        dpg.add_separator()

        # ---- Body ratio --------------------------------------------------------
        with dpg.group(tag="body_ratio_group"):
            with dpg.group(horizontal=True):
                dpg.add_text("Human body ratio")
                dpg.add_button(label="Refresh MuJoCo", callback=refresh_human_model_callback)
                dpg.add_button(label="Add Component", callback=add_body_ratio_callback, user_data=human_names)
            dpg.add_text("Whole body")
            create_three_slider(prefix="", callback=update_body_ratio_callback, min_value=0.5, max_value=1.5, default_value=1.0)
        dpg.add_separator()

        # ---- Body rotation -----------------------------------------------------
        with dpg.group(tag="body_rotate_group"):
            with dpg.group(horizontal=True):
                dpg.add_text("Human body rotation")
                dpg.add_button(label="Add Rotation Component", callback=add_body_rotate_callback, user_data=human_names)
        dpg.add_separator()

        # ---- Tracker dict ------------------------------------------------------
        with dpg.group(tag="tracker_dict_group"):
            dpg.add_text("Build tracker_dict")
            with dpg.group(horizontal=True):
                text_id = dpg.generate_uuid()
                dpg.add_input_text(label="Part name", tag=text_id, hint="Enter part name")
                dpg.add_button(label="Add Part", callback=add_tracker_callback, user_data=text_id)
        dpg.add_separator()

    # ---- Launch DearPyGui ------------------------------------------------------
    dpg.create_viewport(title="MuJoCo Control", width=800, height=600)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

# -----------------------------------------------------------------------------
# CLI entry point (Click)
# -----------------------------------------------------------------------------

@click.command()
@click.option("--robot_name", prompt="Robot name")
@click.option("--motion_type", prompt="Motion type")
@click.option("--motion_path", prompt="Path to motion file")
def main(robot_name: str, motion_type: str, motion_path: str):
    """CLI wrapper - sets up *Aligner*, starts sim thread, launches GUI."""
    global aligner

    aligner = Aligner(source_file_path=motion_path, robot_name=robot_name, generator_type=motion_type)
    aligner.set_base_rotation()

    threading.Thread(target=simulation_loop, daemon=True).start()

    create_gui()

    aligner.viewer.close()
    print(retarget_params)
    
if __name__ == "__main__":
    main()