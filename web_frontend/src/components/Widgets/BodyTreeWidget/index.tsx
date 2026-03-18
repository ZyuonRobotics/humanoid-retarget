import React from 'react';
import { Card, Tree } from 'antd';
import { useTranslation } from 'react-i18next';
import type { DataNode } from 'antd/es/tree';

interface BodyTreeWidgetProps {
  bodyTree: {
    robot?: DataNode[];
    human?: {
      note?: string;
      error?: string;
    };
  };
}

const BodyTreeWidget: React.FC<BodyTreeWidgetProps> = ({ bodyTree }) => {
  const { t } = useTranslation();

  return (
    <div>
      <Card size="small" title={t('configPanel.card.robotBodies')} style={{ marginBottom: 8 }}>
        {bodyTree.robot && bodyTree.robot.length > 0 ? (
          <Tree treeData={bodyTree.robot} />
        ) : (
          <div className="text-secondary">{t('configPanel.loading')}</div>
        )}
      </Card>
      <Card size="small" title={t('configPanel.card.humanBodies')}>
        {bodyTree.human ? (
          <div className="text-secondary">{bodyTree.human.note || t('configPanel.noData')}</div>
        ) : (
          <div className="text-secondary">{t('configPanel.loading')}</div>
        )}
      </Card>
    </div>
  );
};

export default BodyTreeWidget;