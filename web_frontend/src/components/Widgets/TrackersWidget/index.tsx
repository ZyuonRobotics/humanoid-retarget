import React, { useState } from 'react';
import { Card, Button, InputNumber, Row, Col, Input, Slider } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { RetargetConfig, TrackerConfig } from '../../../types/config';
import { useConfig } from '../../../hooks/useConfig';
import { useConfigContext } from '../../../contexts/ConfigContext';
import BodyTreeSelectorModal from './BodyTreeSelectorModal';

interface TrackersWidgetProps {
  config: RetargetConfig;
  onChange: (config: RetargetConfig) => void;
}

const TrackersWidget: React.FC<TrackersWidgetProps> = ({ config, onChange }) => {
  const { t } = useTranslation();
  const { updateConfig, addTracker, removeTracker, updateTracker } = useConfig(config, onChange);
  const { bodyTree } = useConfigContext();

  // Track which tracker is being edited with the add pair modal
  const [addPairModalTracker, setAddPairModalTracker] = useState<string | null>(null);

  const maxPairs = (tracker: TrackerConfig) => Math.max(tracker.human.length, tracker.robot.length);

  const handleAddPair = (trackerKey: string, human: string, robot: string) => {
    const tracker = config.tracker_dict[trackerKey];
    updateTracker(trackerKey, {
      ...tracker,
      human: [...tracker.human, human],
      robot: [...tracker.robot, robot],
    });
    setAddPairModalTracker(null);
  };

  const handleUpdatePair = (
    trackerKey: string,
    index: number,
    field: 'human' | 'robot',
    value: string
  ) => {
    const tracker = config.tracker_dict[trackerKey];
    const newHuman = [...tracker.human];
    const newRobot = [...tracker.robot];
    if (field === 'human') {
      newHuman[index] = value;
    } else {
      newRobot[index] = value;
    }
    updateTracker(trackerKey, {
      ...tracker,
      human: newHuman,
      robot: newRobot,
    });
  };

  const handleDeletePair = (trackerKey: string, index: number) => {
    const tracker = config.tracker_dict[trackerKey];
    const newHuman = tracker.human.filter((_, i) => i !== index);
    const newRobot = tracker.robot.filter((_, i) => i !== index);
    updateTracker(trackerKey, {
      ...tracker,
      human: newHuman,
      robot: newRobot,
    });
  };

  const getExistingPairs = (trackerKey: string) => {
    const tracker = config.tracker_dict[trackerKey];
    const pairs: Array<{ human: string; robot: string }> = [];
    const len = Math.max(tracker.human.length, tracker.robot.length);
    for (let i = 0; i < len; i++) {
      if (tracker.human[i] && tracker.robot[i]) {
        pairs.push({ human: tracker.human[i], robot: tracker.robot[i] });
      }
    }
    return pairs;
  };

  return (
    <div>
      {/* Damping Cost Section */}
      <div style={{ marginBottom: 16 }}>
        <div className="widget-label">{t('configPanel.label.dampingCost')}</div>
        <Slider
          min={0}
          max={20}
          step={0.1}
          value={config.damping_cost}
          onChange={(v) => updateConfig('damping_cost', v)}
        />
        <InputNumber
          style={{ width: '100%' }}
          step={0.1}
          min={0}
          value={config.damping_cost}
          onChange={(v) => updateConfig('damping_cost', v)}
        />
      </div>

      {/* Trackers Section */}
      {Object.entries(config.tracker_dict).map(([key, tracker]) => {
        const pairCount = maxPairs(tracker);
        const dataSource = Array.from({ length: Math.max(pairCount, 0) }, (_, i) => ({
          key: `${key}-${i}`,
          index: i,
          trackerKey: key,
          human: tracker.human[i] || '',
          robot: tracker.robot[i] || '',
        }));

        return (
          <Card
            size="small"
            key={key}
            title={key}
            extra={
              <Button
                type="text"
                danger
                size="small"
                icon={<DeleteOutlined />}
                onClick={() => removeTracker(key)}
              />
            }
            style={{ marginBottom: 8 }}
          >
            {dataSource.length > 0 ? (
              <div className="tracker-pairs-table">
                {/* Header */}
                <div className="tracker-pairs-header">
                  <div className="tracker-pair-cell tracker-pair-input">
                    {t('configPanel.label.humanTrackers')}
                  </div>
                  <div className="tracker-pair-cell tracker-pair-input">
                    {t('configPanel.label.robotTrackers')}
                  </div>
                  <div className="tracker-pair-cell tracker-pair-action" />
                </div>
                {/* Rows */}
                {dataSource.map((record) => (
                  <div className="tracker-pairs-row" key={record.key}>
                    <div className="tracker-pair-cell tracker-pair-input">
                      <Input
                        value={record.human}
                        onChange={(e) =>
                          handleUpdatePair(record.trackerKey, record.index, 'human', e.target.value)
                        }
                      />
                    </div>
                    <div className="tracker-pair-cell tracker-pair-input">
                      <Input
                        value={record.robot}
                        onChange={(e) =>
                          handleUpdatePair(record.trackerKey, record.index, 'robot', e.target.value)
                        }
                      />
                    </div>
                    <div className="tracker-pair-cell tracker-pair-action">
                      <Button
                        type="text"
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={() => handleDeletePair(record.trackerKey, record.index)}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ textAlign: 'center', color: 'var(--color-text-tertiary)', padding: 16 }}>
                {t('configPanel.noData')}
              </div>
            )}

            <div style={{ marginTop: 8 }}>
              <Button
                type="dashed"
                size="small"
                icon={<PlusOutlined />}
                onClick={() => setAddPairModalTracker(key)}
                block
              >
                {t('configPanel.button.addPair')}
              </Button>
            </div>

            <div style={{ marginTop: 8 }}>
              <Row gutter={8}>
                <Col span={12}>
                  <div className="widget-label">{t('configPanel.label.positionCost')}</div>
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    step={0.1}
                    value={tracker.position_cost}
                    onChange={(v) => updateTracker(key, { ...tracker, position_cost: v || 1 })}
                  />
                </Col>
                <Col span={12}>
                  <div className="widget-label">{t('configPanel.label.orientationCost')}</div>
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    step={0.1}
                    value={tracker.orientation_cost}
                    onChange={(v) => updateTracker(key, { ...tracker, orientation_cost: v || 1 })}
                  />
                </Col>
              </Row>
            </div>
          </Card>
        );
      })}
      <Button type="dashed" icon={<PlusOutlined />} onClick={addTracker} block>
        {t('configPanel.button.addTrackerGroup')}
      </Button>

      {/* Add Pair Modal */}
      {addPairModalTracker && (
        <BodyTreeSelectorModal
          open={addPairModalTracker !== null}
          bodyTree={bodyTree}
          existingPairs={getExistingPairs(addPairModalTracker)}
          onCancel={() => setAddPairModalTracker(null)}
          onConfirm={(human, robot) => handleAddPair(addPairModalTracker, human, robot)}
        />
      )}
    </div>
  );
};

export default TrackersWidget;
