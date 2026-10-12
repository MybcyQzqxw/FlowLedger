# FlowLedger

*Turn bank income screenshots into a tidy Excel ledger.*

FlowLedger 是一个桌面小工具：把手机上的银行“进账明细”截图拖进来，自动（离线 OCR）提取交易信息并汇总到 Excel 表格中，同时把截图按“时间-金额”归档。最终以单个 `.exe` 分发，无需安装 Python 或任何依赖。

## 界面与功能

1. **Excel 文件**（顶部）：左侧输入框可直接输入绝对路径，右侧按钮选择文件。默认 `D:\mine\！文件\报销\！银行卡\银行卡.xlsx`；可指向尚不存在的 `.xlsx`，首次上传时自动创建。
2. **截图存放目录**：格式同上，默认 `D:\mine\！文件\报销\！银行卡\截图`（不存在时自动创建）。修改后的路径会被记住，下次启动沿用。
3. **拖放区**：支持拖放（窗口任意位置均可）、**Ctrl+V 粘贴**、“浏览文件…”、手动输入路径（分号分隔）四种方式，可一次选多张。粘贴需要先**点击拖放框激活**（框变为玫红实线并显示“粘贴已激活”，终端同步提示），**再次点击拖放框则取消**；未激活时 Ctrl+V 不会添加截图，路径输入框的文本粘贴也完全不受影响。激活后支持粘贴微信等处复制的图片（无论剪贴板里是文件还是图片本身；后者会先存为临时 PNG，上传/移除/退出后自动清理），激活状态下焦点在路径输入框时，剪贴板为纯文本仍是普通粘贴，只有含图片/文件时才会作为截图添加。按文件**内容**判断是否为图片，兼容 PNG / JPG / JPE / JFIF / BMP / GIF / WebP / TIFF / HEIC / HEIF / AVIF / JPEG2000 / ICO / TGA / PPM 等（含带透明通道、EXIF 旋转、改过扩展名或无扩展名的图片）；PDF、文本等非图片文件会被拒绝并在终端提示。
4. **按钮**（左侧两个大按钮，右侧上下两个小按钮）
   - **上传**：逐张识别截图 → 查重 → 录入 Excel → 将图片**统一保存为 JPG**（原本就是正向 JPEG 的按字节原样复制，不二次压缩；其他格式转为高质量 JPG，透明背景填白，按 EXIF 方向摆正），命名为 `YYYYMMDD_HHMMSS-金额.jpg`（如 `20260930_101630-3286.45.jpg`；同名时追加 `_2`）。原图不会被改动。
   - **导出**：弹出对话框选择导出目录（默认桌面），确认后将 Excel 复制到该目录。
   - **检查**：用系统默认程序打开 Excel 文件。
   - **删改**：弹出对话框展示 Excel 全部内容，左侧一列复选框（顶部有“全选”，点击行任意位置也可勾选），底部四个按钮：**删除**（删除已勾选的行，快捷键 Delete）、**撤销**（逐步回退上一次删除，快捷键 Ctrl+Z）、**取消**（不修改 Excel 并关闭）、**保存**（确认后把修改写入 Excel 并关闭）。所有操作都在内存副本上进行，点“保存”前 Excel 不会改动；有未保存的修改时取消/关闭会二次确认。保存后金额总计自动更新；**同时会把截图目录中对应的图片（`时间-金额.jpg`）移入回收站**，误删可从回收站找回。保存前的确认框会写明将删除多少条记录、多少张图片；先写入 Excel，成功后才删图片，保存失败则图片不会被动。图片不存在时仅提示跳过；若有多条记录的时间和金额完全相同（图片名带 `_2` 等后缀），无法确定图片归属，会保留图片并在终端提示手动处理。上传进行中该按钮不可用。
5. **终端**：实时显示提示、警告与报错。

## 提取字段（Excel 表头）

`交易时间 | 付款方名称 | 付款方账号 | 交易类型 | 交易渠道 | 具体信息 | 收入金额 | 备注`

- 付款方名称/账号取自截图的“对方名称/对方账号”。
- **备注**为“附言”的全文；**具体信息**为附言中去掉数字和符号后保留的文字（如 `6254797:202609D067549:专用材料购置` → `专用材料购置`）。
- 识别基于标签定位（而非固定坐标），截图中的状态栏、广告等无关内容会被忽略，附言换行也能正确拼接。

