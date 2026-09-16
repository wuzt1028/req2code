# 仓库侦察清单

Phase 0 必做；Phase 5/6/7 需要时做增量侦察。目标：让后续所有设计与编码都建立在仓库的真实约定与可复用资产上，禁止凭空假设。

## 一、先读规范文件

按顺序查找并通读（存在即读，路径记录进 `P0-输入与仓库侦察.md`）：

1. `AGENTS.md` / `CLAUDE.md`（仓库根及子目录）
2. `README.md`、`CONTRIBUTING.md`
3. 构建配置：`pom.xml` / `package.json` / `.editorconfig` / lint 配置
4. 已有同类功能的代码（最好的规范样本）

## 二、后端侦察（Java 默认，其他栈按同构维度替换）

| 维度 | 要提取的内容 |
|---|---|
| 技术栈与版本 | JDK（jenv 管理，1.8/11 并存）、Maven（建议 3.9+）、Lombok、Spring/框架版本 |
| 模块与分层 | 模块划分、Controller/Service/DAO 分层与包结构、DTO/VO/Entity 命名位置 |
| 命名约定 | 类/方法/接口路径/常量命名风格 |
| 异常与响应 | 统一响应体、异常体系、错误码规范 |
| 鉴权 | 认证方式、拦截器/过滤器、权限注解 |
| 接口风格 | REST/RPC、版本策略、分页/排序/幂等约定 |
| DB 访问 | MyBatis/JPA、Mapper/XML 位置、事务方式、缓存/MQ 使用 |
| 多租户与数据可见性 | 租户模型（多租户/单租户）、数据隔离方式、跨租户查询限制、管理租户与业务租户差异 |
| 相似功能 | 找 1-3 个最接近的已有功能，作为实现参照 |
| 复用清单 | 公共组件、工具类、异常/鉴权组件、通用查询、可复用 Service/DAO |

常用检索（用 rg，按需替换关键词）：

```bash
rg -l "关键词" --type java            # 找相似功能
rg "class .*Controller" -g "*.java"   # 看接口层写法
rg "统一响应体类名" -g "*.java"        # 看响应封装惯例
```

## 三、前端侦察

| 维度 | 要提取的内容 |
|---|---|
| 框架与版本 | `package.json` 中的框架、构建工具、Node 版本要求 |
| 组件库 | 组件库及版本、二次封装组件位置 |
| 样式方案 | less/sass/css modules/tailwind、主题变量与设计 token 位置 |
| 请求封装 | axios/fetch 封装位置、错误处理与 loading 惯例 |
| 状态管理 | redux/mobx/zustand 等及 store 组织方式 |
| 路由与权限 | 路由配置位置、权限/菜单控制方式 |
| 交互惯例 | 加载/空态/错误态/禁用的既有组件与写法 |
| 命名约定 | 目录、文件、组件、class 命名 |
| 可访问性基线 | 焦点管理、对比度、键盘操作现状 |
| 复用清单 | 公共组件、hooks、工具函数、布局模板 |

## 四、参考源视觉语言提取（Phase 3 用）

从参考源（默认目标前端仓库）提取 design token，填入 `P3-设计说明.md` 的映射表：

- 色板：主色、语义色（成功/警告/错误/信息）、中性色阶
- 字体：字号阶梯、字重、行高
- 间距：基础间距单位与常用组合
- 圆角与阴影：卡片/弹窗/按钮规格
- 组件模式：表格、表单、弹窗、抽屉、空态、分页的既有样式
- 交互模式：hover/focus/loading/骨架屏/过渡动效
- 提取方式：优先读主题/变量文件与公共组件源码；无法读源码时从截图取样

## 五、环境准备与常用命令

按需检查，缺失时提示用户或协助安装（命令仅供参考，以仓库实际为准）：

**后端**

```bash
jenv versions          # JDK 多版本管理（1.8 / 11）
mvn -v                 # Maven 建议 3.9+
# Lombok 随 IDE/构建配置，检查 pom 中依赖是否已存在
```

**前端**

```bash
node -v
brew install node                       # 未安装时（macOS）
npm install -g n && sudo n 20.18.0      # 版本管理
npm install --legacy-peer-deps -verbose # 安装依赖（进入前端工程）
npm run start                           # 本地启动
npm run build                           # 打包

# 打包报错时依次执行
rm -rf node_modules
rm -rf package-lock.json
npm install --legacy-peer-deps -verbose
npm run build
```

## 六、输出

侦察结论写入 `P0-输入与仓库侦察.md`：

- 摘要进正文（仓库信息表、规范摘要、复用清单、UI/UE 规范、待确认清单）
- 详细提取记录（文件路径、代码位置、token 取值）作为附录或同文件扩展章节
- 每条结论标注来源（文件路径/代码位置）；找不到依据的一律进待确认清单
- 脱敏：密钥、凭据、Token、生产数据一律不写入产物；示例数据脱敏（如 `user***@corp.com`）
