# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Lê Quang Thành            |
| MSSV               | 2A202602647                    |
| Khóa/Lớp         | K4              |
| Tên nhóm         | ColdBrew     |
| Vai trò chính    | Corruption & Integration Owner |
| Repository         | https://github.com/Le-Anh-Duy/K4-L3B-DAY10-ColdBrew-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | :---: |
| **Synthetic Corruption Suite** | `src/ingestion/corruption.py`<br>`corrupt_clean_dataframe()` | DataFrame sạch (`data/clean/papers_clean.json`), đường dẫn log `output_log_path` | Corrupted DataFrame (`papers_clean_corrupted.{csv,json}`) và audit log 6 dạng lỗi (`data/results/corruption_log.json`) | **Hoàn thành** |
| **Baseline Pipeline Orchestration** | `src/pipelines/phase1.py`<br>`main()` | `Settings` cấu hình, Raw records (`data/raw/crossref_records.json`), Benchmark test set (`data/eval/test_set.json`) | ChromaDB vector collection `papers-baseline`, baseline metrics (`baseline_metrics.json`), báo cáo `data/reports/phase1_report.md` | **Hoàn thành** |
| **Corruption, Repair & Observability Flow** | `src/pipelines/corruption_flow.py`<br>`main()` | Baseline metrics, Clean DataFrame, Raw records bất biến, Benchmark test set | Vector collection corrupted & repaired, bộ chỉ số so sánh (`corrupted_metrics.json`, `repaired_metrics.json`), báo cáo đối chiếu 3 trạng thái `data/reports/corruption_report.md` | **Hoàn thành** |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Data Contract & Clean Schema Verification** | Thành viên 1 (Data Ingestion & Cleaning) | Kiểm thử tính tương thích giữa output của `cleaning.py` (cấu trúc 16 cột chuẩn, 5 phần của `text_for_embedding`) với ChromaDB indexer trong `phase1.py`. |
| **Observability & Quality Gate Integration** | Thành viên 2 (Observability Owner) | Tích hợp các hàm kiểm tra Great Expectations 1.x và Freshness SLA (`quality.py`) vào cả 2 pipeline; bổ sung cơ chế fallback để hệ thống chạy thông suốt. |
| **Benchmark Consistency Verification** | Thành viên 3 (Evaluation Owner) | Đảm bảo bộ test set gồm 10 câu hỏi (`data/eval/test_set.json`) được cố định và tái sử dụng 100% xuyên suốt 3 trạng thái Baseline, Corrupted và Repaired. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Triển khai bộ giả lập 6 kịch bản làm bẩn dữ liệu thực tế | `src/ingestion/corruption.py`<br>`corrupt_clean_dataframe` | Sinh dữ liệu lỗi, ghi nhận 6 scenario vào `data/results/corruption_log.json` | `python -c "from ingestion.corruption import corrupt_clean_dataframe..."` kiểm tra 6 scenarios |
| Xây dựng và điều phối pipeline Baseline Phase 1 | `src/pipelines/phase1.py`<br>`script/run_phase1.py` | Tạo Chroma index sạch, sinh `data/results/baseline_metrics.json` và `phase1_report.md` | Chạy lệnh `python script/run_phase1.py`, console in đủ các bước từ 1/10 đến 10/10 |
| Xây dựng luồng tích hợp Corruption -> Evaluate -> Repair -> Compare | `src/pipelines/corruption_flow.py`<br>`script/run_corruption_flow.py` | Tạo đầy đủ artifacts 3 trạng thái, sinh `data/reports/corruption_report.md` | Chạy lệnh `python script/run_corruption_flow.py`, in bảng so sánh 3 trạng thái ra terminal |
| Thiết kế cơ chế tự phục hồi an toàn (Idempotent Repair) | `src/pipelines/corruption_flow.py`<br>Bước 6 & 7 | Khôi phục 100% dữ liệu gốc từ `crossref_records.json`, index lại vào `papers-repaired` | Chỉ số `retrieval_hit_rate` và `mean_token_f1` phục hồi tuyệt đối từ 0.8 & 0.6741 về 1.0 & 1.0 |

