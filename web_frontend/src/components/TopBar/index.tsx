import React, { useState, useEffect } from 'react';
import { Select, Button, Input, Dropdown, Spin } from 'antd';
import {
  SettingOutlined,
  PlayCircleOutlined,
  RobotOutlined,
  FileTextOutlined,
  GlobalOutlined,
  PlusOutlined,
  CheckOutlined,
  FileOutlined,
  FolderOutlined,
  CloseOutlined,
  RightOutlined,
  SaveOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useConfigContext } from '../../contexts/ConfigContext';
import { useMotionContext } from '../../contexts/MotionContext';
import { modelApi, MotionTreeNode, MotionFileInfo } from '../../api/client';
import './FileSelector.css';

interface FolderInfo {
  name: string;
  node: MotionTreeNode;
  path: string[];
}

interface ColumnData {
  path: string[];
  folders: FolderInfo[];
  files: MotionFileInfo[];
}

type ThemeType = 'dark' | 'light' | 'ocean' | 'forest' | 'sunset';

interface TopBarProps {
  activePanel: string;
  onPanelChange: (panel: string) => void;
  theme: ThemeType;
  onThemeChange: (theme: ThemeType) => void;
  onPlayerMotionChange?: (type: 'robot' | 'human', robotName: string, motionFile: string, generatorType?: string) => void;
}

