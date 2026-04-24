import React, { useState, useEffect } from 'react';
import { FolderOutlined, FileOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { modelApi, MotionTreeNode, MotionFileInfo } from '../../../api/client';
import './index.css';

interface FileBrowserWidgetProps {
  generatorType: 'bvh' | 'smpl';
  onFileSelect: (relativePath: string, filename: string) => void;
  selectedFile?: string;
}

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

const FileBrowserWidget: React.FC<FileBrowserWidgetProps> = ({
  generatorType,
  onFileSelect,
  selectedFile
}) => {
  const { t } = useTranslation();
  const [motionTree, setMotionTree] = useState<Record<string, MotionTreeNode> | null>(null);
  const [loading, setLoading] = useState(true);
  const [columns, setColumns] = useState<ColumnData[]>([]);

  useEffect(() => {
    loadMotionTree();
  }, []);

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
    try {
      setLoading(true);
      const tree = await modelApi.listMotionsTree();
      setMotionTree(tree);
    } catch (error) {
      console.error('Failed to load motion tree:', error);
    } finally {
      setLoading(false);
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
    onFileSelect(file.relative_path, file.filename);
  };

  const handleColumnClick = (columnIndex: number) => {
    if (columnIndex < columns.length - 1) {
      setColumns(prev => prev.slice(0, columnIndex + 1));
    }
  };

  const getBreadcrumbs = () => {
    const crumbs: { name: string; path: string[] }[] = [{ name: generatorType, path: [] }];
    columns.forEach((col) => {
      if (col.path.length > 0) {
        crumbs.push({ name: col.path[col.path.length - 1], path: col.path });
      }
    });
    return crumbs;
  };

  if (loading) {
    return <div className="fbw-loading">{t('configPanel.loading')}</div>;
  }

  if (!motionTree || !motionTree[generatorType]) {
    return <div className="fbw-empty">{t('configPanel.noData')}</div>;
  }

  return (
    <div className="file-browser-widget">
      {/* Breadcrumb Navigation */}
      <div className="fbw-breadcrumb">
        {getBreadcrumbs().map((crumb, index) => (
          <span key={index}>
            {index > 0 && <span className="fbw-breadcrumb-sep">/</span>}
            <span
              className={`fbw-breadcrumb-item ${index === getBreadcrumbs().length - 1 ? 'active' : ''}`}
              onClick={() => index < getBreadcrumbs().length - 1 && handleColumnClick(index)}
            >
              {crumb.name}
            </span>
          </span>
        ))}
      </div>

      {/* Multi-column Content */}
      <div className="fbw-columns-container">
        {columns.map((column, columnIndex) => (
          <div key={columnIndex} className="fbw-column">
            <div className="fbw-column-header">
              {column.path.length === 0 ? generatorType : column.path[column.path.length - 1]}
            </div>
            <div className="fbw-column-content">
              {column.folders.length === 0 && column.files.length === 0 ? (
                <div className="fbw-empty-column">{t('fileBrowser.emptyFolder')}</div>
              ) : (
                <>
                  {column.folders.map(folder => (
                    <div
                      key={folder.name}
                      className="fbw-column-item folder"
                      onClick={() => handleFolderClick(columnIndex, folder)}
                    >
                      <span className="fbw-item-icon">
                        <FolderOutlined />
                      </span>
                      <span className="fbw-item-name">{folder.name}</span>
                      <span className="fbw-item-count">
                        {folder.node.motions.length}
                      </span>
                      <span className="fbw-item-chevron">›</span>
                    </div>
                  ))}
                  {column.files.map(file => (
                    <div
                      key={file.relative_path}
                      className={`fbw-column-item ${selectedFile === file.relative_path ? 'selected' : ''}`}
                      onClick={() => handleFileClick(file)}
                    >
                      <span className="fbw-item-icon">
                        <FileOutlined />
                      </span>
                      <span className="fbw-item-name">{file.filename}</span>
                      <span className="fbw-item-type">{file.type.toUpperCase()}</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default FileBrowserWidget;
