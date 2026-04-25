import React, { useState, useMemo } from 'react';
import { Modal, Select, Space, Typography } from 'antd';
import { useTranslation } from 'react-i18next';
import { BodyTree, BodyTreeNode } from '../../../types/config';

const { Text } = Typography;

interface BodyTreeSelectorModalProps {
  open: boolean;
  bodyTree: BodyTree;
  existingPairs: Array<{ human: string; robot: string }>;
  onCancel: () => void;
  onConfirm: (human: string, robot: string) => void;
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

function flattenTreeNames(nodes: BodyTreeNode[] | TreeNodeLocal[]): string[] {
  const names: string[] = [];
  for (const node of nodes) {
    names.push(node.name);
    if (node.children) {
      names.push(...flattenTreeNames(node.children));
    }
  }
  return names;
}

const BodyTreeSelectorModal: React.FC<BodyTreeSelectorModalProps> = ({
  open,
  bodyTree,
  existingPairs,
  onCancel,
  onConfirm,
}) => {
  const { t } = useTranslation();
  const [selectedHuman, setSelectedHuman] = useState<string | null>(null);
  const [selectedRobot, setSelectedRobot] = useState<string | null>(null);

  const humanBodyNames = useMemo(() => {
    if (!bodyTree.human) return [];

    if (isTreeNodeArray(bodyTree.human)) {
      return flattenTreeNames(bodyTree.human);
    }

    // If it's HumanBodyInfo (error/note), return empty array
    return [];
  }, [bodyTree.human]);

  const robotBodyNames = useMemo(() => {
    if (!bodyTree.robot) return [];
    return flattenTreeNames(bodyTree.robot);
  }, [bodyTree.robot]);

  const availableHumanNames = humanBodyNames.filter(
    (name) => !existingPairs.some((p) => p.human === name)
  );

  const availableRobotNames = robotBodyNames.filter(
    (name) => !existingPairs.some((p) => p.robot === name)
  );

  const handleConfirm = () => {
    if (selectedHuman && selectedRobot) {
      onConfirm(selectedHuman, selectedRobot);
      setSelectedHuman(null);
      setSelectedRobot(null);
    }
  };

  const handleCancel = () => {
    setSelectedHuman(null);
    setSelectedRobot(null);
    onCancel();
  };

  return (
    <Modal
      open={open}
      title={t('configPanel.modal.addPair')}
      onCancel={handleCancel}
      onOk={handleConfirm}
      okText={t('common.confirm')}
      cancelText={t('common.cancel')}
      okButtonProps={{ disabled: !selectedHuman || !selectedRobot }}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%', marginTop: 16 }}>
        <div>
          <Text strong>{t('configPanel.label.humanTrackers')}</Text>
          <Select
            style={{ width: '100%', marginTop: 4 }}
            placeholder={t('configPanel.modal.selectHumanBody')}
            value={selectedHuman}
            onChange={setSelectedHuman}
            options={availableHumanNames.map((name) => ({ label: name, value: name }))}
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
          />
        </div>
        <div>
          <Text strong>{t('configPanel.label.robotTrackers')}</Text>
          <Select
            style={{ width: '100%', marginTop: 4 }}
            placeholder={t('configPanel.modal.selectRobotBody')}
            value={selectedRobot}
            onChange={setSelectedRobot}
            options={availableRobotNames.map((name) => ({ label: name, value: name }))}
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
          />
        </div>
      </Space>
    </Modal>
  );
};

export default BodyTreeSelectorModal;
