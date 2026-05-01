import React, { useState, useEffect, useRef } from 'react';
import { Select, Button, Input, Dropdown, Spin, message, Modal, Form, InputNumber, Space } from 'antd';
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
  UploadOutlined,
  ToolOutlined,
  ScissorOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useConfigContext } from '../../contexts/ConfigContext';
import { useMotionContext } from '../../contexts/MotionContext';
import { modelApi, MotionTreeNode, MotionFileInfo, HumanConfig } from '../../api/client';
import JointAdjustmentWidget from '../Widgets/JointAdjustmentWidget';
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
  playerMotion?: {
    type: 'robot' | 'human' | 'retarget-preview' | 'retarget-stream';
    robotName: string;
    motionFile: string;
    generatorType?: string;
    reloadKey?: number;
  } | null;
  onPanelChange: (panel: string) => void;
  theme: ThemeType;
  onThemeChange: (theme: ThemeType) => void;
  onPlayerMotionChange?: (type: 'robot' | 'human', robotName: string, motionFile: string, generatorType?: string) => void;
  onCloseRetargetStream?: () => void;
}

const TopBar: React.FC<TopBarProps> = ({
  activePanel,
  playerMotion,
  onPanelChange,
  theme,
  onThemeChange,
  onPlayerMotionChange,
  onCloseRetargetStream,
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

  // HumanConfig modal state
  const [humanConfigOpen, setHumanConfigOpen] = useState(false);
  const [humanConfig, setHumanConfig] = useState<HumanConfig | null>(null);
  const [humanConfigLoading, setHumanConfigLoading] = useState(false);
  const [humanConfigSaving, setHumanConfigSaving] = useState(false);
  const [humanBodyNames, setHumanBodyNames] = useState<string[]>([]);

  // File selector popover state
  const [fileSelectorOpen, setFileSelectorOpen] = useState(false);
  const [motionTree, setMotionTree] = useState<Record<string, MotionTreeNode> | null>(null);
  const [columns, setColumns] = useState<ColumnData[]>([]);
  const [treeLoading, setTreeLoading] = useState(false);

  // Upload state
  const [uploadRobotLoading, setUploadRobotLoading] = useState(false);
  const [uploadHumanLoading, setUploadHumanLoading] = useState(false);
  const robotFileInputRef = useRef<HTMLInputElement>(null);
  const humanFileInputRef = useRef<HTMLInputElement>(null);

  // Toolbox state
  const [toolboxOpen, setToolboxOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);

  // Motion Segmentation tool state
  const [segmentFormat, setSegmentFormat] = useState<'bvh' | 'smpl'>('smpl');
  const [segmentMotionFile, setSegmentMotionFile] = useState<string>('');
  const [splitPosition, setSplitPosition] = useState<string>('');
  const [splitting, setSplitting] = useState(false);

  // Robot Motion Segmentation tool state
  const [robotSegmentRobot, setRobotSegmentRobot] = useState<string>('');
  const [robotSegmentMotion, setRobotSegmentMotion] = useState<string>('');
  const [robotSplitPosition, setRobotSplitPosition] = useState<string>('');
  const [robotSplitting, setRobotSplitting] = useState(false);
  const [robotSegmentMotions, setRobotSegmentMotions] = useState<string[]>([]);
  const [robotSegmentLoading, setRobotSegmentLoading] = useState(false);

  // Load retargeted motions when entering player mode
  useEffect(() => {
    if (activePanel === 'player' && selectedRobot) {
      setRetargetedLoading(true);
      modelApi.listRetargetedMotions(selectedRobot)
        .then(setRetargetedMotions)
        .catch(console.error)
        .finally(() => setRetargetedLoading(false));
    }
  }, [activePanel, selectedRobot]);

  // Load robot motions when robot is selected in robot segmentation tool
  useEffect(() => {
    if (selectedTool === 'robotMotionSegmentation' && robotSegmentRobot) {
      setRobotSegmentLoading(true);
      modelApi.listRetargetedMotions(robotSegmentRobot)
        .then(setRobotSegmentMotions)
        .catch(console.error)
        .finally(() => setRobotSegmentLoading(false));
    }
  }, [selectedTool, robotSegmentRobot]);
  useEffect(() => {
    if (fileSelectorOpen && !motionTree) {
      loadMotionTree();
    }
  }, [fileSelectorOpen]);

  // Initialize columns when motionTree or generatorType changes
  useEffect(() => {
    // Use segmentFormat in segmentation tool mode, otherwise use panel-based selection
    let currentGenType: string;
    if (selectedTool === 'motionSegmentation') {
      currentGenType = segmentFormat;
    } else {
      currentGenType = activePanel === 'player' ? selectedHumanFormat : generatorType;
    }
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
  }, [motionTree, generatorType, selectedHumanFormat, activePanel, selectedTool, segmentFormat]);

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
    if (selectedTool === 'motionSegmentation') {
      // Segmentation tool mode
      setSegmentMotionFile(file.relative_path);
    } else if (activePanel === 'player') {
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

  const toolboxMenu = {
    items: [
      { key: 'motionSegmentation', label: t('toolbox.motionSegmentation') || 'Human Motion Segmentation', onClick: () => { setSelectedTool('motionSegmentation'); setToolboxOpen(false); } },
      { key: 'robotMotionSegmentation', label: t('toolbox.robotMotionSegmentation') || 'Robot Motion Segmentation', onClick: () => { setSelectedTool('robotMotionSegmentation'); setToolboxOpen(false); } },
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

  // Upload robot motion handler
  const handleUploadRobotMotion = async () => {
    if (!selectedRobot) {
      message.warning(t('player.pleaseSelectRobotFirst'));
      return;
    }
    robotFileInputRef.current?.click();
  };

  const handleRobotFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedRobot) return;

    setUploadRobotLoading(true);
    try {
      const result = await modelApi.uploadRobotMotion(selectedRobot, file);
      if (result.status === 'uploaded') {
        message.success(t('player.uploadRobotMotionSuccess'));
        // Refresh the retargeted motions list
        const motions = await modelApi.listRetargetedMotions(selectedRobot);
        setRetargetedMotions(motions);
        setSelectedRobotMotion(result.filename);
        if (onPlayerMotionChange) {
          onPlayerMotionChange('robot', selectedRobot, result.filename);
        }
      }
    } catch (error) {
      message.error(t('player.uploadRobotMotionFailed'));
    } finally {
      setUploadRobotLoading(false);
      if (robotFileInputRef.current) {
        robotFileInputRef.current.value = '';
      }
    }
  };

  // Upload human motion handler
  const handleUploadHumanMotion = async () => {
    humanFileInputRef.current?.click();
  };

  const handleHumanFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadHumanLoading(true);
    try {
      const result = await modelApi.uploadHumanMotion(file);
      if (result.status === 'uploaded') {
        message.success(t('player.uploadHumanMotionSuccess'));
        // Refresh the motion tree
        setMotionTree(null);
        setColumns([]);
        // Use the generator_type returned from backend to properly select the file
        const genType = result.generator_type || selectedHumanFormat;
        setSelectedHumanFormat(genType as 'bvh' | 'smpl');
        setSelectedHumanMotion(result.filename);
        if (onPlayerMotionChange) {
          onPlayerMotionChange('human', selectedRobot, result.filename, genType);
        }
      }
    } catch (error) {
      message.error(t('player.uploadHumanMotionFailed'));
    } finally {
      setUploadHumanLoading(false);
      if (humanFileInputRef.current) {
        humanFileInputRef.current.value = '';
      }
    }
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
            type={!selectedTool && activePanel === 'retargeter' ? 'primary' : 'text'}
            icon={<SettingOutlined />}
            onClick={() => {
              setSelectedTool(null);
              onPanelChange('retargeter');
            }}
          >
            {t('menu.retargeter')}
          </Button>
          <Button
            type={!selectedTool && activePanel === 'player' ? 'primary' : 'text'}
            icon={<PlayCircleOutlined />}
            onClick={() => {
              setSelectedTool(null);
              onPanelChange('player');
              setSelectedMotionFile('');
              setMotionTree(null);
              setColumns([]);
            }}
          >
            {t('menu.player')}
          </Button>
          <Dropdown menu={toolboxMenu} trigger={['click']} open={toolboxOpen} onOpenChange={setToolboxOpen}>
            <Button type={selectedTool ? 'primary' : 'text'} icon={<ToolOutlined />}>{t('toolbox.name')}</Button>
          </Dropdown>
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

      {/* Row 2: Tool selection or activePanel content */}
      {selectedTool ? (
        <>
          <div className="topbar-row">
            <div className="topbar-section">
              <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 14 }}>
                {t('toolbox.selected') || 'Selected Tool'}: {toolboxMenu.items.find(item => item.key === selectedTool)?.label}
              </span>
            </div>
          </div>
          <div className="topbar-row-separator" />

          {/* Row 3: Reserved for tool content */}
          {selectedTool === 'motionSegmentation' ? (
            <>
              <div className="topbar-row">
                <div className="topbar-section">
                  <Select
                    value={segmentFormat}
                    onChange={(val) => { setSegmentFormat(val); setSegmentMotionFile(''); setMotionTree(null); setColumns([]); }}
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
                      {segmentMotionFile
                        ? segmentMotionFile.split('/').pop()
                        : t('toolbox.selectMotionFile')}
                    </span>
                  </Button>
                </div>
                <div className="topbar-section">
                  <Input
                    value={splitPosition}
                    onChange={(e) => setSplitPosition(e.target.value)}
                    placeholder={t('toolbox.splitPositions')}
                    style={{ width: 200 }}
                  />
                </div>
                <div className="topbar-section">
                  <Button
                    type="primary"
                    icon={<ScissorOutlined />}
                    onClick={async () => {
                      if (!segmentMotionFile) {
                        message.warning(t('toolbox.noMotionSelected'));
                        return;
                      }
                      if (!splitPosition.trim()) {
                        message.warning(t('toolbox.noSplitPositions'));
                        return;
                      }
                      setSplitting(true);
                      try {
                        await modelApi.splitMotion(segmentFormat, segmentMotionFile, splitPosition);
                        message.success(t('toolbox.splitSuccess'));
                      } catch (error) {
                        message.error(t('toolbox.splitFailed'));
                      } finally {
                        setSplitting(false);
                      }
                    }}
                    loading={splitting}
                  >
                    {t('toolbox.split')}
                  </Button>
                </div>
              </div>
            </>
          ) : selectedTool === 'robotMotionSegmentation' ? (
            <>
              <div className="topbar-row">
                <div className="topbar-section">
                  <Select
                    value={robotSegmentRobot}
                    onChange={(val) => { setRobotSegmentRobot(val); setRobotSegmentMotion(''); }}
                    style={{ width: 140 }}
                    options={robotOptions}
                    placeholder={t('toolbox.selectRobot')}
                    suffixIcon={<RobotOutlined />}
                  />
                </div>
                <div className="topbar-section">
                  <Select
                    value={robotSegmentMotion}
                    onChange={setRobotSegmentMotion}
                    style={{ width: 200 }}
                    placeholder={robotSegmentMotions.length === 0 && !robotSegmentLoading ? t('toolbox.noRobotMotions') : t('toolbox.selectRobotMotion')}
                    loading={robotSegmentLoading}
                    options={robotSegmentMotions.map(m => ({ value: m, label: m }))}
                    disabled={robotSegmentMotions.length === 0}
                  />
                </div>
                <div className="topbar-section">
                  <Input
                    value={robotSplitPosition}
                    onChange={(e) => setRobotSplitPosition(e.target.value)}
                    placeholder={t('toolbox.splitPositions')}
                    style={{ width: 200 }}
                  />
                </div>
                <div className="topbar-section">
                  <Button
                    type="primary"
                    icon={<ScissorOutlined />}
                    onClick={async () => {
                      if (!robotSegmentRobot) {
                        message.warning(t('toolbox.noRobotSelected'));
                        return;
                      }
                      if (!robotSegmentMotion) {
                        message.warning(t('toolbox.noRobotMotionSelected'));
                        return;
                      }
                      if (!robotSplitPosition.trim()) {
                        message.warning(t('toolbox.noSplitPositions'));
                        return;
                      }
                      setRobotSplitting(true);
                      try {
                        await modelApi.splitRobotMotion(robotSegmentRobot, robotSegmentMotion, robotSplitPosition);
                        message.success(t('toolbox.splitSuccess'));
                        // Refresh robot motions list
                        const motions = await modelApi.listRetargetedMotions(robotSegmentRobot);
                        setRobotSegmentMotions(motions);
                      } catch (error) {
                        message.error(t('toolbox.splitFailed'));
                      } finally {
                        setRobotSplitting(false);
                      }
                    }}
                    loading={robotSplitting}
                  >
                    {t('toolbox.split')}
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <div className="topbar-row">
              <div className="topbar-section" />
            </div>
          )}
        </>
      ) : (
        <>
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
              {/* Only show Robot/Human toggle if not in retarget-preview or retarget-stream mode */}
              {playerMotion?.type !== 'retarget-preview' && playerMotion?.type !== 'retarget-stream' && (
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
                </>
              )}

              {/* Show retarget preview info if in retarget-preview or retarget-stream mode */}
              {(playerMotion?.type === 'retarget-preview' || playerMotion?.type === 'retarget-stream') && (
                <>
                  <div className="topbar-row">
                    <div className="topbar-section">
                      <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 14 }}>
                        {playerMotion.type === 'retarget-stream'
                          ? (t('player.retargetStreaming') || 'Retarget Streaming')
                          : (t('player.retargetPreview') || 'Retarget Preview')
                        }: {playerMotion.robotName}
                      </span>
                    </div>
                    <div className="topbar-section">
                      <Button
                        type="text"
                        icon={<CloseOutlined />}
                        onClick={() => {
                          if (onCloseRetargetStream) {
                            onCloseRetargetStream();
                          }
                        }}
                        style={{ color: 'rgba(255,255,255,0.7)' }}
                        title={t('player.closeRetargetMode') || 'Close Retarget Mode'}
                      />
                    </div>
                  </div>

                  <div className="topbar-row-separator" />
                </>
              )}

              {/* Row 3: Player motion selectors - only show if not in retarget-preview or retarget-stream mode */}
              {playerMotion?.type !== 'retarget-preview' && playerMotion?.type !== 'retarget-stream' && (
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
                    <div className="topbar-section">
                      <Button
                        icon={<UploadOutlined />}
                        onClick={handleUploadRobotMotion}
                        loading={uploadRobotLoading}
                        disabled={!selectedRobot}
                      >
                        {t('player.uploadRobotMotion')}
                      </Button>
                      <input
                        ref={robotFileInputRef}
                        type="file"
                        accept=".npz"
                        style={{ display: 'none' }}
                        onChange={handleRobotFileChange}
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
                    <div className="topbar-section">
                      <Button
                        icon={<UploadOutlined />}
                        onClick={handleUploadHumanMotion}
                        loading={uploadHumanLoading}
                      >
                        {t('player.uploadHumanMotion')}
                      </Button>
                      <input
                        ref={humanFileInputRef}
                        type="file"
                        accept=".bvh,.npz"
                        style={{ display: 'none' }}
                        onChange={handleHumanFileChange}
                      />
                    </div>
                    {playerMotionType === 'human' && selectedHumanMotion && (
                      <div className="topbar-section">
                        <Button
                          icon={<SettingOutlined />}
                          onClick={() => {
                            setHumanConfig(null);
                            setHumanBodyNames([]);
                            setHumanConfigLoading(true);
                            setHumanConfigOpen(true);
                            Promise.all([
                              modelApi.getHumanPlayerConfig(selectedHumanFormat, selectedHumanMotion),
                              modelApi.getHumanPlayerMotionData(selectedHumanFormat, selectedHumanMotion, false),
                            ])
                              .then(([config, motionData]) => {
                                setHumanConfig(config);
                                setHumanBodyNames(motionData.body_names || []);
                              })
                              .catch(err => {
                                console.error('Failed to load HumanConfig:', err);
                                message.error(t('player.loadHumanConfigFailed'));
                                setHumanConfigOpen(false);
                              })
                              .finally(() => setHumanConfigLoading(false));
                          }}
                          loading={humanConfigLoading}
                        >
                          {t('player.humanConfig')}
                        </Button>
                      </div>
                    )}
                  </>
                )}
                </div>
              )}
            </>
          )}
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
                {(selectedTool === 'motionSegmentation' ? segmentFormat : (activePanel === 'player' ? selectedHumanFormat : generatorType)).toUpperCase()}
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
                        ? (selectedTool === 'motionSegmentation' ? segmentFormat : (activePanel === 'player' ? selectedHumanFormat : generatorType)).toUpperCase()
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

    {/* HumanConfig Modal */}
    <Modal
      title={t('player.humanConfig')}
      open={humanConfigOpen}
      onCancel={() => setHumanConfigOpen(false)}
      footer={null}
      width={600}
      className="human-config-modal"
    >
      {humanConfig && (
        <Form
          layout="vertical"
          initialValues={humanConfig}
          onValuesChange={(_, allValues) => setHumanConfig({
            ...allValues,
            joint_adjustments: humanConfig.joint_adjustments
          } as HumanConfig)}
        >
          <Form.Item label={t('player.heightAdjustment')} name="height_adjustment">
            <InputNumber style={{ width: '100%' }} placeholder="Auto calculated" />
          </Form.Item>

          <Form.Item label={t('player.hipNames')}>
            <Space direction="horizontal" size="small" style={{ display: 'flex' }}>
              <Form.Item name={['hip_names', 0]} noStyle>
                <Select
                  placeholder={t('player.selectHipName')}
                  options={humanBodyNames.map(name => ({ value: name, label: name }))}
                  style={{ width: 280 }}
                />
              </Form.Item>
              <Form.Item name={['hip_names', 1]} noStyle>
                <Select
                  placeholder={t('player.selectHipName')}
                  options={humanBodyNames.map(name => ({ value: name, label: name }))}
                  style={{ width: 280 }}
                />
              </Form.Item>
            </Space>
          </Form.Item>

          <Form.Item label={t('player.hipOffset')} name="hip_offset">
            <InputNumber style={{ width: '100%' }} step={0.01} />
          </Form.Item>

          <Form.Item label={t('player.footNames')}>
            <Space direction="horizontal" size="small" style={{ display: 'flex' }}>
              <Form.Item name={['foot_names', 0]} noStyle>
                <Select
                  placeholder={t('player.selectFootName')}
                  options={humanBodyNames.map(name => ({ value: name, label: name }))}
                  style={{ width: 280 }}
                />
              </Form.Item>
              <Form.Item name={['foot_names', 1]} noStyle>
                <Select
                  placeholder={t('player.selectFootName')}
                  options={humanBodyNames.map(name => ({ value: name, label: name }))}
                  style={{ width: 280 }}
                />
              </Form.Item>
            </Space>
          </Form.Item>

          <Form.Item label={t('player.footOffset')} name="foot_offset">
            <InputNumber style={{ width: '100%' }} step={0.01} />
          </Form.Item>

          <Form.Item>
            <JointAdjustmentWidget
              jointAdjustments={humanConfig.joint_adjustments || {}}
              availableJoints={humanBodyNames}
              onChange={(adjustments) => {
                setHumanConfig({ ...humanConfig, joint_adjustments: adjustments });
              }}
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                loading={humanConfigSaving}
                onClick={async () => {
                  if (!humanConfig || !selectedHumanMotion) return;
                  setHumanConfigSaving(true);
                  try {
                    await modelApi.saveHumanPlayerConfig(selectedHumanFormat, selectedHumanMotion, humanConfig);
                    message.success(t('player.saveHumanConfigSuccess'));
                    setHumanConfigOpen(false);
                    // Trigger reload of motion
                    if (onPlayerMotionChange) {
                      onPlayerMotionChange('human', selectedRobot, selectedHumanMotion, selectedHumanFormat);
                    }
                  } catch (err) {
                    console.error('Failed to save HumanConfig:', err);
                    message.error(t('player.saveHumanConfigFailed'));
                  } finally {
                    setHumanConfigSaving(false);
                  }
                }}
              >
                {t('configPanel.save')}
              </Button>
              <Button onClick={() => setHumanConfigOpen(false)}>
                {t('common.cancel')}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      )}
    </Modal>
  </>
  );
};

export default TopBar;