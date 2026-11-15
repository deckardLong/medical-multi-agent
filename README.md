# AURELIA

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.162-009688?logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" alt="React 18"></a>
  <a href="https://qdrant.tech/"><img src="https://img.shields.io/badge/Qdrant-hybrid%20search-DC244C" alt="Qdrant"></a>
  <a href="https://ollama.com/"><img src="https://img.shields.io/badge/Ollama-local%20LLM-000000?logo=ollama&logoColor=white" alt="Ollama"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-4CECB8" alt="License MIT"></a>
</p>

<p align="center">
  <img src="docs/assets/aurelia-logo.svg" alt="AURELIA" width="360">
</p>

<p align="center">
  <b>A</b>ssisted <b>U</b>nderstanding &amp; <b>R</b>easoning for <b>E</b>vidence-based <b>L</b>ife &amp; <b>I</b>ntegrated <b>A</b>ssistance
</p>

**AURELIA** là trợ lý sức khoẻ gia đình. AURELIA trả lời câu hỏi y khoa bằng cách tra cứu kho tài liệu y tế đa ngôn ngữ
(tiếng Việt, tiếng Trung). Kho được tìm kiếm bằng hybrid search (dense + sparse) trên Qdrant. Hệ thống quản lý
hồ sơ và lịch khám cho từng thành viên trong gia đình, đọc ảnh đơn thuốc, và gửi email nhắc lịch.

**Chức năng chính**

