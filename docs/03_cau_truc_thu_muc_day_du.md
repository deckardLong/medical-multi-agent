# 06 — Cấu trúc thư mục hoàn chỉnh (cuộc thi + sản phẩm mở rộng)

> Gộp cây thư mục gốc từ `01_cau_truc_va_schema.md` (phần `retrieval/`, `submission/`, `common/`... — **giữ nguyên, không sửa**) với phần mở rộng sản phẩm từ `04_mo_rong_tro_ly_y_te_gia_dinh.md` và `05_octochains_xac_minh_anh_y_te.md`. Đây là bản đầy đủ nhất, dùng làm tham chiếu khi tạo thư mục thật.
>
> Ký hiệu: **[CŨ]** = đã có từ repo cuộc thi, không đổi · **[MỚI]** = thêm trong giai đoạn mở rộng sản phẩm.

```text
multilingual-medical-retrieval/
│
├─ README.md                                              [CŨ]
├─ pyproject.toml                                         [CŨ]
├─ .env.example                                           [CŨ]
├─ .gitignore                                              [CŨ]
│
├─ configs/                                                [CŨ]
│  ├─ chunk.yaml
│  ├─ embed.yaml
│  ├─ retrieve.yaml
│  ├─ corpus_sync.yaml
│  └─ submit.yaml
│
├─ common/                                                 [CŨ] — đóng băng, nhiều phía dùng chung
│  ├─ schema/
│  │  └─ __init__.py                                       # Doc, Chunk, Candidate, SparseVec
│  ├─ config/
│  │  ├─ env.py                                            # Env (.env)
│  │  └─ paths.py                                          # ROOT
│  └─ io/
│     ├─ docs.py  tables.py  vectors.py  rows.py  fingerprint.py
│
├─ corpus_sync/                                             [CŨ]
│  ├─ settings.py  hf.py  report.py  run_fetch.py
│
├─ retrieval/                                               [CŨ] — ĐÃ build index, không chạy lại trừ khi nạp thêm corpus
│  ├─ chunking/       split/  tokens/  structure.py  plan.py  run.py
│  ├─ embedding/      backends/{bge_m3.py,fake.py}  encode_shard.py  checkpoint.py
│  │                  batching.py  sparse.py  validate.py  run.py
│  ├─ index/          client.py  spec.py  points.py  upsert.py  manifest.py  names.py  run.py
│  ├─ search/         hybrid.py  filters.py  hits.py  retriever.py
│  │                  decompose/  splitters.py
│  ├─ progress/       bar.py  quiet.py
│  ├─ pipeline/       cycle.py
│  ├─ settings/       chunk/  embed.py  checks.py
│  ├─ run_index.py    run_embed.py  run_queries.py  run_select.py  promote.py
│
├─ submission/                                              [CŨ]
│  ├─ checks/         problems.py  structure.py  ids.py
│  ├─ schema.py  settings.py  build.py  sources.py  pack.py  log.py  run.py  run_submit.py
│
├─ corpus/                                                  [CŨ, ngoài git] — dữ liệu crawl BTC
│  └─ viz/{crawl_log, docs/{a,b}/*.jsonl.zst, manifest}
├─ queries/query.parquet                                    [CŨ, ngoài git]
├─ derived/                                                  [CŨ, ngoài git] — chunks/, vectors/
├─ state/                                                    [CŨ, ngoài git] — manifest.parquet
├─ candidates/                                                [CŨ] — <run_id>.jsonl
│
├─ tests/                                                     [CŨ]
│  ├─ common/  corpus_sync/  retrieval/  submission/
│
│
├─ product/                                                  [MỚI] — sản phẩm, KHÔNG sửa gì phía trên
│  │
│  ├─ apps/
│  │  │
│  │  ├─ api/                                                [MỚI] — FastAPI, một domain = một thư mục
│  │  │  ├─ main.py                                          # khởi tạo app, gắn router từng domain
│  │  │  ├─ auth/
│  │  │  │  ├─ router.py  schemas.py  service.py  deps.py    # deps.py: get_current_user cho các router khác
│  │  │  │
│  │  │  ├─ members/                                         # family_members + connections
│  │  │  │  ├─ router.py
│  │  │  │  ├─ schemas.py                                    # FamilyMemberIn/Out, ConnectionIn/Out
│  │  │  │  ├─ service.py                                    # tạo member, gửi/duyệt lời mời kết bạn
│  │  │  │  └─ permissions.py                                # mức manage / view_own
│  │  │  │
│  │  │  ├─ records/                                         # medical_records + documents
│  │  │  │  ├─ router.py
│  │  │  │  ├─ schemas.py
│  │  │  │  ├─ service.py                                    # ghi record sau khi người dùng xác nhận
│  │  │  │  └─ storage.py                                    # upload/đọc file từ object storage
│  │  │  │
│  │  │  ├─ calendar/
│  │  │  │  ├─ router.py  schemas.py  service.py
│  │  │  │  └─ reminders.py                                  # job APScheduler quét sự kiện sắp tới
│  │  │  │
│  │  │  ├─ chat/
│  │  │  │  ├─ router.py                                     # REST: lịch sử hội thoại
│  │  │  │  ├─ ws.py                                         # WebSocket: luồng chat realtime
│  │  │  │  └─ schemas.py
│  │  │  │
│  │  │  └─ dashboard/
│  │  │     ├─ router.py
│  │  │     └─ aggregates.py                                 # truy vấn tổng hợp cho 4 khối ở mục 7 (file 04)
│  │  │
│  │  ├─ agent/                                               [MỚI] — LangGraph orchestrator
│  │  │  ├─ graph.py                                          # state machine: router -> tool -> confirm
│  │  │  ├─ state.py                                          # định nghĩa AgentState (Pydantic)
│  │  │  ├─ router.py                                         # phân loại ý định, chọn tool
│  │  │  ├─ prompts/
│  │  │  │  ├─ router.md  retrieval.md  confirm.md
│  │  │  │
│  │  │  └─ tools/
│  │  │     ├─ medical_retrieval_tool.py                      # bọc retrieval/search/hybrid.py, KHÔNG sửa code cũ
│  │  │     ├─ web_search_tool.py                             # Tavily/SerpAPI, whitelist nguồn y tế
│  │  │     ├─ calendar_tool.py
│  │  │     ├─ member_profile_tool.py
│  │  │     │
│  │  │     └─ vision_extract_tool/                           # chi tiết theo file 05
│  │  │        ├─ __init__.py                                 # expose extract(image) cho graph.py gọi
│  │  │        ├─ schema.py                                   # JSON schema chung cho cả 3 agent
│  │  │        ├─ agents/
│  │  │        │  ├─ vlm_direct.py                            # Agent 1: VLM đọc trực tiếp
│  │  │        │  ├─ ocr_then_llm.py                          # Agent 2: OCR thuần + LLM diễn giải
│  │  │        │  └─ vlm_cropped.py                           # Agent 3: VLM đọc lại theo vùng crop
│  │  │        └─ aggregate/
│  │  │           ├─ field_match.py                           # chuẩn hoá + so khớp từng trường
│  │  │           └─ conflict_checker.py                      # bọc Octochains ConflictChecker
│  │  │
│  │  └─ web/                                                  [MỚI, ngoài phạm vi các file .md này]
│  │     └─ (frontend — chỉ cần giữ đúng hợp đồng REST/WebSocket của apps/api)
│  │
│  ├─ db/                                                      [MỚI]
│  │  ├─ models/                                               # một bảng = một file (mục 3, file 04)
│  │  │  ├─ user.py  family.py  family_member.py  connection.py
│  │  │  ├─ medical_record.py  document.py  calendar_event.py
│  │  │  ├─ chat_session.py  chat_message.py  agent_tool_call.py
│  │  ├─ session.py                                            # engine + SessionLocal (SQLAlchemy)
│  │  └─ migrations/                                           # Alembic
│  │     ├─ env.py
│  │     └─ versions/
│  │
│  ├─ config.py                                                [MỚI] — Env riêng của product/ (DB_URL, OBJECT_STORAGE_*, TAVILY_API_KEY...)
│  │
│  └─ tests/                                                   [MỚI] — rootdir/pytest.ini riêng, tách khỏi tests/ của cuộc thi
│     ├─ api/        test_members.py  test_records.py  test_calendar.py  test_dashboard.py
│     ├─ agent/      test_router.py  test_medical_retrieval_tool.py
│     │              test_vision_extract/  test_field_match.py  test_conflict_checker.py
│     └─ db/         test_models.py
│
└─ docs/                                                       [MỚI, tuỳ chọn] — gom các file .md thiết kế vào một chỗ
   ├─ 01_cau_truc_va_schema.md
   ├─ 02_pipeline_tu_dong.md
   ├─ 03_phan_cong_va_lich.md
   ├─ 04_mo_rong_tro_ly_y_te_gia_dinh.md
   ├─ 05_octochains_xac_minh_anh_y_te.md
   └─ 06_cau_truc_thu_muc_day_du.md                            # chính là file này
```