**Output cụ thể bàn giao:**
Bảng đối chiếu định lượng 3 trạng thái trong [corruption_report.md](../data/reports/corruption_report.md) và audit log [corruption_log.json](../data/results/corruption_log.json) ghi nhận chi tiết 5 bài báo bị drop, 2 bài bị blank summary, 2 bài bị inject noise, 2 bài bị truncate title, 9 bài bị lùi ngày quá hạn và 2 bài bị duplicate.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong các hệ thống RAG Agent thực tế, dữ liệu thu thập từ các nguồn bên ngoài thường xuyên bị suy thoái (data drift, network drop, parsing failure, schema violation). Nếu không có Data Observability, hệ thống sẽ rơi vào trạng thái **Silent Failure** — LLM vẫn trả lời nghe có vẻ tự tin nhưng thông tin đã bị sai lệch nghiêm trọng. Nhiệm vụ của tôi là:
1. Giả lập chính xác 6 dạng lỗi dữ liệu phổ biến để chứng minh sự suy giảm hiệu năng của RAG.
2. Tự động hóa điều phối chu trình đánh giá đa trạng thái (Baseline → Corrupted → Repaired).
3. Chứng minh cơ chế phục hồi dữ liệu Idempotent Repair giúp AI lấy lại phong độ hoàn toàn.

### Cách triển khai

1. **Bộ tiêm lỗi Synthetic Corruption Suite (`corruption.py`):**
   - *Drop latest records:* Cắt bỏ 5 bản ghi mới nhất (~20.8% của 24 bài), trực tiếp làm mất tài liệu liên quan đến câu hỏi `q01` và `q02` trong test set.
   - *Blank summary:* Xóa rỗng trường `summary` ở 2 bài báo (`10.1145/3637528.3671822`, `10.1145/3637528.3671820`), khiến QA agent không thể trích xuất câu trả lời tóm tắt cho câu `q05` (F1 = 0).
   - *Inject noise:* Chèn các chuỗi byte rác `[CORRUPTED_STREAM_#$!@%*&_0xDEADBEEF_GARBAGE]` vào tóm tắt của 2 bài báo, phá hủy không gian embedding vector của mô hình `all-MiniLM-L6-v2`.
   - *Truncate title:* Cắt ngắn tiêu đề xuống < 8 ký tự (ví dụ: `"Advan"`), vừa vi phạm chốt chặn GX `ExpectColumnValueLengthsToBeBetween`, vừa làm hỏng cơ chế exact title lookup của QA agent.
   - *Stale date:* Trừ 500 ngày vào trường `published` của 9 bài báo, đẩy `age_days` vượt xa ngưỡng 180 ngày. Tỷ lệ bài quá hạn tăng lên **57.1%** (vượt xa trần SLA 25%), kích hoạt còi báo động Freshness SLA.
   - *Duplicate rows:* Nhân bản 2 dòng dữ liệu, vi phạm trực tiếp ràng buộc `ExpectColumnValuesToBeUnique` đối với khóa chính `paper_id`.
   - *Rebuild & Audit:* Tái tạo lại chuỗi 5 thành phần `text_for_embedding` và ghi lại file nhật ký `corruption_log.json`.

2. **Điều phối luồng tích hợp (`phase1.py` & `corruption_flow.py`):**
   - Thiết kế theo mô hình State Machine tuyến tính rõ ràng: nạp cấu hình `Settings` → nạp dữ liệu → sinh vector index → đánh giá với `evaluate_pipeline` → kiểm định chất lượng với GX 1.x & Freshness → tổng hợp báo cáo Markdown.
   - Cung cấp cơ chế phòng vệ (defensive fallback) cho các module reporting và quality checks để pipeline chạy hoàn toàn tự động mà không bị crash nếu có module đang hoàn thiện dở dang.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Clean DataFrame tuân thủ `CLEAN_COLUMNS` (16 cột), file raw `crossref_records.json` bất biến, bộ 10 câu hỏi test `test_set.json`. |
| **Output** | 2 collection ChromaDB (`papers-corrupted`, `papers-repaired`), 2 file metrics JSON, 2 file dataset corrupted/repaired CSV & JSON, và báo cáo đối chiếu `corruption_report.md`. |
| **Module phụ thuộc** | `ingestion.cleaning` (lấy schema và hàm clean thuần), `retrieval.index` (Chroma embedding indexer), `evaluation.metrics` (hàm đo Hit Rate và Token F1). |
| **Module sử dụng output** | Toàn bộ nhóm sử dụng các file metrics và báo cáo Markdown để hoàn thiện `group_report.md` và chuẩn bị nội dung Live Demo trước lớp. |
| **Điều kiện lỗi cần xử lý** | Dữ liệu bị thiếu cột, ChromaDB collection đã tồn tại (phải xoá collection cũ trước khi nạp mới), LLM Judge bị rate limit (sử dụng fallback heuristic token F1). |

