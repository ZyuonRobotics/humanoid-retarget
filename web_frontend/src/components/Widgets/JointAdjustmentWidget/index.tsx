import React from 'react';
import { Card, Button, InputNumber, Row, Col, Select } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

interface JointAdjustmentWidgetProps {
  jointAdjustments: Record<string, number[]>;
  availableJoints: string[];
  onChange: (adjustments: Record<string, number[]>) => void;
}

const JointAdjustmentWidget: React.FC<JointAdjustmentWidgetProps> = ({
  jointAdjustments,
  availableJoints,
  onChange,
}) => {
  const { t } = useTranslation();

  const addJointAdjustment = (jointName: string) => {
    onChange({
      ...jointAdjustments,
      [jointName]: [0, 0, 0],
    });
  };

  const removeJointAdjustment = (jointName: string) => {
    const newAdjustments = { ...jointAdjustments };
    delete newAdjustments[jointName];
    onChange(newAdjustments);
  };

  const updateJointAdjustment = (jointName: string, value: number[]) => {
    onChange({
      ...jointAdjustments,
      [jointName]: value,
    });
  };

  const availableJointOptions = availableJoints.filter(
    (name) => !jointAdjustments[name]
  );

  return (
    <div>
      <div className="widget-label">{t('player.jointAdjustments')}</div>
      {Object.entries(jointAdjustments).map(([jointName, value]) => (
        <Card
          size="small"
          key={jointName}
          title={jointName}
          extra={
            <Button
              type="text"
              danger
              size="small"
              icon={<DeleteOutlined />}
              onClick={() => removeJointAdjustment(jointName)}
            />
          }
          style={{ marginBottom: 8 }}
        >
          <Row gutter={8}>
            <Col span={8}>
              <InputNumber
                style={{ width: '100%' }}
                placeholder={t('configPanel.label.x')}
                value={value[0]}
                onChange={(v) => updateJointAdjustment(jointName, [v || 0, value[1], value[2]])}
              />
            </Col>
            <Col span={8}>
              <InputNumber
                style={{ width: '100%' }}
                placeholder={t('configPanel.label.y')}
                value={value[1]}
                onChange={(v) => updateJointAdjustment(jointName, [value[0], v || 0, value[2]])}
              />
            </Col>
            <Col span={8}>
              <InputNumber
                style={{ width: '100%' }}
                placeholder={t('configPanel.label.z')}
                value={value[2]}
                onChange={(v) => updateJointAdjustment(jointName, [value[0], value[1], v || 0])}
              />
            </Col>
          </Row>
        </Card>
      ))}
      <Row gutter={8}>
        <Col span={24}>
          <Select
            style={{ width: '100%' }}
            placeholder={t('player.selectJointName')}
            onChange={(value) => {
              addJointAdjustment(value);
            }}
            options={availableJointOptions.map((name) => ({ value: name, label: name }))}
            disabled={availableJointOptions.length === 0}
          />
        </Col>
      </Row>
    </div>
  );
};

export default JointAdjustmentWidget;
