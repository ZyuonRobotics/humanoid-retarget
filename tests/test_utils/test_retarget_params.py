from humanoid_retargeting.utils.retarget_config import RetargetConfig, TrackerConfig

def build_test_obj():
    return RetargetConfig(
        base_x_shift=0.0,
        base_y_shift=0.0,
        extra_body_ratio=[1.0, 1.0, 1.0],
        relative_body_ratio_dict={"arm": 1.2, "leg": 0.9},
        tracker_dict={
            "main_tracker": TrackerConfig(
                human=["left_shoulder", "right_shoulder"],
                robot=["left_arm", "right_arm"],
                position_cost=1.0,
                orientation_cost=0.5
            )
        }
    )


def test_retarget_config_to_yaml(tmp_path):
    config = build_test_obj()
    config.to_yaml(str(tmp_path / "retarget_config.yaml"))


def test_retarget_config_from_yaml(tmp_path):
    config = build_test_obj()
    yaml_path = tmp_path / "retarget_config.yaml"
    config.to_yaml(str(yaml_path))
    loaded_config = RetargetConfig.from_yaml(str(yaml_path))
    assert loaded_config == config
