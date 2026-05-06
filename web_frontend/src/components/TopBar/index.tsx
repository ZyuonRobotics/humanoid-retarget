import React, { useState, useEffect, useRef } from 'react';
import { Select, Button, Input, Dropdown, Spin, message, Modal, Form, InputNumber, Space, Radio } from 'antd';
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
  ThunderboltOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useConfigContext } from '../../contexts/ConfigContext';
import { useMotionContext } from '../../contexts/MotionContext';
import { usePerformanceContext } from '../../contexts/PerformanceContext';
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
  onPlayerMotionChange?: (type: 'robot' | 'human' | 'retarget-preview' | 'retarget-stream', robotName: string, motionFile: string, generatorType?: string) => void;
}

const TopBar: React.FC<TopBarProps> = ({
  activePanel,
  playerMotion,
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
  const { settings: performanceSettings, setLowPerformanceMode } = usePerformanceContext();
  const [isCreatingConfig, setIsCreatingConfig] = useState(false);
  const [newConfigName, setNewConfigName] = useState('');

  // Player mode state
  const [playerMotionType, setPlayerMotionType] = useState<'robot' | 'human' | 'retargeted'>('robot');
  const [selectedRobotMotion, setSelectedRobotMotion] = useState<string>('');
  const [selectedHumanFormat, setSelectedHumanFormat] = useState<'smpl' | 'bvh'>('bvh');
  const [selectedHumanMotion, setSelectedHumanMotion] = useState<string>('');

  // HumanConfig modal state
  const [humanConfigOpen, setHumanConfigOpen] = useState(false);
  const [humanConfig, setHumanConfig] = useState<HumanConfig | null>(null);
  const [humanConfigLoading, setHumanConfigLoading] = useState(false);
  const [humanConfigSaving, setHumanConfigSaving] = useState(false);
  const [humanConfigCalculating, setHumanConfigCalculating] = useState(false);
  const [humanBodyNames, setHumanBodyNames] = useState<string[]>([]);
  const [humanConfigForm] = Form.useForm();
  const [humanConfigMotionKey, setHumanConfigMotionKey] = useState<string>('');

  // File selector popover state
  const [fileSelectorOpen, setFileSelectorOpen] = useState(false);
  const [fileSelectorMode, setFileSelectorMode] = useState<'human' | 'robot' | 'segment'>('human');
  const [motionTree, setMotionTree] = useState<Record<string, MotionTreeNode> | null>(null);
  const [robotMotionTree, setRobotMotionTree] = useState<MotionTreeNode | null>(null);
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

  // Load retargeted motions when entering player mode - no longer needed since we use file selector
  // useEffect(() => {
  //   if (activePanel === 'player' && selectedRobot) {
  //     setRetargetedLoading(true);
  //     modelApi.listRetargetedMotions(selectedRobot)
  //       .then(setRetargetedMotions)
  //       .catch(console.error)
  //       .finally(() => setRetargetedLoading(false));
  //   }
  // }, [activePanel, selectedRobot]);

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

  // Reload human config when motion file or format changes while modal is open
  useEffect(() => {
    const currentKey = `${selectedHumanFormat}:${selectedHumanMotion}`;
    if (humanConfigOpen && selectedHumanMotion && humanConfigMotionKey !== currentKey) {
      setHumanConfig(null);
      setHumanBodyNames([]);
      setHumanConfigLoading(true);
      setHumanConfigMotionKey(currentKey);
      Promise.all([
        modelApi.getHumanPlayerConfig(selectedHumanFormat, selectedHumanMotion),
        modelApi.getHumanPlayerMotionData(selectedHumanFormat, selectedHumanMotion, false),
      ])
        .then(([config, motionData]) => {
          setHumanConfig(config);
          setHumanBodyNames(motionData.body_names || []);
          humanConfigForm.setFieldsValue({
            ...config,
            height_adjustment_method: config.height_adjustment_method ||
              (config.height_adjustment === null ? 'plane_fit' :
                (Array.isArray(config.height_adjustment) ? 'plane_fit' : 'offset'))
          });
        })
        .catch(err => {
          console.error('Failed to load HumanConfig:', err);
          message.error(t('player.loadHumanConfigFailed'));
        })
        .finally(() => setHumanConfigLoading(false));
    }
  }, [humanConfigOpen, selectedHumanFormat, selectedHumanMotion, humanConfigMotionKey, humanConfigForm, t]);

  // Auto-switch to retargeted motion type when entering retarget mode
  useEffect(() => {
    if (activePanel === 'player' && (playerMotion?.type === 'retarget-preview' || playerMotion?.type === 'retarget-stream')) {
      setPlayerMotionType('retargeted');
    }
  }, [activePanel, playerMotion?.type]);
  useEffect(() => {
    if (fileSelectorOpen) {
      if (fileSelectorMode === 'robot' && !robotMotionTree) {
        loadMotionTree();
      } else if (fileSelectorMode === 'human' && !motionTree) {
        loadMotionTree();
      }
    }
  }, [fileSelectorOpen, fileSelectorMode]);

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

  const loadMotionTree = async (preserveSelection: boolean = false) => {
    setTreeLoading(true);
    try {
      // Save current selections before reloading
      const savedColumns = preserveSelection ? [...columns] : null;
      const savedSelectedMotionFile = preserveSelection ? selectedMotionFile : null;
      const savedSegmentMotionFile = preserveSelection ? segmentMotionFile : null;
      const savedSelectedHumanMotion = preserveSelection ? selectedHumanMotion : null;
      const savedSelectedRobotMotion = preserveSelection ? selectedRobotMotion : null;

      // Load appropriate tree based on mode
      if (fileSelectorMode === 'robot' && selectedRobot) {
        // Load robot motion tree
        const tree = await modelApi.listRetargetedMotionsTree(selectedRobot);
        setRobotMotionTree(tree);

        // Initialize columns for robot motion tree
        if (!preserveSelection || !savedColumns || savedColumns.length === 0) {
          const rootColumn: ColumnData = {
            path: [],
            folders: Object.entries(tree.subdirs).map(([name, node]) => ({
              name,
              node,
              path: [name]
            })),
            files: tree.motions
          };
          setColumns([rootColumn]);
        } else {
          // Restore columns for robot motion
          setTimeout(() => {
            const newColumns: ColumnData[] = [];
            let currentNode = tree;

            newColumns.push({
              path: [],
              folders: Object.entries(currentNode.subdirs).map(([name, node]) => ({
                name,
                node,
                path: [name]
              })),
              files: currentNode.motions
            });

            for (let i = 1; i < savedColumns.length; i++) {
              const savedPath = savedColumns[i].path;
              if (savedPath.length > 0) {
                const folderName = savedPath[savedPath.length - 1];
                if (currentNode.subdirs[folderName]) {
                  currentNode = currentNode.subdirs[folderName];
                  newColumns.push({
                    path: savedPath,
                    folders: Object.entries(currentNode.subdirs).map(([name, node]) => ({
                      name,
                      node,
                      path: [...savedPath, name]
                    })),
                    files: currentNode.motions
                  });
                } else {
                  break;
                }
              }
            }

            setColumns(newColumns);
            if (savedSelectedRobotMotion) {
              setSelectedRobotMotion(savedSelectedRobotMotion);
            }
          }, 0);
        }
      } else {
        // Load human motion tree
        const tree = await modelApi.listMotionsTree();
        setMotionTree(tree);

        // Restore selections after tree is loaded
        if (preserveSelection && savedColumns && savedColumns.length > 0) {
          // Reconstruct columns based on saved paths
          setTimeout(() => {
            const currentGenType = selectedTool === 'motionSegmentation'
              ? segmentFormat
              : (activePanel === 'player' ? selectedHumanFormat : generatorType);

            if (tree && tree[currentGenType]) {
              const newColumns: ColumnData[] = [];
              let currentNode = tree[currentGenType];

              // Rebuild columns by following the saved paths
              newColumns.push({
                path: [],
                folders: Object.entries(currentNode.subdirs).map(([name, node]) => ({
                  name,
                  node,
                  path: [name]
                })),
                files: currentNode.motions
              });

              // Traverse through saved column paths
              for (let i = 1; i < savedColumns.length; i++) {
                const savedPath = savedColumns[i].path;
                if (savedPath.length > 0) {
                  const folderName = savedPath[savedPath.length - 1];
                  if (currentNode.subdirs[folderName]) {
                    currentNode = currentNode.subdirs[folderName];
                    newColumns.push({
                      path: savedPath,
                      folders: Object.entries(currentNode.subdirs).map(([name, node]) => ({
                        name,
                        node,
                        path: [...savedPath, name]
                      })),
                      files: currentNode.motions
                    });
                  } else {
                    break; // Path no longer exists
                  }
                }
              }

              setColumns(newColumns);
            }

            // Restore selected file
            if (savedSelectedMotionFile) {
              setSelectedMotionFile(savedSelectedMotionFile);
            }
            if (savedSegmentMotionFile) {
              setSegmentMotionFile(savedSegmentMotionFile);
            }
            if (savedSelectedHumanMotion) {
              setSelectedHumanMotion(savedSelectedHumanMotion);
            }
          }, 0);
        }
      }
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
      } else if (playerMotionType === 'robot') {
        // Robot motion selection - file.filename is just the name without extension
        const motionName = file.filename.replace(/\.npz$/, '');
        setSelectedRobotMotion(motionName);
        if (onPlayerMotionChange && selectedRobot) {
          onPlayerMotionChange('robot', selectedRobot, motionName);
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
        // Refresh the robot motion tree
        if (fileSelectorMode === 'robot') {
          loadMotionTree(true);
        }
        // Strip .npz extension from filename for API calls
        const motionName = result.filename.replace(/\.npz$/, '');
        setSelectedRobotMotion(motionName);
        if (onPlayerMotionChange) {
          onPlayerMotionChange('robot', selectedRobot, motionName);
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
          <Button
            type={performanceSettings.lowPerformanceMode ? 'text' : 'primary'}
            icon={<ThunderboltOutlined />}
            onClick={() => {
              const newMode = !performanceSettings.lowPerformanceMode;
              setLowPerformanceMode(newMode);
              message.success(
                newMode
                  ? t('performance.lowModeEnabled') || 'Low quality mode enabled (VRAM ~500MB)'
                  : t('performance.normalModeEnabled') || 'High quality mode enabled (VRAM ~2GB)'
              );
              // Force page reload to apply settings
              setTimeout(() => window.location.reload(), 500);
            }}
            title={performanceSettings.lowPerformanceMode ? t('performance.lowMode') || 'Low Quality' : t('performance.normalMode') || 'High Quality'}
          >
            {performanceSettings.lowPerformanceMode ? t('performance.lowMode') || 'Low Quality' : t('performance.normalMode') || 'High Quality'}
          </Button>
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
                    onClick={() => {
                      setFileSelectorMode('human');
                      setFileSelectorOpen(true);
                    }}
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
                    onClick={() => {
                      setFileSelectorMode('human');
                      setFileSelectorOpen(true);
                    }}
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
              {/* Row 2: Motion type toggle - always show */}
              <div className="topbar-row">
                <div className="topbar-section">
                  <Button
                    type={playerMotionType === 'robot' ? 'primary' : 'text'}
                    onClick={() => {
                      setPlayerMotionType('robot');
                      if (selectedRobot && selectedRobotMotion && onPlayerMotionChange) {
                        onPlayerMotionChange('robot', selectedRobot, selectedRobotMotion);
                      }
                    }}
                  >
                    {t('player.robotMotion')}
                  </Button>
                  <Button
                    type={playerMotionType === 'human' ? 'primary' : 'text'}
                    onClick={() => {
                      setPlayerMotionType('human');
                      if (selectedRobot && selectedHumanMotion && onPlayerMotionChange) {
                        onPlayerMotionChange('human', selectedRobot, selectedHumanMotion, selectedHumanFormat);
                      }
                    }}
                    style={{ marginLeft: 8 }}
                  >
                    {t('player.humanMotion')}
                  </Button>
                  {/* Show retargeted motion button only when in retarget mode */}
                  {(playerMotion?.type === 'retarget-preview' || playerMotion?.type === 'retarget-stream') && (
                    <Button
                      type={playerMotionType === 'retargeted' ? 'primary' : 'text'}
                      onClick={() => {
                        setPlayerMotionType('retargeted');
                        if (playerMotion && onPlayerMotionChange) {
                          onPlayerMotionChange(
                            playerMotion.type === 'retarget-stream' ? 'retarget-stream' : 'retarget-preview',
                            playerMotion.robotName,
                            playerMotion.motionFile,
                            playerMotion.generatorType
                          );
                        }
                      }}
                      style={{ marginLeft: 8 }}
                    >
                      {t('player.retargetedMotion')}
                    </Button>
                  )}
                </div>
              </div>

              <div className="topbar-row-separator" />

              {/* Row 3: Motion selectors based on selected type */}
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
                      <Button
                        className="motion-file-btn"
                        icon={<FileOutlined />}
                        onClick={() => {
                          setFileSelectorMode('robot');
                          setFileSelectorOpen(true);
                        }}
                        disabled={!selectedRobot}
                      >
                        <span className="motion-file-btn-text">
                          {selectedRobotMotion
                            ? selectedRobotMotion
                            : t('player.selectRobotMotion')}
                        </span>
                      </Button>
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
                ) : playerMotionType === 'human' ? (
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
                        onClick={() => {
                          setFileSelectorMode('human');
                          setFileSelectorOpen(true);
                        }}
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
                    {selectedHumanMotion && (
                      <div className="topbar-section">
                        <Button
                          icon={<SettingOutlined />}
                          onClick={() => {
                            setHumanConfig(null);
                            setHumanBodyNames([]);
                            setHumanConfigLoading(true);
                            setHumanConfigOpen(true);
                            setHumanConfigMotionKey(`${selectedHumanFormat}:${selectedHumanMotion}`);
                            Promise.all([
                              modelApi.getHumanPlayerConfig(selectedHumanFormat, selectedHumanMotion),
                              modelApi.getHumanPlayerMotionData(selectedHumanFormat, selectedHumanMotion, false),
                            ])
                              .then(([config, motionData]) => {
                                setHumanConfig(config);
                                setHumanBodyNames(motionData.body_names || []);
                                humanConfigForm.setFieldsValue({
                                  ...config,
                                  height_adjustment_method: config.height_adjustment_method ||
                                    (config.height_adjustment === null ? 'plane_fit' :
                                      (Array.isArray(config.height_adjustment) ? 'plane_fit' : 'offset'))
                                });
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
                ) : playerMotionType === 'retargeted' && playerMotion ? (
                  <>
                    <div className="topbar-section">
                      <span style={{ color: 'rgba(255,255,255,0.9)', fontSize: 14 }}>
                        {t('player.robot')}: <strong>{playerMotion.robotName}</strong>
                      </span>
                    </div>
                    <div className="topbar-section">
                      <span style={{ color: 'rgba(255,255,255,0.9)', fontSize: 14 }}>
                        {t('player.humanMotion')}: <strong>{playerMotion.motionFile}</strong>
                      </span>
                    </div>
                  </>
                ) : null}
              </div>
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
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Button
                type="text"
                icon={<ReloadOutlined />}
                onClick={() => loadMotionTree(true)}
                loading={treeLoading}
                title={t('fileBrowser.refresh')}
                style={{ color: 'rgba(255,255,255,0.85)' }}
              >
                {t('fileBrowser.refresh')}
              </Button>
              <button
                className="file-selector-modal-close"
                onClick={() => setFileSelectorOpen(false)}
              >
                <CloseOutlined />
              </button>
            </div>
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
          form={humanConfigForm}
          layout="vertical"
          initialValues={{
            ...humanConfig,
            height_adjustment_method: humanConfig.height_adjustment_method ||
              (humanConfig.height_adjustment === null ? 'plane_fit' :
                (Array.isArray(humanConfig.height_adjustment) ? 'plane_fit' : 'offset'))
          }}
          onValuesChange={(changedValues, allValues) => {
            // When method changes, reset height_adjustment to null for recalculation
            if (changedValues.height_adjustment_method) {
              setHumanConfig({
                ...allValues,
                height_adjustment: null,
                joint_adjustments: humanConfig.joint_adjustments
              } as HumanConfig);
            } else {
              setHumanConfig({
                ...allValues,
                joint_adjustments: humanConfig.joint_adjustments
              } as HumanConfig);
            }
          }}
        >
          <Form.Item label={t('player.heightAdjustmentMethod')} name="height_adjustment_method">
            <Radio.Group>
              <Radio value="plane_fit"><span style={{ color: 'white' }}>{t('player.planeFit')}</span></Radio>
              <Radio value="offset"><span style={{ color: 'white' }}>{t('player.offset')}</span></Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prevValues, currentValues) =>
            prevValues.height_adjustment_method !== currentValues.height_adjustment_method
          }>
            {({ getFieldValue }) => {
              const method = getFieldValue('height_adjustment_method');
              if (method === 'plane_fit') {
                return (
                  <>
                    <Form.Item label={t('player.heightAdjustment')}>
                      <Space direction="horizontal" size="small" style={{ display: 'flex' }}>
                        <Form.Item name={['height_adjustment', 0]} noStyle>
                          <InputNumber
                            placeholder="a"
                            style={{ width: 180 }}
                            step={0.000001}
                            precision={6}
                          />
                        </Form.Item>
                        <Form.Item name={['height_adjustment', 1]} noStyle>
                          <InputNumber
                            placeholder="b"
                            style={{ width: 180 }}
                            step={0.000001}
                            precision={6}
                          />
                        </Form.Item>
                        <Form.Item name={['height_adjustment', 2]} noStyle>
                          <InputNumber
                            placeholder="c"
                            style={{ width: 180 }}
                            step={0.000001}
                            precision={6}
                          />
                        </Form.Item>
                      </Space>
                    </Form.Item>
                    <Form.Item>
                      <Button
                        type="default"
                        loading={humanConfigCalculating}
                        onClick={async () => {
                          if (!humanConfig || !selectedHumanMotion) return;
                          setHumanConfigCalculating(true);
                          try {
                            // Save config with height_adjustment set to null to trigger auto-calculation
                            const configToSave: HumanConfig = {
                              ...humanConfig,
                              height_adjustment: null,
                              height_adjustment_method: 'plane_fit' as const
                            };
                            const result = await modelApi.saveHumanPlayerConfig(selectedHumanFormat, selectedHumanMotion, configToSave);
                            // Update the form with the calculated values
                            setHumanConfig(result.config);
                            humanConfigForm.setFieldsValue(result.config);
                            message.success(t('player.autoCalculateSuccess'));
                          } catch (err) {
                            console.error('Failed to auto-calculate:', err);
                            message.error(t('player.autoCalculateFailed'));
                          } finally {
                            setHumanConfigCalculating(false);
                          }
                        }}
                      >
                        {t('player.autoCalculate')}
                      </Button>
                    </Form.Item>
                  </>
                );
              } else {
                return (
                  <>
                    <Form.Item label={t('player.heightAdjustment')} name="height_adjustment">
                      <InputNumber style={{ width: '100%' }} placeholder={t('common.autoCalculated')} step={0.01} />
                    </Form.Item>
                    <Form.Item>
                      <Button
                        type="default"
                        loading={humanConfigCalculating}
                        onClick={async () => {
                          if (!humanConfig || !selectedHumanMotion) return;
                          setHumanConfigCalculating(true);
                          try {
                            // Save config with height_adjustment set to null to trigger auto-calculation
                            const configToSave: HumanConfig = {
                              ...humanConfig,
                              height_adjustment: null,
                              height_adjustment_method: 'offset' as const
                            };
                            const result = await modelApi.saveHumanPlayerConfig(selectedHumanFormat, selectedHumanMotion, configToSave);
                            // Update the form with the calculated values
                            setHumanConfig(result.config);
                            humanConfigForm.setFieldsValue(result.config);
                            message.success(t('player.autoCalculateSuccess'));
                          } catch (err) {
                            console.error('Failed to auto-calculate:', err);
                            message.error(t('player.autoCalculateFailed'));
                          } finally {
                            setHumanConfigCalculating(false);
                          }
                        }}
                      >
                        {t('player.autoCalculate')}
                      </Button>
                    </Form.Item>
                  </>
                );
              }
            }}
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
                    // Get current form values
                    const formValues = humanConfigForm.getFieldsValue();
                    const configToSave = {
                      ...humanConfig,
                      ...formValues
                    };

                    // Check if height_adjustment is empty/null and needs auto-calculation
                    const method = formValues.height_adjustment_method || humanConfig.height_adjustment_method;
                    const heightAdjustment = formValues.height_adjustment;

                    let needsAutoCalculation = false;
                    if (method === 'plane_fit') {
                      // For plane_fit, check if any of the three values is null/undefined
                      if (!heightAdjustment ||
                          heightAdjustment[0] === null || heightAdjustment[0] === undefined ||
                          heightAdjustment[1] === null || heightAdjustment[1] === undefined ||
                          heightAdjustment[2] === null || heightAdjustment[2] === undefined) {
                        needsAutoCalculation = true;
                      }
                    } else if (method === 'offset') {
                      // For offset, check if the value is null/undefined
                      if (heightAdjustment === null || heightAdjustment === undefined) {
                        needsAutoCalculation = true;
                      }
                    }

                    // If needs auto-calculation, set height_adjustment to null
                    if (needsAutoCalculation) {
                      configToSave.height_adjustment = null;
                    }

                    const result = await modelApi.saveHumanPlayerConfig(selectedHumanFormat, selectedHumanMotion, configToSave);

                    // If auto-calculation was triggered, update the form with calculated values
                    if (needsAutoCalculation && result.config) {
                      setHumanConfig(result.config);
                      humanConfigForm.setFieldsValue(result.config);
                    }

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