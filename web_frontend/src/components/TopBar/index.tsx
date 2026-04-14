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
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useConfigContext } from '../../contexts/ConfigContext';
import { useMotionContext } from '../../contexts/MotionContext';
import { modelApi, MotionTreeNode, MotionFileInfo } from '../../api/client';
import { MotionInfo } from '../../types/config';
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
}

const TopBar: React.FC<TopBarProps> = ({
  activePanel,
  onPanelChange,
  theme,
  onThemeChange,
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
  } = useConfigContext();
  const { setSelectedMotion } = useMotionContext();
  const [isCreatingConfig, setIsCreatingConfig] = useState(false);
  const [newConfigName, setNewConfigName] = useState('');
  const [motions, setMotions] = useState<MotionInfo[]>([]);

  // File selector popover state
  const [fileSelectorOpen, setFileSelectorOpen] = useState(false);
  const [motionTree, setMotionTree] = useState<Record<string, MotionTreeNode> | null>(null);
  const [columns, setColumns] = useState<ColumnData[]>([]);
  const [treeLoading, setTreeLoading] = useState(false);

  // Fetch motion files when generator type changes
  useEffect(() => {
    const fetchMotions = async () => {
      try {
        const data = await modelApi.listMotions(generatorType);
        setMotions(data);
      } catch (error) {
        console.error('Failed to load motions', error);
        setMotions([]);
      }
    };
    fetchMotions();
  }, [generatorType]);

  // Load motion tree when file selector opens
  useEffect(() => {
    if (fileSelectorOpen && !motionTree) {
      loadMotionTree();
    }
  }, [fileSelectorOpen]);

  // Initialize columns when motionTree or generatorType changes
  useEffect(() => {
    if (motionTree && motionTree[generatorType]) {
      const rootNode = motionTree[generatorType];
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
  }, [motionTree, generatorType]);

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
    setSelectedMotionFile(file.relative_path);
    setSelectedMotion(file.relative_path);
    loadBodyTree(file.relative_path);
    setFileSelectorOpen(false);
  };

  const handleColumnClick = (columnIndex: number) => {
    if (columnIndex < columns.length - 1) {
      setColumns(prev => prev.slice(0, columnIndex + 1));
    }
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

  const handleMotionChange = (filename: string) => {
    setSelectedMotionFile(filename);
    setSelectedMotion(filename);
    loadBodyTree(filename);
  };

  const handleGeneratorTypeChange = (type: string) => {
    setGeneratorType(type);
    setSelectedMotionFile('');
    setSelectedMotion('');
    setMotions([]);
  };

  // Convert robots to options - handle both string[] and RobotInfo[]
  const robotOptions = robots.map((r) =>
    typeof r === 'string' ? { value: r, label: r } : { value: r.name, label: r.name }
  );

  // Motion file options based on generator type
  const motionOptions = motions.map((m) => ({ value: m.filename, label: m.filename }));

  return (
    <>
    <div className="topbar">
      {/* Row 1: Logo | Robot | Generator Type | Motion File | Config */}
      <div className="topbar-row">
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
            onChange={handleGeneratorTypeChange}
            style={{ width: 100 }}
            options={[
              { value: 'bvh', label: 'BVH' },
              { value: 'smpl', label: 'SMPL' },
            ]}
          />
        </div>

        {/* Motion File Selection */}
        <div className="topbar-section">
          <Button
            style={{ width: 160 }}
            icon={<FileOutlined />}
            onClick={() => setFileSelectorOpen(true)}
          >
            {selectedMotionFile
              ? selectedMotionFile.split('/').pop()
              : t('configPanel.selectMotionPlaceholder')}
          </Button>
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
      </div>

      <div className="topbar-divider" />

      {/* Row 2: Panel Toggles | Theme & Language */}
      <div className="topbar-row">
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
                {generatorType.toUpperCase()}
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
                        ? generatorType.toUpperCase()
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