const TopBar: React.FC<TopBarProps> = ({
  activePanel,
  onPanelChange,
  theme,
  onThemeChange,
  onPlayerMotionChange,
}) => {
  const { t, i18n } = useTranslation();
  const {
    robots,
    selectedRobot,
    setSelectedRobot,
    generatorType,
    setGeneratorType,
    selectedMotionFile,
    setSelectedMotionFile,
    configs,
    selectedConfig,
    setSelectedConfig,
    handleCreateConfig,
    loadBodyTree,
    saveConfig,
    handleDeleteConfig,
    saving,
  } = useConfigContext();
  const { setSelectedMotion } = useMotionContext();
  const [isCreatingConfig, setIsCreatingConfig] = useState(false);
  const [newConfigName, setNewConfigName] = useState('');

  // Player mode state
  const [playerMotionType, setPlayerMotionType] = useState<'robot' | 'human'>('robot');
  const [selectedRobotMotion, setSelectedRobotMotion] = useState<string>('');
  const [selectedHumanFormat, setSelectedHumanFormat] = useState<'smpl' | 'bvh'>('bvh');
  const [selectedHumanMotion, setSelectedHumanMotion] = useState<string>('');
  const [retargetedMotions, setRetargetedMotions] = useState<string[]>([]);
  const [retargetedLoading, setRetargetedLoading] = useState(false);

  // File selector popover state
  const [fileSelectorOpen, setFileSelectorOpen] = useState(false);
  const [motionTree, setMotionTree] = useState<Record<string, MotionTreeNode> | null>(null);
  const [columns, setColumns] = useState<ColumnData[]>([]);
  const [treeLoading, setTreeLoading] = useState(false);

  // Load retargeted motions when entering player mode
  useEffect(() => {
    if (activePanel === 'player') {
      setRetargetedLoading(true);
      modelApi.listRetargetedMotions()
        .then(setRetargetedMotions)
        .catch(console.error)
        .finally(() => setRetargetedLoading(false));
    }
  }, [activePanel]);
  useEffect(() => {
    if (fileSelectorOpen && !motionTree) {
      loadMotionTree();
    }
  }, [fileSelectorOpen]);

  // Initialize columns when motionTree or generatorType changes
  useEffect(() => {
    // Use selectedHumanFormat in player mode, generatorType in retargeter mode
    const currentGenType = activePanel === 'player' ? selectedHumanFormat : generatorType;
    if (motionTree && motionTree[currentGenType]) {
      const rootNode = motionTree[currentGenType];
      const rootColumn: ColumnData = {
        path: [],
        folders: Object.entries(rootNode.subdirs).map(([name, node]) => ({
          name,
          node,
          path: [name]
        })),
        files: rootNode.motions
      };
      setColumns([rootColumn]);
    }
  }, [motionTree, generatorType, selectedHumanFormat, activePanel]);

  const loadMotionTree = async () => {
    setTreeLoading(true);
    try {
      const tree = await modelApi.listMotionsTree();
      setMotionTree(tree);
    } catch (error) {
      console.error('Failed to load motion tree:', error);
    } finally {
      setTreeLoading(false);
    }
  };

  const handleFolderClick = (columnIndex: number, folder: FolderInfo) => {
    const node = folder.node;
    const newColumn: ColumnData = {
      path: folder.path,
      folders: Object.entries(node.subdirs).map(([name, subNode]) => ({
        name,
        node: subNode,
        path: [...folder.path, name]
      })),
      files: node.motions
    };
    setColumns(prev => {
      const newColumns = prev.slice(0, columnIndex + 1);
      newColumns.push(newColumn);
      return newColumns;
    });
  };

  const handleFileClick = (file: MotionFileInfo) => {
    if (activePanel === 'player') {
      // Player mode: only update player-specific state
      if (playerMotionType === 'human') {
        setSelectedHumanMotion(file.relative_path);
        if (onPlayerMotionChange) {
          onPlayerMotionChange('human', selectedRobot, file.relative_path, selectedHumanFormat);
        }
      }
    } else {
      // Retargeter mode: update retargeter state
      setSelectedMotionFile(file.relative_path);
      setSelectedMotion(file.relative_path);
      loadBodyTree(file.relative_path);
    }
    setFileSelectorOpen(false);
  };

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

  const handleGeneratorTypeChange = (type: string) => {
    setGeneratorType(type);
    setSelectedMotionFile('');
    setSelectedMotion('');
    setMotionTree(null);
    setColumns([]);
  };

  // Convert robots to options - handle both string[] and RobotInfo[]
  const robotOptions = robots.map((r) =>
    typeof r === 'string' ? { value: r, label: r } : { value: r.name, label: r.name }
  );

  return (
    <>
    <div className="topbar">
      {/* Row 1: Logo | Retargeter/Player toggles | Theme & Language */}
      <div className="topbar-row">
        <div className="topbar-section">
          <div className="topbar-logo">
            <RobotOutlined />
            <span>{t('app.title')}</span>
          </div>
        </div>

        <div className="topbar-divider" />

        <div className="topbar-section">
          <Button
            type={activePanel === 'retargeter' ? 'primary' : 'text'}
            icon={<SettingOutlined />}
            onClick={() => onPanelChange('retargeter')}
          >
            {t('menu.retargeter')}
          </Button>
          <Button
            type={activePanel === 'player' ? 'primary' : 'text'}
            icon={<PlayCircleOutlined />}
            onClick={() => onPanelChange('player')}
          >
            {t('menu.player')}
          </Button>
        </div>

        <div className="topbar-divider" />

        <div className="topbar-section">
          <Dropdown menu={themeMenu} trigger={['click']}>
            <Button type="text">{t('theme.' + theme)}</Button>
          </Dropdown>
          <Dropdown menu={languageMenu} trigger={['click']}>
            <Button type="text" icon={<GlobalOutlined />} />
          </Dropdown>
        </div>
      </div>

      <div className="topbar-row-separator" />

      {/* Row 2: Conditional based on activePanel */}
      {activePanel === 'retargeter' && (
        <>
          <div className="topbar-row">
            <div className="topbar-section">
              <Select
                value={selectedRobot}
                onChange={setSelectedRobot}
                style={{ width: 140 }}
                options={robotOptions}
                suffixIcon={<RobotOutlined />}
              />
            </div>

            <div className="topbar-section">
              <Select
                value={generatorType}
                onChange={handleGeneratorTypeChange}
                style={{ width: 100 }}
                options={[
                  { value: 'bvh', label: 'BVH' },
                  { value: 'smpl', label: 'SMPL' },
                ]}
              />
            </div>

            <div className="topbar-section">
              <Button
                className="motion-file-btn"
                icon={<FileOutlined />}
                onClick={() => setFileSelectorOpen(true)}
              >
                <span className="motion-file-btn-text">
                  {selectedMotionFile
                    ? selectedMotionFile.split('/').pop()
                    : t('configPanel.selectMotionPlaceholder')}
                </span>
              </Button>
            </div>
          </div>

          <div className="topbar-row-separator" />

          {/* Row 3: Config selector | Add | Save | Delete */}
          <div className="topbar-row">
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

            <div className="topbar-section">
              <Button icon={<SaveOutlined />} onClick={saveConfig} loading={saving}>
                {t('configPanel.save')}
              </Button>
              <Button icon={<DeleteOutlined />} onClick={handleDeleteConfig} danger>
                {t('configPanel.delete')}
              </Button>
            </div>
          </div>
        </>
      )}

      {activePanel === 'player' && (
        <>
          <div className="topbar-row">
            <div className="topbar-section">
              <Button
                type={playerMotionType === 'robot' ? 'primary' : 'text'}
                onClick={() => setPlayerMotionType('robot')}
              >
                {t('player.robotMotion')}
              </Button>
              <Button
                type={playerMotionType === 'human' ? 'primary' : 'text'}
                onClick={() => setPlayerMotionType('human')}
                style={{ marginLeft: 8 }}
              >
                {t('player.humanMotion')}
              </Button>
            </div>
          </div>

          <div className="topbar-row-separator" />

          {/* Row 3: Player motion selectors */}
          <div className="topbar-row">
            {playerMotionType === 'robot' ? (
              <>
                <div className="topbar-section">
                  <Select
                    value={selectedRobot}
                    onChange={setSelectedRobot}
                    style={{ width: 140 }}
                    options={robotOptions}
                    placeholder={t('player.selectRobot')}
                    suffixIcon={<RobotOutlined />}
                  />
                </div>
                <div className="topbar-section">
                  <Select
                    value={selectedRobotMotion}
                    onChange={(val) => {
                      setSelectedRobotMotion(val);
                      if (onPlayerMotionChange && selectedRobot) {
                        onPlayerMotionChange('robot', selectedRobot, val);
                      }
                    }}
                    style={{ width: 200 }}
                    placeholder={retargetedMotions.length === 0 && !retargetedLoading ? t('player.noRetargetedMotions') : t('player.selectRobotMotion')}
                    loading={retargetedLoading}
                    options={retargetedMotions.map(m => ({ value: m, label: m }))}
                    disabled={retargetedMotions.length === 0}
                  />
                </div>
              </>
            ) : (
              <>
                <div className="topbar-section">
                  <Select
                    value={selectedHumanFormat}
                    onChange={(val) => {
                      setSelectedHumanFormat(val);
                      setSelectedHumanMotion('');
                      setMotionTree(null);
                      setColumns([]);
                    }}
                    style={{ width: 100 }}
                    options={[
                      { value: 'bvh', label: 'BVH' },
                      { value: 'smpl', label: 'SMPL' },
                    ]}
                  />
                </div>
                <div className="topbar-section">
                  <Button
                    className="motion-file-btn"
                    icon={<FileOutlined />}
                    onClick={() => setFileSelectorOpen(true)}
                  >
                    <span className="motion-file-btn-text">
                      {selectedHumanMotion
                        ? selectedHumanMotion.split('/').pop()
                        : t('player.selectHumanMotion')}
                    </span>
                  </Button>
                </div>
              </>
            )}
          </div>
        </>
      )}
    </div>

    {/* File Selector Modal */}
    {fileSelectorOpen && (
      <div className="file-selector-overlay" onClick={() => setFileSelectorOpen(false)}>
        <div className="file-selector-modal" onClick={e => e.stopPropagation()}>
          {/* Header */}
          <div className="file-selector-modal-header">
            <div className="file-selector-modal-title">
              <FileOutlined />
              <span>{t('configPanel.selectMotionPlaceholder')}</span>
            </div>
            {/* Breadcrumb */}
            <div className="file-selector-breadcrumb">
              <span
                className="file-selector-breadcrumb-item root"
                onClick={() => setColumns(prev => prev.slice(0, 1))}
              >
                {(activePanel === 'player' ? selectedHumanFormat : generatorType).toUpperCase()}
              </span>
              {columns.slice(1).map((col, i) => (
                <React.Fragment key={i}>
                  <RightOutlined className="file-selector-breadcrumb-sep" />
                  <span
                    className="file-selector-breadcrumb-item"
                    onClick={() => setColumns(prev => prev.slice(0, i + 2))}
                  >
                    {col.path[col.path.length - 1]}
                  </span>
                </React.Fragment>
              ))}
            </div>
            <button
              className="file-selector-modal-close"
              onClick={() => setFileSelectorOpen(false)}
            >
              <CloseOutlined />
            </button>
          </div>

          {/* Body */}
          <div className="file-selector-modal-body">
            {treeLoading ? (
              <div className="file-selector-loading">
                <Spin size="default" />
              </div>
            ) : columns.length === 0 ? (
              <div className="file-selector-empty">{t('fileBrowser.emptyFolder')}</div>
            ) : (
              <div className="file-selector-columns">
                {columns.map((column, columnIndex) => (
                  <div key={columnIndex} className="file-selector-column">
                    <div className="file-selector-column-label">
                      {column.path.length === 0
                        ? (activePanel === 'player' ? selectedHumanFormat : generatorType).toUpperCase()
                        : column.path[column.path.length - 1]}
                    </div>
                    <div className="file-selector-column-content">
                      {column.folders.length === 0 && column.files.length === 0 ? (
                        <div className="file-selector-empty">{t('fileBrowser.emptyFolder')}</div>
                      ) : (
                        <>
                          {column.folders.map(folder => (
                            <div
                              key={folder.name}
                              className={`file-selector-item folder ${
                                columns[columnIndex + 1]?.path[columnIndex] === folder.name ? 'active' : ''
                              }`}
                              onClick={() => handleFolderClick(columnIndex, folder)}
                            >
                              <FolderOutlined className="fsi-icon" />
                              <span className="fsi-name">{folder.name}</span>
                              <span className="fsi-badge">{folder.node.motions.length}</span>
                              <RightOutlined className="fsi-arrow" />
                            </div>
                          ))}
                          {column.files.map(file => (
                            <div
                              key={file.relative_path}
                              className={`file-selector-item ${
                                selectedMotionFile === file.relative_path ? 'selected' : ''
                              }`}
                              onClick={() => handleFileClick(file)}
                            >
                              <FileOutlined className="fsi-icon" />
                              <span className="fsi-name">{file.filename}</span>
                              <span className="fsi-tag">{file.type.toUpperCase()}</span>
                            </div>
                          ))}
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    )}
    </>
  );
};

export default TopBar;