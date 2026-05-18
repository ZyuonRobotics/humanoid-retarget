import React from 'react';
import { HelpSection } from '../../helper/helpContent';

interface SidebarProps {
  sections: HelpSection[];
  selectedSection: string;
  selectedSubsection: string;
  onSelect: (sectionId: string, subsectionId: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sections,
  selectedSection,
  selectedSubsection,
  onSelect,
}) => {
  return (
    <div className="help-sidebar">
      {sections.map((section, index) => (
        <div key={section.id} className="help-section-group">
          <div className="help-section-title">
            {index + 1}. {section.title}
          </div>
          <div className="help-subsection-list">
            {section.subsections.map((sub, subIndex) => (
              <div
                key={sub.id}
                className={`help-subsection-item ${
                  selectedSection === section.id && selectedSubsection === sub.id
                    ? 'active'
                    : ''
                }`}
                onClick={() => onSelect(section.id, sub.id)}
              >
                {index + 1}.{subIndex + 1} {sub.title}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};
