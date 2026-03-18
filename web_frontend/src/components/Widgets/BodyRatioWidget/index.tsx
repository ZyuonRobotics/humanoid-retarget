import React from 'react';
import { Slider, InputNumber, Row, Col } from 'antd';
import { useTranslation } from 'react-i18next';
import { RetargetConfig } from '../../../api/client';

interface BodyRatioWidgetProps {
  config: RetargetConfig;
  onChange: (config: RetargetConfig) => void;
}

const BodyRatioWidget: React.FC<BodyRatioWidgetProps> = ({ config, onChange }) => {
  const { t } = useTranslation();

  const updateConfig = (key: keyof RetargetConfig, value: any) => {
    onChange({ ...config, [key]: value });
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <div className="widget-label">{t('configPanel.card.extraBodyRatio')}</div>
        <Row gutter={16}>
          <Col span={8}>
            <div style={{ marginBottom: 4 }}>
              <span className="text-secondary" style={{ fontSize: 12 }}>{t('configPanel.label.x')}</span>
            </div>
            <InputNumber
              style={{ width: '100%' }}
              step={0.01}
              min={0.1}
              value={config.extra_body_ratio[0]}
              onChange={(v) => updateConfig('extra_body_ratio', [v || 1, config.extra_body_ratio[1], config.extra_body_ratio[2]])}
            />
          </Col>
          <Col span={8}>
            <div style={{ marginBottom: 4 }}>
              <span className="text-secondary" style={{ fontSize: 12 }}>{t('configPanel.label.y')}</span>
            </div>
            <InputNumber
              style={{ width: '100%' }}
              step={0.01}
              min={0.1}
              value={config.extra_body_ratio[1]}
              onChange={(v) => updateConfig('extra_body_ratio', [config.extra_body_ratio[0], v || 1, config.extra_body_ratio[2]])}
            />
          </Col>
          <Col span={8}>
            <div style={{ marginBottom: 4 }}>
              <span className="text-secondary" style={{ fontSize: 12 }}>{t('configPanel.label.z')}</span>
            </div>
            <InputNumber
              style={{ width: '100%' }}
              step={0.01}
              min={0.1}
              value={config.extra_body_ratio[2]}
              onChange={(v) => updateConfig('extra_body_ratio', [config.extra_body_ratio[0], config.extra_body_ratio[1], v || 1])}
            />
          </Col>
        </Row>
      </div>

      <div>
        <div className="widget-label">{t('configPanel.card.dampingCost')}</div>
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
    </div>
  );
};

export default BodyRatioWidget;
