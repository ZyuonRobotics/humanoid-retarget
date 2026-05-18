import { useCallback } from 'react';
import { RetargetConfig, TrackerConfig } from '../types/config';

export function useConfig(
  config: RetargetConfig,
  onChange: (config: RetargetConfig) => void
) {
  const updateConfig = useCallback(
    (key: keyof RetargetConfig, value: unknown) => {
      onChange({ ...config, [key]: value });
    },
    [config, onChange]
  );

  const addTracker = useCallback(() => {
    const existingKeys = Object.keys(config.tracker_dict);
    let index = 1;
    let key = `tracker_${index}`;
    while (existingKeys.includes(key)) {
      index++;
      key = `tracker_${index}`;
    }
    updateConfig('tracker_dict', {
      ...config.tracker_dict,
      [key]: { human: [], robot: [], position_cost: 1.0, orientation_cost: 1.0 } as TrackerConfig,
    });
  }, [config.tracker_dict, updateConfig]);

  const removeTracker = useCallback(
    (key: string) => {
      const newDict = { ...config.tracker_dict };
      delete newDict[key];
      updateConfig('tracker_dict', newDict);
    },
    [config.tracker_dict, updateConfig]
  );

  const updateTracker = useCallback(
    (key: string, tracker: TrackerConfig) => {
      updateConfig('tracker_dict', { ...config.tracker_dict, [key]: tracker });
    },
    [config.tracker_dict, updateConfig]
  );

  const addBodyRotate = useCallback(
    (key?: string) => {
      let bodyKey = key;
      if (!bodyKey) {
        const existingKeys = Object.keys(config.body_rotate_dict);
        let index = 1;
        bodyKey = `body_${index}`;
        while (existingKeys.includes(bodyKey)) {
          index++;
          bodyKey = `body_${index}`;
        }
      }
      updateConfig('body_rotate_dict', { ...config.body_rotate_dict, [bodyKey]: [0, 0, 0] });
    },
    [config.body_rotate_dict, updateConfig]
  );

  const removeBodyRotate = useCallback(
    (key: string) => {
      const newDict = { ...config.body_rotate_dict };
      delete newDict[key];
      updateConfig('body_rotate_dict', newDict);
    },
    [config.body_rotate_dict, updateConfig]
  );

  const updateBodyRotate = useCallback(
    (key: string, value: number[]) => {
      updateConfig('body_rotate_dict', { ...config.body_rotate_dict, [key]: value });
    },
    [config.body_rotate_dict, updateConfig]
  );

  const addRelativeBodyRatio = useCallback(
    (key?: string) => {
      let bodyKey = key;
      if (!bodyKey) {
        const existingKeys = Object.keys(config.relative_body_ratio_dict);
        let index = 1;
        bodyKey = `body_${index}`;
        while (existingKeys.includes(bodyKey)) {
          index++;
          bodyKey = `body_${index}`;
        }
      }
      updateConfig('relative_body_ratio_dict', {
        ...config.relative_body_ratio_dict,
        [bodyKey]: [1, 1, 1],
      });
    },
    [config.relative_body_ratio_dict, updateConfig]
  );

  const removeRelativeBodyRatio = useCallback(
    (key: string) => {
      const newDict = { ...config.relative_body_ratio_dict };
      delete newDict[key];
      updateConfig('relative_body_ratio_dict', newDict);
    },
    [config.relative_body_ratio_dict, updateConfig]
  );

  const updateRelativeBodyRatio = useCallback(
    (key: string, value: number[]) => {
      updateConfig('relative_body_ratio_dict', { ...config.relative_body_ratio_dict, [key]: value });
    },
    [config.relative_body_ratio_dict, updateConfig]
  );

  return {
    updateConfig,
    addTracker,
    removeTracker,
    updateTracker,
    addBodyRotate,
    removeBodyRotate,
    updateBodyRotate,
    addRelativeBodyRatio,
    removeRelativeBodyRatio,
    updateRelativeBodyRatio,
  };
}
