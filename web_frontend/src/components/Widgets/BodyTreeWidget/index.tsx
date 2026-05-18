import React from 'react';
import { Card, Tree } from 'antd';
import { useTranslation } from 'react-i18next';
import type { DataNode } from 'antd/es/tree';
import { BodyTree, HumanBodyInfo } from '../../../types/config';

interface TreeNodeLocal {
  name: string;
  children?: TreeNodeLocal[];
}

function transformToDataNode(node: TreeNodeLocal): DataNode {
  return {
    title: node.name,
    key: node.name,
    children: node.children?.map(transformToDataNode),
  };
}

function isTreeNodeArray(human: BodyTree['human']): human is TreeNodeLocal[] {
  if (!human) return false;
  if (Array.isArray(human)) return true;
  return false;
}

function isHumanBodyInfo(human: BodyTree['human']): human is HumanBodyInfo {
  if (!human) return false;
  return 'note' in human || 'error' in human;
}

const BodyTreeWidget: React.FC<{ bodyTree: BodyTree }> = ({ bodyTree }) => {
  const { t } = useTranslation();

  const renderHumanTree = () => {
    if (!bodyTree.human) {
      return <div className="text-secondary">{t('configPanel.loading')}</div>;
    }

    if (isTreeNodeArray(bodyTree.human)) {
      return <Tree treeData={bodyTree.human.map(transformToDataNode)} />;
    }

    if (isHumanBodyInfo(bodyTree.human)) {
      if (bodyTree.human.error) {
        return <div className="text-error">{bodyTree.human.error}</div>;
      }
      if (bodyTree.human.note) {
        return <div className="text-secondary">{t(bodyTree.human.note)}</div>;
      }
    }

    return <div className="text-secondary">{t('configPanel.noData')}</div>;
  };

  return (
    <div>
      <Card size="small" title={t('configPanel.card.robotBodies')} style={{ marginBottom: 8 }}>
        {bodyTree.robot && bodyTree.robot.length > 0 ? (
          <Tree treeData={bodyTree.robot.map(transformToDataNode)} />
        ) : (
          <div className="text-secondary">{t('configPanel.loading')}</div>
        )}
      </Card>
      <Card size="small" title={t('configPanel.card.humanBodies')}>
        {renderHumanTree()}
      </Card>
    </div>
  );
};

export default BodyTreeWidget;