### Cách xác minh

Chạy kiểm thử toàn bộ luồng thông qua các script entrypoint:

```bash
# 1. Chạy Baseline Phase 1
python script/run_phase1.py

# 2. Chạy luồng Corruption -> Repair -> Báo cáo đối chiếu
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả hai script chạy trơn tru từ đầu đến cuối, không gặp lỗi runtime; xuất bảng so sánh 3 trạng thái ra console chứng minh hiệu năng RAG sụt giảm khi dính data bẩn và phục hồi 100% sau repair.
- **Kết quả thực tế:**
  - Baseline: Hit Rate = 1.0, Token F1 = 1.0, Quality = PASS, Freshness = PASS.
  - Corrupted: Hit Rate = 0.8, Token F1 = 0.6741, Quality = FAIL (vi phạm unique, length), Freshness = FAIL (57.1% stale).
  - Repaired: Hit Rate = 1.0, Token F1 = 1.0, Quality = PASS, Freshness = PASS.
- **Artifact/log:** `data/results/corruption_log.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương án triển khai cơ chế Phục hồi dữ liệu (Data Repair) khi phát hiện Data Quality Gate báo lỗi.
- **Các phương án đã cân nhắc:**
  1. *Phương án A (In-place patching / Data cleaning trên tập corrupted):* Viết hàm quét qua DataFrame đang bị lỗi để tìm và vá lỗi cục bộ (ví dụ: drop các dòng trùng, điền giá trị mặc định cho summary bị rỗng, sửa lại ngày).
  2. *Phương án B (Idempotent re-ingestion & rebuilding from immutable raw snapshot):* Không sửa chữa trên dữ liệu đã biến dạng. Kích hoạt luồng đọc lại bản snapshot dữ liệu thô ban đầu `data/raw/crossref_records.json` và chạy lại toàn bộ quy trình làm sạch thuần túy `build_clean_dataframe()`.
- **Phương án đã chọn:** **Phương án B (Idempotent Repair from Raw Source)**.
- **Lý do:**
  - *Tính đúng đắn (Correctness):* In-place patching không thể khôi phục được 20% bản ghi mới nhất đã bị xóa mất (`drop_latest_records`). Khi dữ liệu đã mất đi, chỉ có quay về nguồn thô (raw lineage) mới phục hồi được đầy đủ thông tin.
  - *Tính Idempotent:* Phương án B biến toàn bộ quá trình phục hồi thành hàm thuần túy (pure function). Dù chạy lại 1 lần hay 100 lần, kết quả dữ liệu sạch tạo ra luôn đồng nhất.
  - *Data Lineage:* Duy trì mối liên hệ chặt chẽ giữa nguồn gốc dữ liệu thô và dữ liệu sạch phục vụ cho embedding.
