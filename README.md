# 抖音续火花助手

一个你自己搭的抖音续火花工具。装在你自己的服务器上，每天定时帮你在手机上续火花。

说白了就是：你在电脑上扫一次码，之后每天到点它自动打开浏览器帮你发一条消息。不用挂电脑，不用开模拟器，一台便宜的云服务器就够。

⚠️ 这个项目走的是浏览器自动化路线，模拟的是你手动操作。抖音社区公约不允许这么做，有被风控甚至封号的可能。只建议给自己的小号、几个好友用，一天一条。拿去搞批量营销出了事别找我。

## 跟别的项目比，我们做了什么不一样的

市面上续火花的工具大多是这几种路子：

| | GitHub Actions 挂机 | 青龙面板脚本 | 本项目 |
|---|---|---|---|
| 运行环境 | 别人的服务器 | 你自己的服务器 | 你自己的服务器 |
| 操作方式 | fork 仓库、改配置 | 命令行、改 json | 网页界面，手机也能用 |
| 登录态获取 | 手动抓 cookie | 手动抓 cookie | 本地扫码，自动导出 |
| 好友管理 | 手动填名字 | 手动填名字 | 从聊天列表自动拉取，勾选就行 |
| 续火花通道 | 只有 consumer | 只有 consumer | consumer + creator 双通道 |
| 失败补发 | 没有 | 没有 | 45 分钟后自动补发一次 |
| 限流保护 | 没有 | 没有 | 检测到"操作频繁"自动停 |

几个值得说的点：

 不用抓 cookie。其他项目要你从浏览器开发者工具里复制一长串 cookie，容易抄错，过期了还得重新抓。我们这边就是本地跑一个脚本，弹出浏览器，你用手机扫码登录，它自动把登录态存好。上传到服务器就行。

 双通道。大多数工具只走 consumer 私信通道——就是你跟好友已经聊过天的情况。但如果你想给一个从没聊过的好友续火花，consumer 通道发不了。我们加了 creator 通道（从创作者中心发），专门处理这种情况。默认关着，你手动打开才生效。

 失败会补发。发送过程中如果某个好友失败了（网络问题、页面卡住之类的），45 分钟后自动再试一次。一天只补一次，不会反复骚扰。

 好友台账。不用你手动输入好友名字。点一下"同步联系人"，它会从你的抖音聊天列表里把好友拉下来，连火花天数都有。你只需要在表格里勾选要续火花的人，保存就行。下次再进来，勾选状态还在。

 手机能用。网页界面做了响应式，手机浏览器打开就能操作。查看状态、改配置、上传登录态都没问题。

## 东西怎么跑起来的

分成两部分，一部分在你自己电脑上（只跑一次），一部分在服务器上（一直跑着）。

```
你的电脑（一次性）                    服务器（每天自动）
┌─────────────────────┐          ┌──────────────────────────────┐
│ extract_cookie.py   │          │ FastAPI 网页服务              │
│ 打开浏览器           │  上传    │ APScheduler 每天定时触发      │
│ 手机扫码登录         │ ──────▶ │ Playwright 无头浏览器          │
│ 导出 state.json     │          │ 打开 douyin.com/chat           │
└─────────────────────┘          │ 给你勾选的好友发随机文案       │
                                 │ 失败自动重试、限流自动停      │
                                 └──────────────────────────────┘
```

登录态是在你自己电脑上扫码拿到的，服务器只是拿去用。这样不会因为"机房 IP + 异地登录"触发抖音的风控。

## 怎么装

1. 在你电脑上获取登录态

```bash
pip install -r requirements.txt
playwright install chromium
python extract_cookie.py
```

浏览器弹出来，用手机抖音扫码登录。登完之后 `data/state.json` 就生成好了。

2. 上传到服务器

```bash
scp -r . root@你的服务器IP:/opt/douyin-spark
```

3. 在服务器上跑部署脚本

```bash
ssh root@你的服务器IP
cd /opt/douyin-spark
bash deploy/deploy.sh
```

脚本会干这些事：装 Python 依赖、装 Chromium、建 2G swap（内存不够的机器需要）、设时区、生成访问令牌、注册系统服务。跑完会告诉你网页地址和令牌。

4. 打开网页配置

