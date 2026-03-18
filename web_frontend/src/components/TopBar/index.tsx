import React from 'react';
import { Select, Button, Dropdown } from 'antd';
import {
  SettingOutlined,
  PlayCircleOutlined,
  RobotOutlined,
  FileTextOutlined,
  GlobalOutlined,
  SunOutlined,
  MoonOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { RobotInfo } from '../../api/client';

interface TopBarProps {
  robots: RobotInfo[];
  selectedRobot: string;
  onRobotChange: (robot: string) => void;
  generatorType: string;
  onGeneratorTypeChange: (type: string) => void;
  configs: string[];
  selectedConfig: string;
  onConfigChange: (config: string) => void;
  activePanel: string;
  onPanelChange: (panel: string) => void;
  theme: 'light' | 'dark';
  onThemeChange: (theme: 'light' | 'dark') => void;
}

const TopBar: React.FC<TopBarProps> = ({
  robots,
  selectedRobot,
  onRobotChange,
  generatorType,
  onGeneratorTypeChange,
  configs,
  selectedConfig,
  onConfigChange,
  activePanel,
  onPanelChange,
  theme,
  onThemeChange,
}) => {
  const { t, i18n } = useTranslation();

  const changeLanguage = (lang: string) => {
    localStorage.setItem('i18nextLng', lang);
    i18n.changeLanguage(lang);
  };

  const languageMenu = {
    items: [
      { key: 'en', label: t('language.en'), onClick: () => changeLanguage('en') },
      { key: 'zh', label: t('language.zh'), onClick: () => changeLanguage('zh') },
    ],
  };

  return (
    <div className="topbar">
      {/* Logo Section */}
      <div className="topbar-section">
        <div className="topbar-logo">
          <RobotOutlined />
          <span>{t('app.title')}</span>
        </div>
      </div>

      <div className="topbar-divider" />

      {/* Robot Selection */}
      <div className="topbar-section">
        <Select
          value={selectedRobot}
          onChange={onRobotChange}
          style={{ width: 140 }}
          options={robots.map((r) => ({ value: r, label: r }))}
          suffixIcon={<RobotOutlined />}
        />
      </div>

      {/* Generator Type */}
      <div className="topbar-section">
        <Select
          value={generatorType}
          onChange={onGeneratorTypeChange}
          style={{ width: 100 }}
          options={[
            { value: 'bvh', label: 'BVH' },
            { value: 'smpl', label: 'SMPL' },
          ]}
        />
      </div>

      {/* Config Selection */}
      <div className="topbar-section">
        <Select
          value={selectedConfig}
          onChange={onConfigChange}
          style={{ width: 140 }}
          options={configs.map((c) => ({ value: c, label: c }))}
          suffixIcon={<FileTextOutlined />}
        />
      </div>

      <div className="topbar-divider" />

      {/* Panel Toggles */}
      <div className="topbar-section">
        <Button
          type={activePanel === 'config' ? 'primary' : 'text'}
          icon={<SettingOutlined />}
          onClick={() => onPanelChange('config')}
        >
          {t('menu.configuration')}
        </Button>
        <Button
          type={activePanel === 'viewer' ? 'primary' : 'text'}
          icon={<PlayCircleOutlined />}
          onClick={() => onPanelChange('viewer')}
        >
          {t('menu.3dViewer')}
        </Button>
      </div>

      <div className="topbar-divider" />

      {/* Theme & Language */}
      <div className="topbar-section">
        <Button
          type="text"
          icon={theme === 'dark' ? <SunOutlined /> : <MoonOutlined />}
          onClick={() => onThemeChange(theme === 'dark' ? 'light' : 'dark')}
        />
        <Dropdown menu={languageMenu} trigger={['click']}>
          <Button type="text" icon={<GlobalOutlined />} />
        </Dropdown>
      </div>
    </div>
  );
};

export default TopBar;
