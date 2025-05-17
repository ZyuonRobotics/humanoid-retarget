from humanoid_retargeting.utils.retarget_params import RetargetParams, FootParams, TrackerConfig

def build_test_obj():
    return RetargetParams(
        robot_foot=FootParams(left_name=1.0, right_name=1.0, height=0.1),
        human_foot=FootParams(left_name=0.9, right_name=0.9, height=0.08),
        whole_body_ratio=[1.0, 1.0, 1.0],
        body_ratio_dict={"arm": 1.2, "leg": 0.9},
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