1. 浏览器打开 `http://你的服务器IP`
2. 输入令牌
3. 上传刚才生成的 `state.json`
4. 去"好友与消息"页点"同步联系人"
5. 勾选要续火花的人，保存
6. 先点"模拟运行"看看没问题，再点"立即续火花"

之后就不用管了。每天到点自动跑。登录态过期了网页会标红提醒你，重新跑一遍第 1 步就行。

## 要是想用域名和 HTTPS

有域名的话可以套一层 nginx + certbot：

```bash
apt-get install -y nginx certbot python3-certbot-nginx

cat > /etc/nginx/sites-available/douyin-spark <<'EOF'
server {
    listen 80;
    server_name 你的域名.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
EOF

ln -s /etc/nginx/sites-available/douyin-spark /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

certbot --nginx -d 你的域名.com --non-interactive --agree-tos \
  --register-unsafely-without-email --redirect
```

`.env` 里加上 `HOST=127.0.0.1`，让后端只监听本机，然后 `systemctl restart douyin-spark`。

## 它怎么保护你不被风控

- 切换校验：点开一个好友之后，会先确认右侧聊天窗口的标题确实是这个人，再发消息。不会发给上一个人。
- 搜索兜底：好友不在聊天列表里（比如你清过最近聊天），会自动搜索找到这个人再打开会话。
- 发送校验：文字进输入框、按回车、文字离开输入框，三步都过了才算发送成功。失败自动重试一次。
- 当日补发：这一轮有失败的好友，45 分钟后再只对失败的人补发一次。全部成功就不补了。
- 限流熔断：页面上出现"操作频繁""安全验证"之类的提示，立刻停掉这一轮，不重试。
- 节奏拟人化：发送时间有随机抖动，好友之间有随机间隔，文案从模板库里随机选。不会每天同一秒、同一句话。

## 常见问题

登录态过期了怎么办
在你电脑上重新跑 `python extract_cookie.py`，扫码，重新上传 `state.json`。登录态一般能维持几天到几周。

好友切换失败
优先用"同步联系人"拉取（取的是聊天列表里的真实显示名）。手动填写的时候用完整的备注或昵称。

提示操作频繁
把"好友间隔"调大，减少每次发送的人数。少量好友（十几个以内）最稳。

服务器 IP 被风控
尽量选跟你日常登录城市一样的国内机房。海外机房的 IP 容易触发验证码。

网页打不开
检查防火墙有没有放行 80 端口，跑一下 `systemctl status douyin-spark` 看服务是不是正常。

## 安全

- 访问令牌是随机生成的，存在 `.env` 文件里。建议在防火墙层限制只有你自己的 IP 能访问管理界面。
- `state.json` 包含你的账号登录信息，属于敏感数据。`data/` 和 `.env` 都在 `.gitignore` 里，不会被提交到仓库。
- 后端只监听 `127.0.0.1:8000`，公网通过 nginx 的 80 端口访问。防火墙不需要开放 8000。

## 目录结构

```
app.py                          FastAPI 服务入口
extract_cookie.py               本机获取登录态脚本
requirements.txt                Python 依赖
.env.example                    环境变量模板
core/
  automation.py                 Playwright 自动化发送逻辑
  config.py                     配置读写
  guard.py                      限流关键词检测
  ledger.py                     好友台账管理
  runtime.py                    状态、日志、运行记录
  scheduler.py                  定时调度
  harvester/
    creator_map.py              抖音号采集
  sender/
    creator_channel.py          首条消息通道
deploy/
  deploy.sh                     一键部署脚本
  douyin-spark.service          systemd 服务文件
static/
  index.html                    网页管理界面（Vue 3 + Element Plus）
  vendor/                       前端资源
```

## 致谢

基于 [douyin-spark](https://github.com/Xiaowu-0916/douyin-spark) 二次开发，在原版的网页管理、定时发送、限流保护等基础上，新增了好友台账、双通道发送、抖音号采集等功能。

发送流程和部署思路也参考了：

- [douyin-cloud-streak](https://github.com/Yuriz132/douyin-cloud-streak)
- [DouYinSparkFlow](https://github.com/2061360308/DouYinSparkFlow)
- [TikTokAutoSparkWeb](https://github.com/DkoBot/TikTokAutoSparkWeb)

## License

[MIT](./LICENSE)
