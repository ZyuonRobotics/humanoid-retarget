import React, { useState } from 'react';
import { Select, Button, Input, Dropdown } from 'antd';
import {
  SettingOutlined,
  PlayCircleOutlined,
  RobotOutlined,
  FileTextOutlined,
  GlobalOutlined,
  PlusOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useConfigContext } from '../../contexts/ConfigContext';

type ThemeType = 'dark' | 'light' | 'ocean' | 'forest' | 'sunset';

interface TopBarProps {
  activePanel: string;
  onPanelChange: (panel: string) => void;
  theme: ThemeType;
  onThemeChange: (theme: ThemeType) => void;
}

const TopBar: React.FC<TopBarProps> = ({
  activePanel,
  onPanelChange,
  theme,
  onThemeChange,
}) => {
  const { t, i18n } = useTranslation();
  const { robots, selectedRobot, setSelectedRobot, generatorType, setGeneratorType, configs, selectedConfig, setSelectedConfig, handleCreateConfig } = useConfigContext();
  const [isCreatingConfig, setIsCreatingConfig] = useState(false);
  const [newConfigName, setNewConfigName] = useState('');

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

  const themeMenu = {
    items: [
      { key: 'dark', label: t('theme.dark'), onClick: () => onThemeChange('dark') },
      { key: 'light', label: t('theme.light'), onClick: () => onThemeChange('light') },
      { key: 'ocean', label: t('theme.ocean'), onClick: () => onThemeChange('ocean') },
      { key: 'forest', label: t('theme.forest'), onClick: () => onThemeChange('forest') },
      { key: 'sunset', label: t('theme.sunset'), onClick: () => onThemeChange('sunset') },
    ],
  };

  const handleCreateConfigLocal = () => {
    if (newConfigName.trim()) {
      handleCreateConfig(newConfigName.trim());
      setNewConfigName('');
      setIsCreatingConfig(false);
    }
  };

  // Convert robots to options - handle both string[] and RobotInfo[]
  const robotOptions = robots.map((r) =>
    typeof r === 'string' ? { value: r, label: r } : { value: r.name, label: r.name }
  );

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
          onChange={setSelectedRobot}
          style={{ width: 140 }}
          options={robotOptions}
          suffixIcon={<RobotOutlined />}
        />
      </div>

      {/* Generator Type */}
      <div className="topbar-section">
        <Select
          value={generatorType}
          onChange={setGeneratorType}
          style={{ width: 100 }}
          options={[
            { value: 'bvh', label: 'BVH' },
            { value: 'smpl', label: 'SMPL' },
          ]}
        />
      </div>

      {/* Config Selection */}
      <div className="topbar-section">
        {isCreatingConfig ? (
          <Input
            placeholder={t('configPanel.newConfigPlaceholder')}
            value={newConfigName}
            onChange={(e) => setNewConfigName(e.target.value)}
            onPressEnter={handleCreateConfigLocal}
            onBlur={() => {
              if (!newConfigName.trim()) {
                setIsCreatingConfig(false);
              }
            }}
            autoFocus
            style={{ width: 140 }}
          />
        ) : (
          <Select
            value={selectedConfig || undefined}
            onChange={setSelectedConfig}
            style={{ width: 140 }}
            options={configs.map((c) => ({ value: c, label: c }))}
            placeholder={t('configPanel.selectConfigPlaceholder')}
            suffixIcon={<FileTextOutlined />}
          />
        )}
        <Button
          type="text"
          icon={isCreatingConfig ? <CheckOutlined /> : <PlusOutlined />}
          onClick={isCreatingConfig ? handleCreateConfigLocal : () => setIsCreatingConfig(true)}
          style={{ marginLeft: 4 }}
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
        <Dropdown menu={themeMenu} trigger={['click']}>
          <Button type="text">{t('theme.' + theme)}</Button>
        </Dropdown>
        <Dropdown menu={languageMenu} trigger={['click']}>
          <Button type="text" icon={<GlobalOutlined />} />
        </Dropdown>
      </div>
    </div>
  );
};

export default TopBar;