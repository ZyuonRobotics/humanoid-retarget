import React from 'react';
import { Card, Button, InputNumber, Row, Col, Input } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { RetargetConfig } from '../../../api/client';

interface BodyRotateWidgetProps {
  config: RetargetConfig;
  onChange: (config: RetargetConfig) => void;
}

const BodyRotateWidget: React.FC<BodyRotateWidgetProps> = ({ config, onChange }) => {
  const { t } = useTranslation();

  const updateConfig = (key: keyof RetargetConfig, value: any) => {
    onChange({ ...config, [key]: value });
  };

  const addBodyRotate = () => {
    const key = `body_${Object.keys(config.body_rotate_dict).length + 1}`;
    updateConfig('body_rotate_dict', { ...config.body_rotate_dict, [key]: [0, 0, 0] });
  };

  const removeBodyRotate = (key: string) => {
    const newDict = { ...config.body_rotate_dict };
    delete newDict[key];
    updateConfig('body_rotate_dict', newDict);
  };

  return (
    <div>
      {Object.entries(config.body_rotate_dict).map(([key, value]) => (
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
              onClick={() => removeBodyRotate(key)}
            />
          }
          style={{ marginBottom: 8 }}
        >
          <Row gutter={8}>
            <Col span={6}>
              <Input placeholder={t('configPanel.bodyName')} value={key} disabled />
            </Col>
            <Col span={6}>
              <InputNumber
                style={{ width: '100%' }}
                placeholder={t('configPanel.label.x')}
                value={value[0]}
                onChange={(v) =>
                  updateConfig('body_rotate_dict', {
                    ...config.body_rotate_dict,
                    [key]: [v || 0, value[1], value[2]],
                  })
                }
              />
            </Col>
            <Col span={6}>
              <InputNumber
                style={{ width: '100%' }}
                placeholder={t('configPanel.label.y')}
                value={value[1]}
                onChange={(v) =>
                  updateConfig('body_rotate_dict', {
                    ...config.body_rotate_dict,
                    [key]: [value[0], v || 0, value[2]],
                  })
                }
              />
            </Col>
            <Col span={6}>
              <InputNumber
                style={{ width: '100%' }}
                placeholder={t('configPanel.label.z')}
                value={value[2]}
                onChange={(v) =>
                  updateConfig('body_rotate_dict', {
                    ...config.body_rotate_dict,
                    [key]: [value[0], value[1], v || 0],
                  })
                }
              />
            </Col>
          </Row>
        </Card>
      ))}
      <Button type="dashed" icon={<PlusOutlined />} onClick={addBodyRotate} block>
        {t('configPanel.button.addBodyRotation')}
      </Button>
    </div>
  );
};

export default BodyRotateWidget;
