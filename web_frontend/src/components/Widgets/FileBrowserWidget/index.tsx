import React, { useState, useEffect, useMemo } from 'react';
import { FolderOpenOutlined, FileOutlined, FolderOutlined, CaretRightOutlined, CaretDownOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { modelApi, MotionTreeNode, MotionFileInfo } from '../../../api/client';
import './index.css';

interface FileBrowserWidgetProps {
  generatorType: 'bvh' | 'smpl';
  onFileSelect: (relativePath: string, filename: string) => void;
  selectedFile?: string;
}

const FileBrowserWidget: React.FC<FileBrowserWidgetProps> = ({
  generatorType,
  onFileSelect,
  selectedFile
}) => {
  const { t } = useTranslation();
  const [motionTree, setMotionTree] = useState<Record<string, MotionTreeNode> | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentPath, setCurrentPath] = useState<string[]>([]);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadMotionTree();
  }, []);

  const loadMotionTree = async () => {
    try {
      setLoading(true);
      const tree = await modelApi.listMotionsTree();
      setMotionTree(tree);
      // Auto-expand root folders
      const rootFolders = Object.keys(tree[generatorType]?.subdirs || {});
      setExpandedFolders(new Set(rootFolders.map(f => `${generatorType}/${f}`)));
    } catch (error) {
      console.error('Failed to load motion tree:', error);
    } finally {
      setLoading(false);
    }
  };

  const currentNode = useMemo(() => {
    if (!motionTree || !motionTree[generatorType]) return null;

    let node: MotionTreeNode = motionTree[generatorType];
    for (const folder of currentPath) {
      if (!node.subdirs[folder]) return null;
      node = node.subdirs[folder];
    }
    return node;
  }, [motionTree, generatorType, currentPath]);

  const rootNode = motionTree?.[generatorType];

  const toggleFolder = (folderPath: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev);
      if (next.has(folderPath)) {
        next.delete(folderPath);
      } else {
        next.add(folderPath);
      }
      return next;
    });
  };

  const navigateToFolder = (folderPath: string[], folderName: string) => {
    setCurrentPath([...folderPath, folderName]);
  };

  const getBreadcrumbs = () => {
    return [
      { name: generatorType, path: [] },
      ...currentPath.map((folder, index) => ({
        name: folder,
        path: currentPath.slice(0, index + 1)
      }))
    ];
  };

  const renderFolderTree = (node: MotionTreeNode, path: string[], depth: number = 0) => {
    const subdirs = Object.entries(node.subdirs);

    return subdirs.map(([folderName, folderNode]) => {
      const folderPath = [...path, folderName];
      const fullPath = `${generatorType}/${folderPath.join('/')}`;
      const isExpanded = expandedFolders.has(fullPath);

      return (
        <div key={folderName} className="fbw-folder-item" style={{ paddingLeft: depth * 16 }}>
          <div
            className="fbw-folder-row"
            onClick={() => toggleFolder(fullPath)}
          >
            <span className="fbw-expand-icon">
              {isExpanded ? <CaretDownOutlined /> : <CaretRightOutlined />}
            </span>
            {isExpanded ? <FolderOpenOutlined /> : <FolderOutlined />}
            <span className="fbw-folder-name">{folderName}</span>
          </div>
          {isExpanded && (
            <div className="fbw-folder-children">
              {renderFolderTree(folderNode, folderPath, depth + 1)}
            </div>
          )}
        </div>
      );
    });
  };

  const handleFileClick = (file: MotionFileInfo) => {
    onFileSelect(file.relative_path, file.filename);
  };

  if (loading) {
    return <div className="fbw-loading">{t('configPanel.loading')}</div>;
  }

  if (!motionTree || !rootNode) {
    return <div className="fbw-empty">{t('configPanel.noData')}</div>;
  }

  const hasRootFiles = rootNode.motions.length > 0;
  const hasSubfolders = Object.keys(rootNode.subdirs).length > 0;

  return (
    <div className="file-browser-widget">
      {/* Breadcrumb Navigation */}
      <div className="fbw-breadcrumb">
        {getBreadcrumbs().map((crumb, index) => (
          <span key={index}>
            {index > 0 && <span className="fbw-breadcrumb-sep">/</span>}
            <span
              className={`fbw-breadcrumb-item ${index === getBreadcrumbs().length - 1 ? 'active' : ''}`}
              onClick={() => {
                if (index < getBreadcrumbs().length - 1) {
                  setCurrentPath(crumb.path);
                }
              }}
            >
              {crumb.name}
            </span>
          </span>
        ))}
      </div>

      <div className="fbw-content">
        {/* Left: Folder Tree */}
        {currentPath.length === 0 && (
          <div className="fbw-sidebar">
            {hasSubfolders && (
              <div className="fbw-sidebar-section">
                <div className="fbw-sidebar-title">{t('fileBrowser.folders')}</div>
                {renderFolderTree(rootNode, [])}
              </div>
            )}
            {hasRootFiles && (
              <div className="fbw-sidebar-section">
                <div className="fbw-sidebar-title">{t('fileBrowser.rootFiles')}</div>
                <div className="fbw-root-files">
                  {rootNode.motions.map(file => (
                    <div
                      key={file.relative_path}
                      className={`fbw-file-item ${selectedFile === file.relative_path ? 'selected' : ''}`}
                      onClick={() => handleFileClick(file)}
                    >
                      <FileOutlined />
                      <span className="fbw-file-name">{file.filename}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Right: Current Directory Files */}
        {currentPath.length > 0 && currentNode && (
          <div className="fbw-file-list">
            {currentNode.motions.length === 0 && Object.keys(currentNode.subdirs).length === 0 ? (
              <div className="fbw-empty-dir">{t('fileBrowser.emptyFolder')}</div>
            ) : (
              <>
                {/* Subdirectories */}
                {Object.entries(currentNode.subdirs).map(([folderName, folderNode]) => (
                  <div
                    key={folderName}
                    className="fbw-file-item folder"
                    onClick={() => navigateToFolder(currentPath, folderName)}
                  >
                    <FolderOutlined />
                    <span className="fbw-file-name">{folderName}</span>
                    <span className="fbw-file-count">
                      {folderNode.motions.length} {t('fileBrowser.files')}
                    </span>
                  </div>
                ))}
                {/* Files */}
                {currentNode.motions.map(file => (
                  <div
                    key={file.relative_path}
                    className={`fbw-file-item ${selectedFile === file.relative_path ? 'selected' : ''}`}
                    onClick={() => handleFileClick(file)}
                  >
                    <FileOutlined />
                    <span className="fbw-file-name">{file.filename}</span>
                    <span className="fbw-file-type">{file.type.toUpperCase()}</span>
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        {/* Show files when in root */}
        {currentPath.length === 0 && (
          <div className="fbw-file-list">
            {!hasSubfolders && rootNode.motions.map(file => (
              <div
                key={file.relative_path}
                className={`fbw-file-item ${selectedFile === file.relative_path ? 'selected' : ''}`}
                onClick={() => handleFileClick(file)}
              >
                <FileOutlined />
                <span className="fbw-file-name">{file.filename}</span>
                <span className="fbw-file-type">{file.type.toUpperCase()}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default FileBrowserWidget;