- **Chat với AURELIA**: câu trả lời có dẫn nguồn từ kho tài liệu. Kho không có thì tìm trên các trang y tế uy tín.
- **Đọc ảnh đơn thuốc**: 3 agent đọc ảnh **chạy song song** bằng [octochains](https://pypi.org/project/octochains/),
  mỗi agent dùng một model khác nhau, rồi đối chiếu từng trường. Trường nào các lần đọc không khớp sẽ được
  đánh dấu để người dùng tự chọn.
- **Hồ sơ và lịch theo mô hình đề xuất → xác nhận**: AI chỉ tạo đề xuất. Dữ liệu chỉ có hiệu lực, và chỉ được
  dùng để tư vấn, sau khi người dùng xác nhận.
- **Nhắc lịch khám và uống thuốc qua email**, hỗ trợ lịch lặp theo chuẩn RRULE.
- **Phân quyền theo gia đình**: chủ gia đình quản lý thành viên chưa có tài khoản (con nhỏ, ông bà...). Thành
  viên đã liên kết tài khoản thì tự quản lý hồ sơ của mình.

### Các model sử dụng

Mọi model đều chạy local, không gửi dữ liệu sức khoẻ ra dịch vụ AI bên ngoài.

| Model | Chạy bằng | Vai trò |
|---|---|---|
| `qwen2.5:7b-instruct` | Ollama | Model chat chính của AURELIA: gọi tool, soạn câu trả lời. Đồng thời chuyển văn bản thô thành JSON cho agent 2 và 3 |
| `qwen2.5vl:7b` | Ollama | **Agent 1** `vlm_direct`: nhìn ảnh, đọc thẳng ra JSON đơn thuốc |
| PaddleOCR (PP-OCRv6) | Python | **Agent 2** `ocr_then_llm`: nhận dạng chữ, sau đó qwen2.5 cấu trúc lại |
| `gemma3:4b` | Ollama | **Agent 3** `vlm_transcribe`: chép nguyên văn chữ trong ảnh, sau đó qwen2.5 cấu trúc lại |
| BGE-M3 | FlagEmbedding | Mã hoá câu hỏi và tài liệu thành vector dense + sparse cho hybrid search |

Agent 1 dùng Qwen, còn agent 3 dùng Gemma: hai model thuộc hai họ khác nhau nên nếu đọc sai thì thường sai theo
những kiểu khác nhau. Nhờ vậy, một tên thuốc đọc nhầm không thể được "xác nhận" chỉ vì hai lần đọc cùng nhầm
giống nhau. Agent 3 đổi model qua biến `PRODUCT_VLM_TRANSCRIBE_MODEL`.

---

## Kiến trúc

### Tổng quan hệ thống

```mermaid
flowchart LR
    U(["Người dùng"]) --> FE["Frontend React<br/>Vite :5173"]
    FE -- "/api/* (proxy)" --> API["FastAPI :8000"]

    subgraph Backend["product/ — FastAPI"]
        API --> ROUTERS["Routers<br/>auth · members · chat · documents<br/>records · calendar · dashboard"]
        ROUTERS -- "chat" --> AGENT["Agent LangChain<br/>+ 7 tools"]
        SCHED["APScheduler<br/>quét nhắc lịch"]
    end

    ROUTERS --> PG[("PostgreSQL :5432")]
    ROUTERS -- "documents" --> FS[("storage/<br/>ảnh tải lên")]
    AGENT -- "LLM / VLM" --> OLLAMA["Ollama :11434<br/>qwen2.5 · qwen2.5vl · gemma3"]
    AGENT -- "hybrid search" --> QD[("Qdrant :6333<br/>~3M chunk")]
    AGENT -- "web search" --> TAV["Tavily API"]
    SCHED --> PG
    SCHED -- "SMTP" --> MAIL["Gmail / SMTP"]

    subgraph Offline["retrieval/ — dựng chỉ mục (chạy riêng)"]
        HF["HuggingFace dataset"] --> PIPE["chunk → embed → index"]
    end
    PIPE -- "upsert" --> QD
```

### Pipeline dựng chỉ mục (`retrieval/` + `corpus_sync/`)

Mỗi bước tạo ra một mã hash, và mã này được tính nối tiếp từ hash của bước trước. Vì vậy chỉ cần sửa cấu hình ở
bất kỳ bước nào là tự sinh ra thư mục mới và collection Qdrant mới. Dữ liệu cũ không bao giờ bị ghi đè.

```mermaid
flowchart LR
    HF["HuggingFace<br/>corpus + chunk/vector có sẵn"] -- "corpus_sync.run_fetch" --> CORPUS[("corpus/<br/>shard tài liệu")]
    CORPUS --> CH["Chunking<br/>h_chunk"]
    CH --> CHD[("derived/chunks/<br/>ver-h_chunk")]
    CHD --> EM["Embedding BGE-M3<br/>dense + sparse<br/>h_embed = f(embed, h_chunk)"]
    EM --> VD[("derived/vectors/<br/>ver-h_embed")]
    VD --> IX["Upsert Qdrant<br/>h_index = f(index, h_embed)"]
    IX --> COL[("collection<br/>prefix__embed__h_index")]
    IX -. "ghi shard đã xong" .-> MF[("state/.../manifest.jsonl")]
    MF -. "chỉ xử lý shard còn thiếu" .-> IX
    COL -- "retrieval.promote<br/>(đủ số điểm)" --> AL["alias đang dùng"]
```

### Luồng hỏi đáp

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant FE as Frontend
    participant C as chat service
    participant DB as PostgreSQL
    participant A as Agent (Ollama)
    participant R as medical_retrieval_tool
    participant Q as Qdrant
    participant W as web_search_tool (Tavily)

    U->>FE: Nhập câu hỏi
    FE->>C: POST /members/{id}/chat
    C->>DB: Kiểm tra quyền, lưu tin nhắn
    C->>DB: Lấy hồ sơ đã xác nhận (dị ứng, bệnh nền, thuốc)
    C->>A: Hồ sơ + 12 tin gần nhất + câu hỏi
    A->>R: Tìm tài liệu liên quan
    R->>Q: Hybrid search: dense + sparse, gộp bằng RRF
    Q-->>R: Các đoạn liên quan nhất kèm tiêu đề bài
    alt Kho tài liệu không có kết quả phù hợp
        A->>W: Tìm trên WHO, CDC, NIH, Bộ Y tế...
        W-->>A: Kết quả kèm URL
    end
    A-->>C: Câu trả lời
    C->>C: Bỏ nguồn bịa, thêm nguồn thật nếu thiếu
    C->>C: Gắn cảnh báo dị ứng nếu câu trả lời nhắc tới thuốc
    C->>DB: Lưu câu trả lời
    C-->>FE: Trả lời
```

`member_id` được truyền cho tool qua cấu hình của lượt chạy, không bao giờ lấy từ tham số do LLM tạo ra. Vì vậy
không thể dùng prompt để đọc dữ liệu của thành viên khác.

### Đọc ảnh đơn thuốc

```mermaid
flowchart TB
    UP["POST /members/{id}/documents<br/>kiểm tra định dạng ảnh bằng Pillow, tối đa 10MB"] --> CHATDOC["POST /members/{id}/chat<br/>kèm document_ids"]
    CHATDOC --> QC{"Kiểm tra chất lượng<br/>kích thước, độ nét"}
    QC -- "không đạt" --> REJ["Đề nghị chụp lại"]
    QC -- "đạt" --> ENG["octochains Engine<br/>3 lần đọc chạy song song"]
    ENG --> A1["vlm_direct<br/>qwen2.5vl đọc thẳng ra JSON"]
    ENG --> A2["ocr_then_llm<br/>PaddleOCR → qwen2.5"]
    ENG --> A3["vlm_transcribe<br/>gemma3 chép chữ → qwen2.5"]
    A1 & A2 & A3 --> CON["Đối chiếu từng trường<br/>tên · liều · tần suất · thời gian dùng"]
    CON --> OK{"≥ 2 lần đọc khớp nhau?"}
    OK -- "có" --> V["Giá trị đã xác định"]
    OK -- "không" --> X["a | b (cần kiểm tra)"]
    V & X --> PROP["Đề xuất hồ sơ thuốc<br/>confirmed_at = null"]
    PROP --> SHOW["Hiển thị nguyên văn kết quả<br/>+ nhắc người dùng xác nhận"]
```

### Đề xuất → xác nhận

```mermaid
stateDiagram-v2
    state "Chờ xác nhận" as ChoXacNhan
    state "Đã xác nhận" as DaXacNhan
    [*] --> ChoXacNhan: AI đề xuất / đọc ảnh
    [*] --> DaXacNhan: Người dùng tự nhập
    ChoXacNhan --> ChoXacNhan: Xác nhận khi còn "(cần kiểm tra)" → 409
    ChoXacNhan --> DaXacNhan: POST .../confirm (đã chọn đúng giá trị)
    ChoXacNhan --> [*]: Xoá
    DaXacNhan --> [*]: Xoá
    DaXacNhan --> DaXacNhan: Dùng để tư vấn, nhắc lịch, hiện trên dashboard

    note right of ChoXacNhan
        Không bao giờ được dùng để tư vấn
    end note
```

### Nhắc lịch qua email

```mermaid
sequenceDiagram
    participant S as APScheduler (5 phút/lần)
    participant DB as PostgreSQL
    participant M as SMTP

    S->>DB: Lịch đã xác nhận rơi vào khoảng [bây giờ, bây giờ + 60 phút]
    Note over S: Khai triển lịch lặp (RRULE) theo giờ Việt Nam
    loop Mỗi lần xảy ra
        S->>DB: INSERT reminder_logs ... ON CONFLICT DO NOTHING
        alt Đã gửi trước đó, hoặc worker khác đang gửi
            DB-->>S: Bỏ qua
        else Ghi được
            S->>M: Gửi email cho chính thành viên, hoặc chủ gia đình nếu thành viên chưa có tài khoản
            alt Gửi thành công
                S->>DB: COMMIT
            else Gửi lỗi
                S->>DB: ROLLBACK, lượt quét sau gửi lại
            end
        end
    end
```

### Mô hình dữ liệu

```mermaid
erDiagram
    USER ||--|| FAMILY : "sở hữu"
    FAMILY ||--o{ FAMILY_MEMBER : "gồm"
    USER |o--o{ FAMILY_MEMBER : "liên kết"
    USER ||--o{ CONNECTION : "gửi / nhận"
    FAMILY_MEMBER ||--o| CHAT_SESSION : "có"
    CHAT_SESSION ||--o{ CHAT_MESSAGE : "gồm"
    FAMILY_MEMBER ||--o{ DOCUMENT : "tải lên"
    FAMILY_MEMBER ||--o{ MEDICAL_RECORD : "có"
    DOCUMENT |o--o{ MEDICAL_RECORD : "nguồn"
    FAMILY_MEMBER ||--o{ CALENDAR_EVENT : "có"
    CALENDAR_EVENT ||--o{ REMINDER_LOG : "đã nhắc"

    USER {
        uuid id
        string email
        string last_name
        string first_name
        date date_of_birth
        enum gender
    }
    FAMILY_MEMBER {
        uuid id
        enum member_type
        string display_name
        date dob
        uuid linked_user_id
    }
    MEDICAL_RECORD {
        uuid id
        enum kind
        jsonb payload
        timestamptz confirmed_at
    }
    CALENDAR_EVENT {
        uuid id
        enum type
        timestamptz starts_at
        string recurrence_rule
        enum source
        timestamptz confirmed_at
    }
    REMINDER_LOG {
        uuid event_id
        timestamptz occurs_at
    }
    CHAT_MESSAGE {
        enum role
        text content
        jsonb attachments
    }
    DOCUMENT {
        string storage_path
        string mime_type
        jsonb extracted_json
    }
```

### Theme frontend (Abstract Factory)

```mermaid
classDiagram
    class UIThemeFactory {
        <<interface>>
        createPalette() Palette
        createEffects() Effects
        createButtonSkin(variant) Skin
        createCardSkin(tone) Skin
        createInputSkin() Skin
        createBadgeSkin(tone) Skin
    }
    class NeonDarkFactory
    class NeonLightFactory
    class ThemeProvider {
        toggle()
    }
    class Button
    class Card
    class Input
    UIThemeFactory <|.. NeonDarkFactory
    UIThemeFactory <|.. NeonLightFactory
    ThemeProvider --> UIThemeFactory : chọn factory
    Button ..> UIThemeFactory : useUI()
    Card ..> UIThemeFactory : useUI()
    Input ..> UIThemeFactory : useUI()
```

Factory trả về **skin** (một bộ biến CSS) chứ không trả về component. Nhờ vậy, khi đổi theme React không phải
dựng lại cây giao diện, và chữ đang gõ trong ô nhập không bị mất.

---

## Cấu trúc thư mục

```text
.
├─ product/                  # Backend FastAPI
│  ├─ apps/api/              #   auth, members, chat, documents, records, calendar, dashboard
│  ├─ apps/agent/            #   Agent LangChain, prompt, tools (retrieval, web, hồ sơ, lịch, đọc ảnh)
│  ├─ db/models/             #   SQLAlchemy models
│  └─ db/migrations/         #   Alembic
├─ frontend/                 # React 18 + TypeScript + Vite
├─ retrieval/                # Chunk, embed, index, search, rerank
├─ corpus_sync/              # Tải corpus và dữ liệu đã tính sẵn từ HuggingFace
├─ common/                   # Cấu hình, schema dùng chung
├─ configs/                  # YAML cấu hình pipeline
└─ docker-compose.yml        # Qdrant + PostgreSQL
```

## Cài đặt và chạy

**Yêu cầu:** Python 3.12, Node.js ≥ 16, Docker, [Ollama](https://ollama.com).

```powershell
# 1. Qdrant + PostgreSQL
docker-compose up -d

# 2. Các model chạy local
ollama pull qwen2.5:7b-instruct
ollama pull qwen2.5vl:7b
ollama pull gemma3:4b

# 3. Backend
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
copy .env.example .env               # rồi điền key (xem bảng bên dưới)
.\venv\Scripts\alembic upgrade head
.\venv\Scripts\uvicorn product.apps.api.main:app --reload     # http://127.0.0.1:8000/docs

# 4. Frontend
cd frontend
npm install
npm run dev                          # http://127.0.0.1:5173
```

**Dựng chỉ mục Qdrant**: chỉ cần làm lần đầu. Bước embedding nên chạy trên máy có GPU.

```powershell
python -m corpus_sync.run_fetch           # tải corpus và chunk/vector đã tính sẵn
python -m retrieval.run_index             # chunk → embed → index, chỉ xử lý phần còn thiếu
python -m retrieval.promote --min-points 1
```

## Biến môi trường chính (`.env`)

| Biến | Ý nghĩa |
|---|---|
| `PRODUCT_DATABASE_URL` | Kết nối PostgreSQL (asyncpg) |
| `PRODUCT_JWT_SECRET` | Khoá ký JWT, dùng chuỗi ngẫu nhiên dài |
| `PRODUCT_LLM_MODEL` / `PRODUCT_VLM_MODEL` | Model chat / model đọc ảnh trên Ollama |
| `PRODUCT_VLM_TRANSCRIBE_MODEL` | Model đọc ảnh thứ hai, khác họ với model trên để hai lần đọc không sai giống nhau |
| `PRODUCT_TAVILY_API_KEY` | Bật tìm kiếm web |
| `PRODUCT_SMTP_HOST` / `_PORT` / `_USER` / `_PASSWORD` / `_FROM` | Gửi email nhắc lịch. Để trống host thì tắt chức năng nhắc |
| `PRODUCT_REMINDER_LEAD_MINUTES` | Nhắc trước bao nhiêu phút (mặc định 60) |
| `QDRANT_URL` | Địa chỉ Qdrant |

Danh sách đầy đủ có trong [`.env.example`](.env.example).

## API

Mọi endpoint (trừ `/auth/register` và `/auth/login`) cần header `Authorization: Bearer <token>`. Với các
endpoint dạng `/members/{member_id}/...`, nếu không có quyền thì trả **404** (không phải 403), để người ngoài
không dò ra được `member_id` nào tồn tại. Tài liệu tương tác: `http://127.0.0.1:8000/docs`.

| Nhóm | Endpoint |
|---|---|
| Xác thực | `POST /auth/register` · `POST /auth/login` · `GET /auth/me` |
| Gia đình | `GET /families/me` · `GET`/`POST /families/me/members` · `POST /connections` · `POST /connections/{id}/respond` |
| Tổng quan | `GET /dashboard` |
| Chat | `GET`/`POST /members/{id}/chat` (body có thể kèm `document_ids`) |
| Tài liệu | `GET`/`POST /members/{id}/documents` |
| Hồ sơ | `GET /members/{id}/records?status_filter=` · `POST .../records` · `POST .../records/{rid}/confirm` · `DELETE .../records/{rid}` |
| Lịch | `GET /members/{id}/calendar?start=&end=&include_pending=` · `GET .../calendar/pending` · `POST .../calendar` · `POST .../calendar/{eid}/confirm` · `DELETE .../calendar/{eid}` |
