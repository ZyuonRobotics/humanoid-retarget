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
}) => {
  const [isMaximized, setIsMaximized] = React.useState(false);

  const handleMaximize = () => {
    setIsMaximized(!isMaximized);
  };

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
              onClick={() => {
                const element = document.getElementById(`panel-${title.replace(/\s+/g, '-')}`);
                if (element) {
                  element.style.display = 'none';
                }
              }}
            />
          </div>
        </div>
        <div className="draggable-panel-content" id={`panel-${title.replace(/\s+/g, '-')}`} style={{ flex: 1, overflow: 'auto' }}>
          {children}
        </div>
      </div>
    </Rnd>
  );
};

export default DraggablePanel;
