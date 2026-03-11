# Builder 执行顺序

## 原则

1. 严格按 Layer 顺序推进，不跨层抢跑。
2. 单 owner 热点文件不得多人同时修改。
3. 若任务需要修改热点文件，必须回到 owner 任务处理。
4. 生成类动作一律按异步接口设计，不得同步阻塞到最终产物。

## 推荐执行层

- Layer 0：Task 1
- Layer 1：Task 2 + Task 14
- Layer 2：Task 3 + Task 11
- Layer 3：Task 4 + Task 5 + Task 6
- Layer 4：Task 7 + Task 8 + Task 9
- Layer 5：Task 10 + Task 15 + Task 16
- Layer 6：Task 12 + Task 17
- Layer 7：Task 13
- Layer 8：Task 18

## 单 owner 热点

- `backend/app/common/*`
- `backend/app/persistence/base.py`
- `backend/app/persistence/session.py`
- `backend/app/persistence/types.py`
- `backend/alembic/env.py`
- `backend/app/api/router.py`
- `backend/app/api/websocket.py`
- `backend/app/main.py`
- `frontend/app/*`
- `frontend/lib/*`
- `frontend/hooks/useWebSocket.ts`
- `frontend/hooks/useAssetManifest.ts`
- `frontend/hooks/useDraftSync.ts`
