import React from 'react';
import { Rnd } from 'react-rnd';
import { FullscreenOutlined, FullscreenExitOutlined, MinusOutlined } from '@ant-design/icons';
import { Button } from 'antd';

interface DraggablePanelProps {
  title: string;
  children: React.ReactNode;
  defaultX?: number;
  defaultY?: number;
  defaultWidth?: number | string;
  defaultHeight?: number | string;
  minWidth?: number | string;
  minHeight?: number | string;
  minimizedIndex?: number;
}

const DraggablePanel: React.FC<DraggablePanelProps> = ({
  title,
  children,
  defaultX = 100,
  defaultY = 100,
  defaultWidth = 320,
  defaultHeight = 320,
  minWidth = 280,
  minHeight = 200,
  minimizedIndex = 0,
}) => {
  const [isMaximized, setIsMaximized] = React.useState(false);
  const [isMinimized, setIsMinimized] = React.useState(false);
  const panelId = `panel-${title.replace(/\s+/g, '-')}`;
  const topOffset = 10 + minimizedIndex * 40;

  const handleMaximize = () => {
    setIsMaximized(!isMaximized);
  };

  const handleMinimize = () => {
    setIsMinimized(!isMinimized);
  };

  if (isMinimized) {
    return (
      <Button
        className="minimized-panel-restore"
        style={{ top: `${topOffset}px` }}
        type="text"
        size="small"
        onClick={handleMinimize}
      >
        {title}
      </Button>
    );
  }

  return (
    <Rnd
      default={{
        x: defaultX,
        y: defaultY,
        width: defaultWidth,
        height: defaultHeight,
      }}
      minWidth={minWidth}
      minHeight={minHeight}
      bounds="parent"
      dragHandleClassName="draggable-panel-header"
      enableResizing={!isMaximized}
      enableUserSelectHack={false}
      size={isMaximized ? { width: '100%', height: 'calc(100vh - 80px)' } : undefined}
      position={isMaximized ? { x: 0, y: 60 } : undefined}
      className="draggable-panel"
    >
      <div className="draggable-panel-wrapper" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <div className="draggable-panel-header">
          <span className="draggable-panel-title">{title}</span>
          <div className="draggable-panel-actions">
            <Button
              type="text"
              size="small"
              icon={isMaximized ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
              onClick={handleMaximize}
            />
            <Button
              type="text"
              size="small"
              icon={<MinusOutlined />}
              onClick={handleMinimize}
            />
          </div>
        </div>
        <div className="draggable-panel-content" id={panelId} style={{ flex: 1, overflow: 'auto' }}>
          {children}
        </div>
      </div>
    </Rnd>
  );
};

export default DraggablePanel;
