import React, { useMemo } from 'react';
import { Card, Button, InputNumber, Row, Col, Select } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { RetargetConfig, BodyTree } from '../../../types/config';
import { useConfig } from '../../../hooks/useConfig';

interface HumanSettingsWidgetProps {
  config: RetargetConfig;
  onChange: (config: RetargetConfig) => void;
  bodyTree: BodyTree;
}

interface TreeNodeLocal {
  name: string;
  children?: TreeNodeLocal[];
}

function isTreeNodeArray(human: BodyTree['human']): human is TreeNodeLocal[] {
  if (!human) return false;
  if (Array.isArray(human)) return true;
  return false;
}

function flattenBodyNames(nodes: TreeNodeLocal[]): string[] {
  const names: string[] = [];
  for (const node of nodes) {
    names.push(node.name);
    if (node.children) {
      names.push(...flattenBodyNames(node.children));
    }
  }
  return names;
}

const HumanSettingsWidget: React.FC<HumanSettingsWidgetProps> = ({ config, onChange, bodyTree }) => {
  const { t } = useTranslation();
  const { updateConfig, addBodyRotate, removeBodyRotate, updateBodyRotate, addRelativeBodyRatio, removeRelativeBodyRatio, updateRelativeBodyRatio } = useConfig(config, onChange);

  const humanBodyNames = useMemo(() => {
    if (isTreeNodeArray(bodyTree.human)) {
      return flattenBodyNames(bodyTree.human);
    }
    return [];
  }, [bodyTree.human]);

  const availableRotateBodies = useMemo(
    () => humanBodyNames.filter((name) => !config.body_rotate_dict[name]),
    [humanBodyNames, config.body_rotate_dict]
  );

  const availableRatioBodies = useMemo(
    () => humanBodyNames.filter((name) => !config.relative_body_ratio_dict[name]),
    [humanBodyNames, config.relative_body_ratio_dict]
  );

  return (
    <div>
      {/* Human Body Rotation Section */}
      <div style={{ marginBottom: 16 }}>
        <div className="widget-label">{t('configPanel.card.bodyRotate')}</div>
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
              <Col span={8}>
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder={t('configPanel.label.x')}
                  value={value[0]}
                  onChange={(v) => updateBodyRotate(key, [v || 0, value[1], value[2]])}
                />
              </Col>
              <Col span={8}>
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder={t('configPanel.label.y')}
                  value={value[1]}
                  onChange={(v) => updateBodyRotate(key, [value[0], v || 0, value[2]])}
                />
              </Col>
              <Col span={8}>
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder={t('configPanel.label.z')}
                  value={value[2]}
                  onChange={(v) => updateBodyRotate(key, [value[0], value[1], v || 0])}
                />
              </Col>
            </Row>
          </Card>
        ))}
        <Row gutter={8}>
          <Col span={24}>
            <Select
              style={{ width: '100%' }}
              placeholder={t('configPanel.bodyName')}
              onChange={(value) => {
                addBodyRotate(value);
              }}
              options={availableRotateBodies.map((name) => ({ value: name, label: name }))}
              disabled={availableRotateBodies.length === 0}
            />
          </Col>
        </Row>
      </div>

      {/* Global Body Ratio Section */}
      <div style={{ marginBottom: 16 }}>
        <div className="widget-label">{t('configPanel.label.globalBodyRatio')}</div>
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

      {/* Relative Body Ratio Section */}
      <div>
        <div className="widget-label">{t('configPanel.label.relativeBodyRatio')}</div>
        {Object.entries(config.relative_body_ratio_dict).map(([key, value]) => (
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
                onClick={() => removeRelativeBodyRatio(key)}
              />
            }
            style={{ marginBottom: 8 }}
          >
            <Row gutter={8}>
              <Col span={8}>
                <InputNumber
                  style={{ width: '100%' }}
                  step={0.01}
                  min={0.1}
                  placeholder={t('configPanel.label.x')}
                  value={value[0]}
                  onChange={(v) => updateRelativeBodyRatio(key, [v || 1, value[1], value[2]])}
                />
              </Col>
              <Col span={8}>
                <InputNumber
                  style={{ width: '100%' }}
                  step={0.01}
                  min={0.1}
                  placeholder={t('configPanel.label.y')}
                  value={value[1]}
                  onChange={(v) => updateRelativeBodyRatio(key, [value[0], v || 1, value[2]])}
                />
              </Col>
              <Col span={8}>
                <InputNumber
                  style={{ width: '100%' }}
                  step={0.01}
                  min={0.1}
                  placeholder={t('configPanel.label.z')}
                  value={value[2]}
                  onChange={(v) => updateRelativeBodyRatio(key, [value[0], value[1], v || 1])}
                />
              </Col>
            </Row>
          </Card>
        ))}
        <Row gutter={8}>
          <Col span={24}>
            <Select
              style={{ width: '100%' }}
              placeholder={t('configPanel.bodyName')}
              onChange={(value) => {
                addRelativeBodyRatio(value);
              }}
              options={availableRatioBodies.map((name) => ({ value: name, label: name }))}
              disabled={availableRatioBodies.length === 0}
            />
          </Col>
        </Row>
      </div>
    </div>
  );
};

export default HumanSettingsWidget;