---

## Ghi chú khi tạo thư mục thật

1. **Không tạo `product/` lồng trong `retrieval/` hay ngược lại** — hai thư mục này cùng cấp dưới gốc repo, không phụ thuộc đường dẫn lẫn nhau ngoài việc `product/apps/agent/tools/medical_retrieval_tool.py` import `retrieval.search...` như một package Python bình thường.
2. **`product/apps/agent/tools/vision_extract_tool/` là một package, không phải một file** — vì nó chứa 3 agent + 2 module gộp, đúng nguyên tắc chia nhỏ theo concern đã áp dụng cho `retrieval/`.
3. **`product/tests/`** cần `conftest.py` riêng ở gốc `product/tests/`, không dùng chung fixture với `tests/` gốc của cuộc thi (fixture đó xoay quanh shard/corpus, không liên quan schema sản phẩm).
4. **`docs/` là tuỳ chọn** — nếu bạn không muốn xáo trộn vị trí các file `.md` đã có ở gốc repo, cứ để chúng ở gốc như hiện tại; mục này chỉ gợi ý nếu sau này muốn gom lại cho gọn.

Thứ tự tạo khi bắt đầu code, theo đúng lộ trình P0 ở mục 9 của file 04: `product/db/models/` → `product/apps/api/auth` + `members` → `product/apps/agent/graph.py` với `medical_retrieval_tool.py` → phần còn lại theo P1/P2.