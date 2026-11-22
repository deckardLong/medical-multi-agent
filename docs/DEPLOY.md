# Deploy AURELIA: Vercel (frontend) + Render (backend)

```text
Trình duyệt ──► Vercel: React (frontend/)             VITE_API_BASE
     │
     └────────► Render Web Service (Docker): FastAPI + agent + BGE-M3 + PaddleOCR
                   ├─► Render Postgres                 PRODUCT_DATABASE_URL (tự nối)
                   ├─► Render Disk /var/data           ảnh đơn thuốc, avatar
                   ├─► Qdrant Cloud                    QDRANT_URL, QDRANT_API_KEY
                   ├─► LLM/VLM (OpenAI-compatible)     PRODUCT_LLM_BASE_URL, ...
                   └─► Tavily, SMTP                    (tuỳ chọn)
```

Frontend gọi **thẳng** API trên Render (không proxy qua Vercel), vì mỗi câu chat có thể mất 20–60 giây.

## 0. Hai quyết định trước khi deploy

### LLM / VLM: chạy ở đâu?

Render không có GPU. Chạy model 7B trên CPU của Render cần khoảng 8GB RAM mỗi model và mỗi câu trả lời
mất vài phút, nên không dùng được. Code gọi LLM qua endpoint **tương thích OpenAI**, nên chỉ cần đổi biến môi trường:

| Phương án | Biến môi trường | Ưu | Nhược |
|---|---|---|---|
| **A. Giữ Ollama trên máy bạn**, mở ra ngoài bằng [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) | `PRODUCT_LLM_BASE_URL=https://<tunnel>/v1` | Dữ liệu sức khoẻ không qua bên thứ ba; không tốn tiền model | Máy phải bật 24/7; tốc độ như hiện tại; phải tự chặn truy cập lạ vào tunnel (Cloudflare Access) |
| **B. Nhà cung cấp LLM có API tương thích OpenAI** | `PRODUCT_LLM_BASE_URL`, `PRODUCT_LLM_API_KEY`, tên model theo nhà cung cấp | Nhanh, không phụ thuộc máy bạn | **Câu hỏi và ảnh đơn thuốc được gửi cho bên thứ ba**: phải sửa câu "Mọi model đều chạy local" trong README, và đọc chính sách dữ liệu của nhà cung cấp. Cần nhà cung cấp có cả model **vision** cho 2 agent đọc ảnh |
| C. Server GPU riêng chạy Ollama/vLLM | như A | Chủ động, nhanh | Đắt nhất, phải tự vận hành |

Với dự án cá nhân, nên **bắt đầu bằng A**: không tốn tiền model, và dữ liệu giữ nguyên như khi chạy local.
Khi cần chạy ổn định thì chuyển sang B hoặc C.

### Qdrant: collection ~3M điểm

Collection hiện tại (`r2ai__bge-m3-v1-b6048a__e50d`) để vector gốc trên đĩa, chỉ giữ bản int8 trong RAM. Ước lượng
cần **~4GB RAM, ~25–30GB đĩa**. Gói miễn phí của Qdrant Cloud (1GB RAM) **không đủ**. Hai cách:

- **Thuê cluster đủ lớn** rồi chuyển nguyên collection sang bằng snapshot (mục 1).
- **Index một phần** (ví dụ chỉ tiếng Việt, vài trăm nghìn đoạn) vào cluster nhỏ hơn. Dùng `retrieval.run_index`
  với `QDRANT_URL` trỏ lên cloud; vector đã tính sẵn trong `derived/vectors/` nên không cần GPU.

> Không đổi file nào trong `configs/` trước khi chuyển: tên collection được tính từ hash cấu hình, đổi cấu hình thì
> backend sẽ tìm một collection khác.

## 1. Qdrant Cloud

