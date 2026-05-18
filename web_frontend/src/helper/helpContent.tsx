import React from 'react';

export interface HelpSubsection {
  id: string;
  title: string;
  content: React.ReactNode;
}

export interface HelpSection {
  id: string;
  title: string;
  subsections: HelpSubsection[];
}

export const helpContent: HelpSection[] = [
  {
    id: 'retargeter',
    title: '重定向器',
    subsections: [
      {
        id: 'retargeting-workflow',
        title: '重定向流程',
        content: (
          <>
            <h3>操作步骤</h3>
            <ol>
              <li>确保待重定向的动捕文件的人体配置已经设置（在播放器→人体动作→人体配置中设置）</li>
              <li>在"重定向器"页面选择机器人、动捕文件格式(bvh,smpl)和动捕文件</li>
              <li>加载或配置重定向参数</li>
              <li>点击"重定向"按钮</li>
              <li>等待处理完成</li>
              <li>完成后可以在可视化界面查看结果</li>
            </ol>
          </>
        ),
      },
      {
        id: 'robot-settings',
        title: '机器人设置',
        content: (
          <>
            <h3>选择机器人模型</h3>
            <ol>
              <li>从下拉菜单中选择目标机器人模型</li>
              <li>系统支持的机器人模型通过 <code>hurodes</code> 库提供</li>
              <li>常见机器人模型包括：
                <ul>
                  <li>DumBot13-21dof</li>
                  <li>unitree-g1-29dof</li>
                  <li>其他自定义机器人模型</li>
                </ul>
              </li>
            </ol>

            <h3>机器人相关参数</h3>
            <ul>
              <li>机器人的髋关节、膝关节、脚部等关键部位由hurodes定义(见HURODES_ASSETS_PATH/robots/robot_name/meta.yaml)</li>
              <li><strong>Base Link X\Y 偏移</strong>: 表示机器人和人体的相对位置，通常均为0</li>
              <li><strong>Base Link 旋转</strong>: 动捕文件坐标系和机器人坐标系的关系，通常和文件格式绑定，一般不需要修改</li>
              <li>系统会自动计算机器人的腿长等物理参数</li>
            </ul>
          </>
        ),
      },
      {
        id: 'human-parameters',
        title: '人体参数',
        content: (
          <>
            <h3>配置说明</h3>
            <p>人体参数需要在播放器的"人体配置"中预先设置（详见 播放器→人体配置）。人体参数用于计算人体与机器人的比例关系。</p>
            <p>其缩放方法为：计算机器人和人体髋到脚的长度，进行等比例缩放。</p>

            <h3>身体比例调整</h3>
            <ul>
              <li>
                <strong>extra_body_ratio</strong>: 全局身体比例缩放 [x, y, z]（默认 [1.0, 1.0, 1.0]）
                <ul>
                  <li>用于整体调整人体模型的尺寸以匹配机器人</li>
                </ul>
              </li>
              <li>
                <strong>relative_body_ratio_dict</strong>: 相对身体比例字典
                <ul>
                  <li>针对特定身体部位的局部比例调整</li>
                  <li>格式：<code>{`{"body_name": [x, y, z]}`}</code>，代表每个方向缩放的比例</li>
                </ul>
              </li>
            </ul>

            <h3>身体旋转调整</h3>
            <ul>
              <li>
                <strong>body_rotate_dict</strong>: 身体部位旋转字典
                <ul>
                  <li>针对特定身体部位的旋转调整</li>
                  <li>格式：<code>{`{"body_name": [roll, pitch, yaw]}`}</code></li>
                </ul>
              </li>
            </ul>
          </>
        ),
      },
      {
        id: 'retargeting-parameters',
        title: '重定向参数',
        content: (
          <>
            <h3>跟踪器配置 (tracker_dict)</h3>
            <p>定义人体关键点与机器人关键点的对应关系，每个跟踪器组包含：</p>
            <ul>
              <li><strong>human</strong>: 人体关键点名称列表</li>
              <li><strong>robot</strong>: 对应的机器人关键点名称列表</li>
              <li><strong>position_cost</strong>: 位置匹配权重（控制位置跟踪的重要性）</li>
              <li><strong>orientation_cost</strong>: 方向匹配权重（控制姿态跟踪的重要性）</li>
            </ul>

            <h3>优化参数</h3>
            <ul>
              <li>
                <strong>damping_cost</strong>: 阻尼代价系数（默认 5.0）
                <ul>
                  <li>用于平滑运动，防止抖动</li>
                  <li>值越大，运动越平滑但可能损失精度</li>
                </ul>
              </li>
            </ul>
          </>
        ),
      },
      {
        id: 'config-save-load',
        title: '保存和加载配置',
        content: (
          <>
            <h3>保存配置</h3>
            <ol>
              <li>配置完参数后，点击"保存配置"按钮</li>
              <li>输入配置名称（例如：<code>default_config</code>）</li>
              <li>配置文件保存在 <code>$RETARGETING_PATH/configs/{`{robot_name}/{config_name}/`}</code></li>
              <li><strong>注意：每次重定向时要对配置进行保存，否则修改不会生效</strong></li>
            </ol>

            <h3>加载配置</h3>
            <ol>
              <li>点击"加载配置"按钮</li>
              <li>从列表中选择已保存的配置</li>
              <li>系统会自动填充所有参数</li>
            </ol>
          </>
        ),
      },
    ],
  },
  {
    id: 'player',
    title: '播放器',
    subsections: [
      {
        id: 'motion-formats',
        title: '动作格式',
        content: (
          <>
            <h3>支持的人体模型格式</h3>
            <ul>
              <li>
                <strong>SMPL 格式</strong> (<code>.npz</code> 文件)：
                <ul>
                  <li>必需字段：<code>trans</code>, <code>poses</code>, <code>betas</code>, <code>mocap_framerate</code>, <code>gender</code></li>
                  <li>SMPL 是参数化人体模型，通过形状参数 (betas) 和姿态参数 (poses) 表示人体</li>
                  <li>支持不同性别模型：male, female, neutral</li>
                </ul>
              </li>
              <li>
                <strong>BVH 格式</strong> (<code>.bvh</code> 文件)：
                <ul>
                  <li>标准 BVH 格式规范</li>
                  <li>包含骨骼层级结构和运动数据</li>
                  <li>广泛用于动作捕捉和动画制作</li>
                </ul>
              </li>
            </ul>
          </>
        ),
      },
      {
        id: 'human-configuration',
        title: '人体配置',
        content: (
          <>
            <h3>配置说明</h3>
            <p>人体配置是针对每个动作捕捉文件的特定配置，是重定向必须的配置。该配置负责计算人体与机器人的比例关系、调整人体高度、调整人体关节偏移。</p>

            <h3>必需参数</h3>
            <ul>
              <li><strong>hip_names</strong>: 髋关节名称列表（左右髋关节）</li>
              <li><strong>hip_offset</strong>: 髋关节偏移量</li>
              <li><strong>foot_names</strong>: 脚部名称列表（左右脚）</li>
              <li><strong>foot_offset</strong>: 脚部偏移量</li>
              <li><strong>height_adjustment</strong>: 高度调整值，用于地面对齐(点击自动计算即可)</li>
              <li><strong>height_adjustment_method</strong>: 高度调整方法（<code>plane_fit</code> 或 <code>offset</code>）</li>
            </ul>

            <h3>高度调整说明</h3>
            <p>由于动捕设备的偏差，导致平面是倾斜的。我们采用了平面拟合或偏移的方法处理。平面拟合（<code>plane_fit</code>）的参数a、b、c通过计算 <code>height = ax + by + c</code> 确认一块平面，对人体高度进行修正。</p>
          </>
        ),
      },
      {
        id: 'robot-motion-playback',
        title: '机器人动作播放',
        content: (
          <>
            <p>选择机器人名称和重定向后的文件即可查看</p>
          </>
        ),
      },
    ],
  },
  {
    id: 'toolbox',
    title: '工具箱',
    subsections: [
      {
        id: 'motion-cutting',
        title: '人体动作切割、机器人动作切割',
        content: (
          <>
            <p>该工具用于将一个动捕动作切割为多段，输入格式为帧的位置，用逗号隔开。</p>
            <p><strong>例如</strong>：输入 <code>400,600</code> 会得到 0-400, 400-600, 600- 三个文件</p>
          </>
        ),
      },
    ],
  },
  {
    id: 'viewer-controls',
    title: '3D查看器操作说明',
    subsections: [
      {
        id: 'mouse-operations',
        title: '鼠标操作',
        content: (
          <>
            <ul>
              <li><strong>左键拖拽</strong>: 旋转视角</li>
              <li><strong>右键拖拽</strong>: 平移视角</li>
              <li><strong>滚轮</strong>: 缩放视角</li>
            </ul>
          </>
        ),
      },
    ],
  },
  {
    id: 'support',
    title: '技术支持',
    subsections: [
      {
        id: 'technical-support',
        title: '获取帮助',
        content: (
          <>
            <p>如有问题，请访问：</p>
            <ul>
              <li>
                <a href="https://github.com/humanoid-retargeting/issues" target="_blank" rel="noopener noreferrer">
                  GitHub Issues
                </a>
              </li>
            </ul>
          </>
        ),
      },
    ],
  },
];