- **Bằng chứng quyết định phù hợp:** Sau khi chạy Repair theo Phương án B, cả 24 bản ghi sạch được tái lập đầy đủ, chỉ số `retrieval_hit_rate` và `mean_token_f1` phục hồi tuyệt đối về mức 1.0 / 1.0.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ModuleNotFoundError: No module named 'core'
  ModuleNotFoundError: No module named 'pipelines'
  ```
- **Lệnh hoặc bước tái hiện:** Chạy trực tiếp `python .\src\pipelines\phase1.py` hoặc `python script/run_phase1.py` trên môi trường terminal PowerShell.
- **Nguyên nhân gốc:** Khi chạy script qua đường dẫn tương đối, Python runtime tự động đưa thư mục chứa script đang chạy vào `sys.path[0]` (ví dụ `src\pipelines\` hoặc `script\`), khiến Python không thể tìm thấy các package anh em nằm ngang cấp trong thư mục `src/` (như `core`, `retrieval`, `ingestion`) nếu package chưa được cài đặt vào virtualenv ở chế độ editable.
- **Cách xử lý:**
  1. Cài đặt project vào môi trường ở chế độ editable: `pip install -e .` (liên kết thư mục `src` theo đúng định nghĩa trong `pyproject.toml`).
  2. Bổ sung đoạn code kiểm tra và đưa đường dẫn `src/` vào `sys.path` một cách linh hoạt ngay đầu các file pipeline khi chạy độc lập:
     ```python
     import sys
     from pathlib import Path

     _SRC_DIR = str(Path(__file__).resolve().parents[1])
     if _SRC_DIR not in sys.path:
         sys.path.insert(0, _SRC_DIR)
     ```
- **Cách xác minh sau khi sửa:** Cả hai cách gọi lệnh `python script/run_phase1.py` và `python .\src\pipelines\phase1.py` đều thực thi trơn tru mà không gặp bất kỳ lỗi import nào.
- **Điều học được:** Khi phát triển dự án Python module hóa theo cấu trúc `src/ layout`, phải luôn tuân thủ quy tắc quản lý package với `pyproject.toml` và hiểu rõ cơ chế phân giải đường dẫn của `sys.path` trên các hệ điều hành khác nhau.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Dữ liệu thô được truy vấn từ Crossref REST API (hoặc đọc từ snapshot local `crossref_response.json`) → được parse thành danh sách đối tượng `PaperRecord` lưu vào `crossref_records.json` → được làm sạch bằng `cleaning.py` (loại bỏ JATS XML tag, chuẩn hóa khoảng trắng, tính `age_days`, khử trùng lặp theo `paper_id`) → tạo cấu trúc văn bản 5 thành phần `text_for_embedding` → sinh vector embedding thông qua mô hình `sentence-transformers/all-MiniLM-L6-v2` → đánh chỉ mục và lưu trữ bền vững vào cơ sở dữ liệu vector ChromaDB.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Bộ benchmark gồm 10 câu hỏi bao quát 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`). Mỗi câu hỏi có gắn kèm danh sách `ground_truth_doc_ids` (ID của bài báo chứa thông tin chuẩn) và `ground_truth` (câu trả lời mẫu).
   - Khi đánh giá, hệ thống thực hiện semantic search trên ChromaDB để lấy Top-k tài liệu. Nếu tài liệu trả về chứa `ground_truth_doc_ids`, `retrieval_hit` được tính là 1.0 (đo `retrieval_hit_rate`). Câu trả lời do hệ thống sinh ra tiếp tục được so sánh với `ground_truth` thông qua chỉ số Token F1 và LLM Judge (đo `mean_token_f1`, `judge_accuracy`, `mean_judge_score`).

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - *Quality checks (Great Expectations 1.x):* Kiểm tra tính toàn vẹn tĩnh của dữ liệu (schema, kiểu dữ liệu, ràng buộc giá trị). Ví dụ: kiểm tra bảng có đủ dòng không, `paper_id` có bị null hoặc trùng lặp không, `title` và `summary` có đạt độ dài tối thiểu không.
   - *Freshness monitoring (Freshness SLA):* Đo lường tính thời sự và độ trôi dạt theo thời gian (temporal freshness / data drift) của dữ liệu so với hiện tại. Tính toán khoảng cách `age_days = (run_date - published).days` và kiểm tra xem tỷ lệ bài báo quá hạn (`age_days > 180`) có vượt quá ngưỡng cho phép (25%) hay không.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Trong nghiên cứu khoa học và kỹ thuật phần mềm, để đo lường tác động của một nhân tố (ở đây là biến số chất lượng dữ liệu), ta phải cố định toàn bộ các nhân tố còn lại (bộ câu hỏi test, ground truth, cấu hình retrieval top-k, mô hình embedding). Nếu đổi test set giữa các trạng thái, phép so sánh sẽ mất tính chuẩn hóa và không còn giá trị chứng minh nhân quả.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - *Về artifacts:* Xuất hiện đầy đủ `papers_clean_repaired.{csv,json}`, collection ChromaDB `papers-repaired`, file số liệu `repaired_metrics.json`, và báo cáo `corruption_report.md`.
   - *Về metrics:*
     - `retrieval_hit_rate` phục hồi từ 0.8 lên đúng 1.0.
     - `mean_token_f1` phục hồi từ 0.6741 lên đúng 1.0.
     - Data Quality checks chuyển từ **FAIL** (vi phạm 3 tiêu chí) trở lại **PASS** (100% pass cả 7 expectations).
     - Freshness SLA chuyển từ **STALE (57.1% quá hạn)** trở lại **FRESH (4.2% quá hạn, đạt SLA <= 25%)**.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **1.0000** | **0.8000** | **1.0000** | Giảm 20% do 5 bài báo mới nhất bị drop; sau khi repair từ raw records, tỷ lệ tìm kiếm đúng tài liệu đạt lại 100%. |