## Excel 样式

- 全部中文（含全角标点）为**楷体**，全部西文（字母、数字、符号）为 **Times New Roman**；同一单元格内中西文混排时按字符分别设置。
- 表头加粗、深蓝底白字、居中，首行冻结，带筛选按钮；数据行斑马纹 + 细边框；时间显示为 `yyyy-mm-dd hh:mm:ss`，金额带千分位与两位小数；列宽按内容自动调整；已设置横向打印、整页宽度、每页重复表头。
- 最下方为醒目的**金额总计**行（金色底、加大加粗红字），使用 `=SUM(...)` 公式，每次录入后自动更新位置与范围，手动修改金额也会自动重算。总计行不会被当作数据参与查重和排序。

## 录入规则

- **查重**：交易时间、收入金额、付款方账号完全一致，且备注（忽略空格/标点差异）一致或高度相似，即视为重复——这样即使 OCR 对同一张图出现全/半角标点之类的细微波动，也不会漏判。重复时终端给出警告并指出与表格第几行相同，不写入 Excel，图片也不会进入截图目录。
- **排序**：每次录入后，全部记录按交易时间升序重新排列。
- **失败处理**：无法识别交易时间/金额、Excel 被占用等情况会在终端报错，对应图片不会上传，并保留在列表中供重试。
- 上传前请先关闭已在 Excel 中打开的目标文件，否则无法写入。
- 仅支持进账（收入）截图；支出类截图会被拒绝。
- 表头必须为上述 8 列（空表会自动写入表头），否则拒绝写入以免破坏已有数据。每次写入会按上述样式重新整理数据行，请勿在数据区域内放置其他内容。

## 项目结构

```
FlowLedger/
├─ src/
│  ├─ main.py                     # 入口
│  └─ flowledger/
│     ├─ main_window.py           # 主窗口
│     ├─ worker.py                # 后台上传流水线（QThread）
│     ├─ extractor.py             # RapidOCR + 版面解析
│     ├─ excel_store.py           # Excel 读写、查重、排序
│     ├─ excel_style.py           # Excel 字体/配色/总计行
│     ├─ screenshots.py           # 记录与截图的对应关系、移入回收站
│     ├─ image_utils.py           # 图片校验/加载/缩略图/转 JPG
│     ├─ theme.py                 # 浅粉色主题样式
│     ├─ constants.py
│     └─ widgets/                 # 终端、拖放区、路径选择器、导出/删改对话框
├─ requirements.txt
├─ build.bat                      # 一键打包
└─ favicon.ico
```

## 开发与运行

```bat
conda create -n flowledger python=3.11 -y
conda activate flowledger
pip install -r requirements.txt
python src\main.py
```

## 打包

**前置条件**：已安装 Miniconda / Anaconda，且 `conda` 在 PATH 中（建议在 *Anaconda Prompt* 中执行）。

在项目根目录执行：

```bat
:: cmd / Anaconda Prompt
build.bat
```

```powershell
# PowerShell（当前目录下的脚本必须带 .\ 前缀）
.\build.bat
```

脚本依次完成：检查 conda → 创建 `flowledger` 环境（Python 3.11，已存在则跳过）→ `pip install -r requirements.txt` → PyInstaller 打包单文件 exe（内含 OCR 模型）→ 复制到 `release\`。首次打包需下载依赖，耗时较长。

产物：`release\FlowLedger.exe`（约 150 MB，免安装，可直接分发）。结束时脚本会询问是否打开输出目录，并 `pause` 等待按键。

<details>
<summary>不使用 build.bat，手动打包</summary>

```bat
conda activate flowledger
python -m PyInstaller --noconfirm --clean --onefile --windowed --name FlowLedger --paths src ^
    --collect-all rapidocr_onnxruntime --collect-all pillow_heif --add-data "favicon.ico;." --icon favicon.ico src\main.py
```

生成的 exe 位于 `dist\FlowLedger.exe`。

</details>

## 技术栈

PySide6（界面）· RapidOCR / onnxruntime（离线 OCR）· Pillow + pillow-heif（图片）· openpyxl（Excel）· PyInstaller（打包）
