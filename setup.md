## 环境准备

### 后端（Python）

```bash
conda create -n pypi python=3.12
conda activate pypi
pip install -r requirements.txt
```

`.env` 文件（放在项目根目录，不要提交到 git）：

```
DEEPSEEK_API_KEY=sk-你的DeepSeekKey
BOCHA_API_KEY=sk-你的博查Key
```

### 前端（Vue 3 + Vite）

需要 Node.js 18+（推荐 20+）。**前端不需要 conda 环境**，在普通终端里跑即可。

```bash
cd frontend
npm install
npm run dev
```

## 项目运行

需要开**两个终端**（前端 + 后端），前端终端**不要** `conda activate`。

### 终端 1：后端 WebSocket 服务

```bash
conda activate pypi
uvicorn src.server.ws_server:app --reload --port 8000
```

### 终端 2：前端

```bash
cd frontend
npm run dev
```

浏览器打开 `http://localhost:5173`。

### 可选：原始终端 REPL

不用 Web 界面时，可以直接跑终端版：

```bash
conda activate pypi
python agent_main.py
```