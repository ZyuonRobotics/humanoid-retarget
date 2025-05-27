from humanoid_retargeting.utils.retarget_params import RetargetParams, FootParams, TrackerConfig

def build_test_obj():
    return RetargetParams(
        robot_foot=FootParams(left_name="l6left", right_name="l6right", offset=0.1),
        human_foot=FootParams(left_name="l6left", right_name="l6right", offset=0.08),
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


def test_retarget_params_to_json():
    params = build_test_obj()
    params.to_json("retarget_params.json")


def test_retarget_params_from_json():
    params = build_test_obj()
    params.to_json("retarget_params.json")
    loaded_params = RetargetParams.from_json("retarget_params.json")
    assert loaded_params == params
