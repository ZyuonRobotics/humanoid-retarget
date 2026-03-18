import React from 'react';
import { Slider, InputNumber, Row, Col } from 'antd';
import { useTranslation } from 'react-i18next';
import { RetargetConfig } from '../../../types/config';
import { useConfig } from '../../../hooks/useConfig';

interface BaseSettingsWidgetProps {
  config: RetargetConfig;
  onChange: (config: RetargetConfig) => void;
}

const BaseSettingsWidget: React.FC<BaseSettingsWidgetProps> = ({
  config,
  onChange,
}) => {
  const { t } = useTranslation();
  const { updateConfig } = useConfig(config, onChange);

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <div className="widget-label">{t('configPanel.card.robotSettings')}</div>
        <Row gutter={16}>
          <Col span={12}>
            <div style={{ marginBottom: 8 }}>
              <span className="text-secondary" style={{ fontSize: 12 }}>{t('configPanel.label.baseLinkXOffset')}</span>
            </div>
            <Slider
              min={-1}
              max={1}
              step={0.01}
              value={config.base_x_shift}
              onChange={(v) => updateConfig('base_x_shift', v)}
            />
            <InputNumber
              style={{ width: '100%' }}
              step={0.01}
              value={config.base_x_shift}
              onChange={(v) => updateConfig('base_x_shift', v)}
            />
          </Col>
          <Col span={12}>
            <div style={{ marginBottom: 8 }}>
              <span className="text-secondary" style={{ fontSize: 12 }}>{t('configPanel.label.baseLinkYOffset')}</span>
            </div>
            <Slider
              min={-1}
              max={1}
              step={0.01}
              value={config.base_y_shift}
              onChange={(v) => updateConfig('base_y_shift', v)}
            />
            <InputNumber
              style={{ width: '100%' }}
              step={0.01}
              value={config.base_y_shift}
              onChange={(v) => updateConfig('base_y_shift', v)}
            />
          </Col>
        </Row>
      </div>

      <div style={{ marginBottom: 16 }}>
        <div className="widget-label">{t('configPanel.label.baseLinkRotation')}</div>
        <Row gutter={16}>
          <Col span={8}>
            <div style={{ marginBottom: 4 }}>
              <span className="text-secondary" style={{ fontSize: 12 }}>{t('configPanel.label.x')}</span>
            </div>
            <InputNumber
              style={{ width: '100%' }}
              step={1}
              value={config.base_rotation[0]}
              onChange={(v) => updateConfig('base_rotation', [v || 0, config.base_rotation[1], config.base_rotation[2]])}
            />
          </Col>
          <Col span={8}>
            <div style={{ marginBottom: 4 }}>
              <span className="text-secondary" style={{ fontSize: 12 }}>{t('configPanel.label.y')}</span>
            </div>
            <InputNumber
              style={{ width: '100%' }}
              step={1}
              value={config.base_rotation[1]}
              onChange={(v) => updateConfig('base_rotation', [config.base_rotation[0], v || 0, config.base_rotation[2]])}
            />
          </Col>
          <Col span={8}>
            <div style={{ marginBottom: 4 }}>
              <span className="text-secondary" style={{ fontSize: 12 }}>{t('configPanel.label.z')}</span>
            </div>
            <InputNumber
              style={{ width: '100%' }}
              step={1}
              value={config.base_rotation[2]}
              onChange={(v) => updateConfig('base_rotation', [config.base_rotation[0], config.base_rotation[1], v || 0])}
            />
          </Col>
        </Row>
      </div>
    </div>
  );
};

export default BaseSettingsWidget;