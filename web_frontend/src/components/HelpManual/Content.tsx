import React from 'react';
import { HelpSection, HelpSubsection } from '../../helper/helpContent';

interface ContentProps {
  section: HelpSection | undefined;
  subsection: HelpSubsection | undefined;
}

export const Content: React.FC<ContentProps> = ({ section, subsection }) => {
  if (!section || !subsection) {
    return (
      <div className="help-content-empty">
        <p>请从左侧目录选择一个章节</p>
      </div>
    );
  }

  return (
    <div className="help-content">
      <h2 className="help-content-title">{subsection.title}</h2>
      <div className="help-content-body">{subsection.content}</div>
    </div>
  );
};