| `mean_token_f1` | **1.0000** | **0.6741** | **1.0000** | Sụt giảm mạnh 32.6% do tóm tắt bị xóa rỗng, tiêu đề bị cắt ngắn và nhiễu embedding; phục hồi hoàn hảo sau repair. |
| `judge_accuracy` | **1.0000** | **0.7000** | **1.0000** | Độ chính xác thẩm định của Agent giảm về 70% trên dữ liệu lỗi và phục hồi 100% sau khi sửa chữa. |
| `mean_judge_score` | **5.00 / 5** | **3.80 / 5** | **5.00 / 5** | Điểm số đánh giá chất lượng câu trả lời giảm 1.2 điểm do thông tin ngữ cảnh bị suy thoái. |
| Quality checks | **PASS** | **FAIL** | **PASS** | Corrupted vi phạm uniqueness của `paper_id` (4 lỗi), độ dài `title` (3 lỗi) và `summary` (2 lỗi); Repaired vượt qua toàn bộ. |
| Freshness status | **FRESH (4.2%)** | **STALE (57.1%)** | **FRESH (4.2%)** | Dữ liệu lỗi có 12/21 bài quá 180 ngày (vi phạm trần 25%); dữ liệu phục hồi chỉ còn 1/24 bài quá hạn, đạt chuẩn SLA. |

### Kết luận từ số liệu

1. **Chuỗi suy thoái:**
   `Tiêm 6 kịch bản corruption` → `Quality Gate báo FAIL (uniqueness, length) & Freshness SLA báo STALE (57.1%)` → `Retrieval Hit Rate rơi xuống 0.80, Token F1 rơi xuống 0.6741`.
2. **Chuỗi phục hồi:**
   `Kích hoạt Idempotent Repair từ raw records bất biến` → `Quality Gate chuyển lại PASS & Freshness SLA đạt chuẩn FRESH (4.2%)` → `Retrieval Hit Rate và Token F1 phục hồi 100% về mức 1.00`.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
- Hai kịch bản ảnh hưởng nặng nề nhất là **Drop latest records** và **Blank summary**:
  - *Drop latest records* gây mất mát hoàn toàn dữ liệu trong vector store. Các câu hỏi liên quan đến tài liệu bị drop (như `q01`, `q02`) chắc chắn nhận `retrieval_hit = False`, khiến Agent hoàn toàn không có ngữ cảnh để trả lời.
  - *Blank summary* khiến phần thông tin cốt lõi nhất của bài báo biến mất. Khi người dùng hỏi tóm tắt (`q05`), câu trả lời trả về chuỗi rỗng dẫn đến Token F1 = 0, minh chứng rõ ràng cho hiện tượng Silent Failure.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Dữ liệu nguồn phải luôn được bảo toàn nguyên trạng dưới dạng Raw Snapshot bất biến (`crossref_records.json`). Mọi thao tác làm sạch và tiền xử lý phải được thiết kế dưới dạng các hàm thuần túy để đảm bảo tính Idempotent — nền tảng cho việc tự phục hồi hệ thống khi có sự cố.
2. **Về Data Observability:** Chốt chặn chất lượng dữ liệu (Quality Gates) kết hợp cùng giám sát tính thời sự (Freshness SLAs) là yêu cầu sống còn. Nếu không có Observability, các sự cố dữ liệu bẩn sẽ âm thầm lọt vào vector store và gây lỗi nghiêm trọng ở tầng ứng dụng AI.
3. **Về RAG Agent:** "Garbage In, Garbage Out" — hiệu năng của LLM và Vector Search phụ thuộc tuyệt đối vào chất lượng của dữ liệu đầu vào. Ngay cả mô hình embedding và LLM mạnh nhất cũng sẽ thất bại nếu văn bản bị chèn nhiễu, cắt ngắn hoặc thiếu hụt.

### Nếu có thêm thời gian

Nếu có thêm thời gian, tôi sẽ xây dựng một cơ chế **Automated Circuit Breaker (Ngắt mạch tự động)**:
- Ngay khi Data Quality Gate hoặc Freshness SLA trả về tín hiệu `FAIL`, hệ thống sẽ tự động chặn không cho phép cập nhật dữ liệu mới vào ChromaDB vector collection chính thức, đồng thời tự động kích hoạt tiến trình Idempotent Repair chạy ngầm và gửi cảnh báo qua Webhook/Discord.
- Hiệu quả cải thiện có thể đo lường bằng việc thời gian gián đoạn dịch vụ (MTTR - Mean Time to Recovery) giảm từ thao tác thủ công xuống dưới 5 giây hoàn toàn tự động.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lê Quang Thành  
**Ngày xác nhận:** 2026-09-26
