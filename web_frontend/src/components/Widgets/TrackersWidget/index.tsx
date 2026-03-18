import React from 'react';
import { Card, Button, InputNumber, Row, Col, Input } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { RetargetConfig, TrackerConfig } from '../../../types/config';
import { useConfig } from '../../../hooks/useConfig';

interface TrackersWidgetProps {
  config: RetargetConfig;
  onChange: (config: RetargetConfig) => void;
}

const TrackersWidget: React.FC<TrackersWidgetProps> = ({ config, onChange }) => {
  const { t } = useTranslation();
  const { updateConfig, addTracker, removeTracker, updateTracker } = useConfig(config, onChange);

  return (
    <div>
      {Object.entries(config.tracker_dict).map(([key, tracker]) => (
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
          <div style={{ marginBottom: 8 }}>
            <div className="widget-label">{t('configPanel.label.humanTrackers')}</div>
            <Input.TextArea
              placeholder={t('configPanel.humanTrackerPlaceholder')}
              value={tracker.human.join(', ')}
              onChange={(e) =>
                updateTracker(key, {
                  ...tracker,
                  human: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                })
              }
              rows={2}
            />
          </div>
          <div style={{ marginBottom: 8 }}>
            <div className="widget-label">{t('configPanel.label.robotTrackers')}</div>
            <Input.TextArea
              placeholder={t('configPanel.robotTrackerPlaceholder')}
              value={tracker.robot.join(', ')}
              onChange={(e) =>
                updateTracker(key, {
                  ...tracker,
                  robot: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                })
              }
              rows={2}
            />
          </div>
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
        </Card>
      ))}
      <Button type="dashed" icon={<PlusOutlined />} onClick={addTracker} block>
        {t('configPanel.button.addTracker')}
      </Button>
    </div>
  );
};

export default TrackersWidget;
