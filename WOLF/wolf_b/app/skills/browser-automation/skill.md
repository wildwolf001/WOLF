# Browser Automation Skill

## Description
使用Playwright进行浏览器自动化操作的能力

## Capabilities
- 网页导航和交互
- 表单填写和提交
- 元素点击和选择
- 内容提取和截图
- JavaScript执行

## Usage
当用户请求浏览网页、执行Web操作或需要与网站交互时使用此技能。

## Tools
- `browser_service`: 浏览器自动化服务
  - `navigate(url)`: 导航到URL
  - `click(selector)`: 点击元素
  - `fill(selector, text)`: 填写表单
  - `screenshot()`: 截图
  - `get_text(selector)`: 获取文本

## Examples
- "打开Google并搜索..."
- "帮我填写这个表单"
- "截取当前页面"
- "点击登录按钮"

## Notes
- 需要安装playwright: `pip install playwright && playwright install`
- 默认使用无头模式
- 所有操作都经过安全验证