1. Tạo cluster trên [cloud.qdrant.io](https://cloud.qdrant.io), cùng khu vực châu Á với Render nếu có. Lấy **URL**
   và **API key**.
2. Chụp snapshot collection ở máy local, rồi tải lên cluster:

   ```powershell
   $C = "r2ai__bge-m3-v1-b6048a__e50d"
   # tạo snapshot (mất vài phút với 3M điểm), trả về tên file .snapshot
   curl.exe -X POST "http://localhost:6333/collections/$C/snapshots"
   # lấy file ra khỏi container
   docker cp medical-multi-agent-qdrant-1:/qdrant/snapshots/$C/<tên-file>.snapshot .
   # tải lên Qdrant Cloud (file lớn: nên chạy khi mạng ổn định)
   curl.exe -X POST "https://<cluster>.cloud.qdrant.io:6333/collections/$C/snapshots/upload?priority=snapshot" `
     -H "api-key: <QDRANT_API_KEY>" -F "snapshot=@<tên-file>.snapshot"
   ```

3. Kiểm tra: `GET https://<cluster>:6333/collections/<C>` phải có `points_count` khoảng 2.97M và `status: green`.

## 2. Backend trên Render

Repo đã có sẵn [`Dockerfile`](../Dockerfile) và [`render.yaml`](../render.yaml):

- **Docker**: Python 3.12, cài torch **bản CPU**, cài sẵn thư viện hệ thống cho OpenCV/Paddle, đóng gói sẵn BGE-M3 vào
  image và chạy HuggingFace ở chế độ offline. Mỗi lần khởi động chạy `alembic upgrade head` trước khi chạy API.
  Image nặng (vài GB, phần lớn là torch, paddle và BGE-M3) nên lần build đầu trên Render mất khá lâu.
- **Gói `2c-8g`** (2 CPU, 8GB RAM). Đo bằng `docker stats` khi chạy đúng image này:

  | Lúc | RAM |
  |---|---|
  | Vừa khởi động, chưa có yêu cầu | ~2.5GB |
  | Sau một câu chat (BGE-M3 + tra cứu) | ~4.0GB |
  | Sau khi đọc ảnh đơn thuốc (nạp PaddleOCR) | **~5.9GB** |

  Gói 4GB sẽ bị kill ở lần đọc ảnh đầu tiên.
- **Disk 5GB** gắn ở `/var/data` (`PRODUCT_STORAGE_DIR=/var/data/storage`) cho ảnh đơn thuốc và avatar. Không có
  disk thì mất hết ảnh sau mỗi lần deploy. Service có disk thì không scale lên nhiều instance được; điều này hợp với
  backend này (1 worker, job nhắc lịch chỉ nên chạy ở một nơi).
- **Postgres** `0.1c-256mb`, tự nối vào `PRODUCT_DATABASE_URL`. URL dạng `postgresql://` được tự đổi sang driver
  `asyncpg`; migration dùng cùng URL đó.

Các bước:

1. [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint** → chọn repo GitHub này.
2. Render đọc `render.yaml` và hỏi các biến `sync: false`:

   | Biến | Giá trị |
   |---|---|
   | `PRODUCT_CORS_ORIGINS` | Để tạm trống, điền sau khi có URL Vercel (bước 3) |
   | `PRODUCT_LLM_BASE_URL` / `_API_KEY` / `_LLM_MODEL` / `_VLM_MODEL` / `_VLM_TRANSCRIBE_MODEL` | Theo phương án LLM ở mục 0 |
   | `QDRANT_URL` / `QDRANT_API_KEY` | Từ mục 1 |
   | `PRODUCT_TAVILY_API_KEY` | Key Tavily (để trống thì tắt tìm kiếm web) |
   | `PRODUCT_SMTP_*` | Để trống `PRODUCT_SMTP_HOST` nếu chưa cần email nhắc lịch |

   `PRODUCT_JWT_SECRET` được Render tự sinh ngẫu nhiên. **Không** dùng lại giá trị trong `.env` local.
3. Deploy. Lần build đầu lâu (tải torch, paddle, BGE-M3). Khi xong, mở:
   - `https://<service>.onrender.com/health` → `{"status":"ok"}`
   - `https://<service>.onrender.com/docs` → Swagger
   - Lần đọc ảnh đầu tiên, PaddleOCR tải model nhận dạng chữ vào disk (`PADDLE_PDX_CACHE_HOME=/var/data/paddlex`),
     các lần deploy sau không phải tải lại.

## 3. Frontend trên Vercel

1. [vercel.com/new](https://vercel.com/new) → import repo GitHub này.
2. **Root Directory: `frontend`**. Framework tự nhận Vite; [`frontend/vercel.json`](../frontend/vercel.json) đã cấu hình
   build và chuyển mọi đường dẫn (`/chat`, `/records`…) về `index.html`, để tải lại trang không bị 404.
3. **Environment Variables**: `VITE_API_BASE = https://<service>.onrender.com` (không có `/` ở cuối, không có `/api`).
   Biến này được nhúng lúc build, nên đổi giá trị thì phải **Redeploy**.
4. Deploy, lấy URL (ví dụ `https://aurelia.vercel.app`).
5. Quay lại Render → service → **Environment** → `PRODUCT_CORS_ORIGINS = https://aurelia.vercel.app` → lưu (Render tự
   deploy lại). Có domain riêng thì thêm, phân cách bằng dấu phẩy.

## 4. Kiểm tra sau deploy

- [ ] Đăng ký, đăng nhập; tải lại trang ở `/chat` không bị 404
- [ ] Thêm thành viên, đổi avatar; deploy lại backend, avatar vẫn còn (disk hoạt động)
- [ ] Hỏi một câu y khoa → có trả lời và "Tài liệu đã tra cứu" (Qdrant + LLM hoạt động)
- [ ] Hỏi liều thuốc cho bé dưới 12 tuổi → câu trả lời cố định, không có con số liều (guardrail hoạt động)
- [ ] Gửi ảnh đơn thuốc → có kết quả đọc và đề xuất hồ sơ chờ xác nhận (VLM + PaddleOCR hoạt động)
- [ ] DevTools → Network: không có lỗi CORS

## 5. Lỗi thường gặp

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| Frontend báo "Không kết nối được máy chủ" | Sai `VITE_API_BASE`, hoặc backend đang khởi động / bị kill | Kiểm tra `/health`; xem Logs trên Render |
| Lỗi CORS trong DevTools | `PRODUCT_CORS_ORIGINS` thiếu hoặc sai origin (thừa `/`, sai `https`) | Điền đúng origin của Vercel, gồm cả `https://` |
| Render báo `Out of memory`, service khởi động lại liên tục | Gói RAM quá nhỏ | Dùng `2c-8g` trở lên (mục 2) |
| Log khởi động có `IncompleteSnapshotError` (BGE-M3) | Đã sửa `ignore_patterns` trong Dockerfile khác với FlagEmbedding | Giữ nguyên dòng `snapshot_download` trong Dockerfile |
| Log có `greenlet` / `email-validator is not installed` | Cài thiếu gói (trên Windows có sẵn nhờ gói khác kéo vào) | Đã ghim trong `requirements.txt`; đừng xoá |
| Chat lỗi 500, log có `collection ... not found` | Chưa chuyển collection, hoặc `configs/` khác bản local nên tên collection khác | Mục 1; kiểm tra tên collection trong log |
| Chat lỗi 500, log có lỗi kết nối LLM | `PRODUCT_LLM_BASE_URL` sai, tunnel tắt, hoặc tên model không có ở nhà cung cấp | Thử `curl <base_url>/models` với API key |
| Ảnh/avatar mất sau khi deploy | Chưa gắn disk, hoặc `PRODUCT_STORAGE_DIR` không nằm trong disk | Disk mount `/var/data`, storage `/var/data/storage` |
| Đăng xuất hết mọi người sau khi deploy | `PRODUCT_JWT_SECRET` bị đổi | Giữ cố định biến này |

## 6. Chạy thử image ở máy local trước khi đẩy lên Render

```powershell
docker build -t aurelia-api .
docker run --rm -p 8000:8000 --env-file .env `
  -e PRODUCT_DATABASE_URL=postgresql://user:pass@host.docker.internal:5432/product `
  -e QDRANT_URL=http://host.docker.internal:6333 `
  -e PRODUCT_LLM_BASE_URL=http://host.docker.internal:11434/v1 aurelia-api
```
