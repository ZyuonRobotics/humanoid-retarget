import React, { useState, useMemo } from 'react';
import { Modal } from 'antd';
import { Sidebar } from './Sidebar';
import { Content } from './Content';
import { helpContent } from '../../helper/helpContent';
import './HelpManual.css';

interface HelpManualProps {
  open: boolean;
  onClose: () => void;
}

export const HelpManual: React.FC<HelpManualProps> = ({ open, onClose }) => {
  const [selectedSection, setSelectedSection] = useState<string>('quick-start');
  const [selectedSubsection, setSelectedSubsection] = useState<string>('overview');

  const currentSection = useMemo(() => {
    return helpContent.find((section) => section.id === selectedSection);
  }, [selectedSection]);

  const currentSubsection = useMemo(() => {
    return currentSection?.subsections.find((sub) => sub.id === selectedSubsection);
  }, [currentSection, selectedSubsection]);

  const handleSelect = (sectionId: string, subsectionId: string) => {
    setSelectedSection(sectionId);
    setSelectedSubsection(subsectionId);
  };

  return (
    <Modal
      title="帮助手册"
      open={open}
      onCancel={onClose}
      footer={null}
      width="90vw"
      style={{ top: 20 }}
      bodyStyle={{ height: 'calc(90vh - 110px)', padding: 0 }}
      destroyOnClose={false}
    >
      <div className="help-manual-container">
        <Sidebar
          sections={helpContent}
          selectedSection={selectedSection}
          selectedSubsection={selectedSubsection}
          onSelect={handleSelect}
        />
        <Content section={currentSection} subsection={currentSubsection} />
      </div>
    </Modal>
  );
};
