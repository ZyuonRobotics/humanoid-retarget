import React from 'react';
import { Card, Tree } from 'antd';
import { useTranslation } from 'react-i18next';

interface BodyTreeWidgetProps {
  bodyTree: {
    robot?: {
      bodies?: string[];
    };
    human?: {
      note?: string;
    };
  };
}

const BodyTreeWidget: React.FC<BodyTreeWidgetProps> = ({ bodyTree }) => {
  const { t } = useTranslation();

  return (
    <div>
      <Card size="small" title={t('configPanel.card.robotBodies')} style={{ marginBottom: 8 }}>
        {bodyTree.robot?.bodies ? (
          <Tree
            treeData={bodyTree.robot.bodies.map((name: string) => ({
              title: name,
              key: name,
            }))}
            defaultExpandAll
          />
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
