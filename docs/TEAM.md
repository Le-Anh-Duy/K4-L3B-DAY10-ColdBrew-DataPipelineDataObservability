# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `ColdBrew`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-ColdBrew-DataPipelineDataObservability`
- **Repository URL:** `https://github.com/Le-Anh-Duy/K4-L3B-DAY10-ColdBrew-DataPipelineDataObservability`

---

## Danh sách Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Lê Anh Duy | 2A202602723 | `duyla25clc@gmail.com` | **Thành viên 1 — Data Ingestion & Cleaning Owner** (`src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `script/run_ingestion.py`, data lineage & contract) | `report/2A202602723_LeAnhDuy.md` |
| 2 | Nguyễn Thị Phương Duyên | 2A202603001 | `duyenntp24@gmail.com` | **Thành viên 2 — Evaluation & Observability Owner** (`src/evaluation/testset.py`, `src/observability/quality.py`, `src/observability/reporting.py`, Great Expectations 1.x & Freshness SLA) | `report/2A202603001_NguyenThiPhuongDuyen.md` |
| 3 | Lê Quang Thành | 2A202602647 | `quangthanh17022004@gmail.com` | **Thành viên 3 — Corruption & Integration Owner** (`src/ingestion/corruption.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, điều phối 2 flow end-to-end & Idempotent Repair) | `report/2A202602647_LeQuangThanh.md` |

---

## Báo cáo Đóng góp Cá nhân Chi tiết

### 1. Lê Anh Duy — MSSV: 2A202602723 (Thành viên 1)
- **Vai trò chính:** Data Ingestion & Cleaning Owner.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref REST API trong `src/ingestion/crossref.py` với cơ chế thử lại (exponential backoff tối đa 4 lần khi gặp mã 429/500/502/503/504) và cơ chế tự động Fallback đọc snapshot offline `data/raw/crossref_response.json` khi mạng mất kết nối.
  - Phân tích payload JSON thành danh sách cấu trúc `PaperRecord`, bảo toàn 2 file dữ liệu thô phục vụ data lineage: `crossref_response.json` và `crossref_records.json`.
  - Triển khai quy trình làm sạch thuần túy trong `src/ingestion/cleaning.py`: loại bỏ tag JATS XML (`<jats:p>`, `<jats:title>`), unescape HTML entities, gom khoảng trắng, tính toán chuẩn hóa `age_days` (UTC), khử trùng lặp theo `paper_id` (DOI chữ thường) giữ bản ghi mới nhất, và tạo chuỗi 5 thành phần `text_for_embedding`.
  - Khởi tạo và đồng bộ tài liệu Data Contract chi tiết tại `report/data_contract.md`, cung cấp dữ liệu sạch 24 dòng tại `data/clean/papers_clean.csv` và `papers_clean.json`.
- **Đóng góp ngoài phạm vi chính:**
  - Viết `script/smoke_retrieval.py` làm bằng chứng cho rubric mục 4–5 (index 24/24 docs, tìm theo title trúng top-4 100%, QA trích xuất 4/4); sửa agent `mock` thiếu `bind_tools` và agent Gemini trả về content block thay vì text (`src/retrieval/llm.py`, `agent.py`).
  - Sửa `src/retrieval/index.py` để manifest lưu đường dẫn tương đối `data/chroma` thay vì đường dẫn tuyệt đối; bỏ `data/chroma`, `data/embeddings` khỏi git (`.gitignore`).
  - Xây dựng chat demo `demo/` (`src/retrieval/rag.py`, `chat.py`, `guardrails.py`): nhớ hội thoại theo session, LLM tự quyết định có retrieve qua tool calling, multi-query retrieval, chặn prompt injection, giới hạn 3 lượt gọi LLM mỗi câu hỏi.
  - Data profiling dữ liệu clean/corrupted và tổng hợp trang báo cáo HTML cho buổi thuyết trình; đối chiếu lại các báo cáo với artifact trong repo.
- **Điều học được / Đóng góp chính:**
  - Nắm vững kỹ thuật bảo toàn nguyên trạng dữ liệu nguồn (Immutable Data Lineage) và nguyên lý thiết kế hàm làm sạch thuần túy (pure functions) để hỗ trợ phục hồi dữ liệu Idempotent.

---

### 2. Nguyễn Thị Phương Duyên — MSSV: 2A202603001 (Thành viên 2)
- **Vai trò chính:** Evaluation & Observability Owner.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng bộ benchmark đánh giá chuẩn hóa 10 câu hỏi trong `src/evaluation/testset.py`, phân bổ đều qua 4 nhóm nghiệp vụ chính: `summary` (tóm tắt nội dung), `authors` (tác giả), `date` (thời điểm xuất bản), `categories` (chuyên mục nghiên cứu), lưu tại `data/eval/test_set.json`.
  - Thiết lập chốt kiểm định chất lượng tự động **Data Quality Gate** theo chuẩn mới **Great Expectations 1.x** (sử dụng ephemeral context) trong `src/observability/quality.py`, định nghĩa đủ 4 Expectations thiết yếu: `ExpectTableRowCountToBeBetween`, `ExpectColumnValuesToNotBeNull`, `ExpectColumnValuesToBeUnique`, `ExpectColumnValueLengthsToBeBetween`.
  - Triển khai thuật toán giám sát **Freshness SLA**: cảnh báo `is_fresh = False` khi tỷ lệ bài báo có `age_days > 180` vượt quá ngưỡng quy định 25%, xuất báo cáo chi tiết vào `data/quality/`.
  - Thiết kế các hàm sinh báo cáo Markdown chuyên biệt trong `src/observability/reporting.py`: `generate_phase1_report` và `generate_corruption_report`.
- **Điều học được / Đóng góp chính:**
  - Thành thạo kiến trúc Great Expectations 1.x và cách thiết lập các rào chắn Observability đa chiều để ngăn chặn sớm hiện tượng dữ liệu lỗi làm suy thoái mô hình AI.

---

### 3. Lê Quang Thành — MSSV: 2A202602647 (Thành viên 3)
- **Vai trò chính:** Corruption & Integration Owner.
- **Công việc chi tiết đã hoàn thành:**
  - Triển khai bộ giả lập làm bẩn dữ liệu thực tế **Synthetic Corruption Suite** trong `src/ingestion/corruption.py` với 6 kịch bản lỗi: drop ~20% bản ghi mới nhất, xóa rỗng tóm tắt (blank summary), chèn ký tự rác (inject noise), cắt ngắn tiêu đề (truncate title < 8 ký tự), lùi ngày xuất bản (stale date 500 ngày), và nhân bản dữ liệu (duplicate rows). Ghi nhận audit log chi tiết vào `data/results/corruption_log.json`.
  - Xây dựng và điều phối pipeline Baseline Phase 1 trong `src/pipelines/phase1.py` (`script/run_phase1.py`), liên kết toàn bộ chu trình Ingestion $\rightarrow$ Cleaning $\rightarrow$ ChromaDB Indexing (`papers-baseline`) $\rightarrow$ Benchmark Evaluation $\rightarrow$ Quality/Freshness checks $\rightarrow$ Báo cáo `phase1_report.md`.
  - Xây dựng luồng thực thi tích hợp `src/pipelines/corruption_flow.py` (`script/run_corruption_flow.py`): tiêm lỗi, đo lường sự sụp đổ chỉ số của RAG Agent (Hit Rate giảm xuống 0.80, Token F1 giảm xuống 0.6741), kích hoạt **Idempotent Repair** khôi phục từ raw snapshot `crossref_records.json`, đánh giá lại tập dữ liệu sau phục hồi và xuất bảng đối chiếu 3 trạng thái ra terminal và `data/reports/corruption_report.md`.
  - Xử lý triệt để lỗi phân giải đường dẫn import module của Python (`sys.path` và `pip install -e .`).
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu sắc cơ chế gây suy giảm hiệu năng AI trong thực tế (Silent Failure), cách cô lập các không gian vector collection trong ChromaDB, và thiết kế quy trình Idempotent Self-Healing đảm bảo AI phục hồi 100% phong độ.
