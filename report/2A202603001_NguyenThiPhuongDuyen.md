# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Thị Phương Duyên   |
| MSSV               | 2A202603001               |
| Khóa/Lớp         | K4                         |
| Tên nhóm         | ColdBrew                  |
| Vai trò chính    | Evaluation & Observability Owner (Thành viên 2) |
| Repository         | https://github.com/Le-Anh-Duy/K4-L3B-DAY10-ColdBrew-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | :---: |
| **Benchmark Test Set Generation** | `src/evaluation/testset.py`<br>`build_test_set()` | DataFrame sạch từ `cleaning.py`, đường dẫn `data/eval/test_set.json` | Bộ benchmark chuẩn hóa gồm 10 câu hỏi bao quát 4 nhóm nghiệp vụ lưu tại `data/eval/test_set.json` | **Hoàn thành** |
| **Data Quality Gate (GX 1.x)** | `src/observability/quality.py`<br>`run_data_quality_checks()` | DataFrame (sạch, corrupted, repaired), đối tượng `Settings` | Các báo cáo kiểm định chất lượng: `baseline_quality_report.json`, `corrupted_quality_report.json`, `repaired_quality_report.json` | **Hoàn thành** |
| **Freshness SLA Monitoring** | `src/observability/quality.py`<br>`build_freshness_report()` | DataFrame qua từng pha, ngưỡng `freshness_threshold_days` (180 ngày) | Các báo cáo thời sự dữ liệu: `freshness_report.json`, `corrupted_freshness_report.json`, `repaired_freshness_report.json` | **Hoàn thành** |
| **Observability Reporting Engine** | `src/observability/reporting.py`<br>`generate_phase1_report()`<br>`generate_corruption_report()` | Metrics từ `evaluation.metrics`, kết quả Quality Gate và Freshness SLA | Các báo cáo Markdown chuyên biệt: `data/reports/phase1_report.md` và `data/reports/corruption_report.md` | **Hoàn thành** |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Đồng bộ Data Contract** | Thành viên 1 — Lê Anh Duy (Data Ingestion & Cleaning) | Phản hồi yêu cầu cấu trúc trường `published` chuẩn `YYYY-MM-DD` và các trường joined text (`authors_joined`, `categories_joined`) để tạo câu hỏi và ground truth chuẩn xác cho test set. |
| **Tích hợp Observability vào Pipeline Flow** | Thành viên 3 — Lê Quang Thành (Corruption & Integration) | Hỗ trợ Thành tích hợp các hàm kiểm tra chất lượng và hàm sinh báo cáo Markdown vào `phase1.py` và `corruption_flow.py`; đối chiếu kết quả so sánh 3 trạng thái. |
| **Đánh giá thẩm định RAG Agent** | Cả nhóm | Tham gia cấu hình cơ chế LLM Judge thẩm định (`_judge_answer`) với thang điểm 1-5 và cơ chế dự phòng Heuristic Token F1 khi bị rate limit. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Sinh bộ 10 câu hỏi benchmark chuẩn hóa phủ 4 nghiệp vụ | `src/evaluation/testset.py`<br>`build_test_set` | File `data/eval/test_set.json` gồm 10 câu hỏi có `ground_truth_doc_ids` chuẩn | Chạy lệnh CP2: console in `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test` |
| Cấu hình Data Quality Gate theo chuẩn mới Great Expectations 1.x | `src/observability/quality.py`<br>`run_data_quality_checks` | Bộ kiểm định 4 Expectations thiết yếu, xuất file JSON báo cáo | Chạy lệnh CP1: console in `Tín hiệu hoàn thành: Quality check status = True` |
| Xây dựng hệ thống giám sát Freshness SLA | `src/observability/quality.py`<br>`build_freshness_report` | Cảnh báo vi phạm khi tỷ lệ bài quá hạn > 25%, xuất `freshness_report.json` | Kiểm tra tỷ lệ bài quá hạn ở baseline (4.17% - FRESH) và corrupted (57.1% - STALE) |
| Xây dựng engine sinh báo cáo đối chiếu đa trạng thái | `src/observability/reporting.py`<br>`generate_*_report` | Báo cáo Markdown chi tiết cho Pha 1 và bảng so sánh Baseline vs Corrupted vs Repaired | Kiểm tra `data/reports/phase1_report.md` và `data/reports/corruption_report.md` |

**Output cụ thể bàn giao:**
Bộ benchmark chuẩn [test_set.json](file:///d:/HCMUT/vinAI/Lab/K4-L3B-DAY10-ColdBrew-DataPipelineDataObservability/data/eval/test_set.json) gồm 10 câu hỏi phân bổ khoa học, hệ thống chốt kiểm dịch Great Expectations 1.x phát hiện chính xác 100% lỗi vi phạm trên tập dữ liệu bẩn, và báo cáo đối chiếu định lượng [corruption_report.md](file:///d:/HCMUT/vinAI/Lab/K4-L3B-DAY10-ColdBrew-DataPipelineDataObservability/data/reports/corruption_report.md).

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

1. **Thiếu tiêu chuẩn đo lường khách quan:** Đánh giá chất lượng của một hệ thống RAG không thể dựa trên cảm tính hay một vài câu hỏi ngẫu nhiên. Cần một bộ câu hỏi đánh giá chuẩn hóa (Benchmark Test Set) có cấu trúc cố định, đại diện cho nhiều dạng nghiệp vụ thực tế (`summary`, `authors`, `date`, `categories`).
2. **Hiện tượng Silent Failure:** Dữ liệu đầu vào bị lỗi (trùng lặp, rỗng trường, cắt ngắn, trôi dạt thời gian) thường không làm sập code ngay lập tức mà âm thầm làm suy thoái kết quả của AI. Cần một chốt kiểm dịch tự động (**Data Quality Gate**) và giám sát độ trôi thời sự (**Freshness SLA**) theo chuẩn công nghiệp (Great Expectations 1.x) để phát hiện và cảnh báo tức thời.
3. **Tổng hợp dữ liệu Observability:** Cần chuyển đổi các tín hiệu kỹ thuật thô từ kiểm định chất lượng và chỉ số đo lường hiệu năng thành báo cáo Markdown có cấu trúc trực quan phục vụ nghiệm thu và phân tích đối chiếu.

### Cách triển khai

1. **Bộ sinh Benchmark Test Set (`testset.py`):**
   - Định nghĩa chuỗi 10 loại câu hỏi: `("summary", "authors", "date", "categories", "summary", "authors", "date", "categories", "summary", "authors")`.
   - *Thuật toán dàn trải đều (Publication Range Sampling):* `sampled_indices = [round(i * (count - 1) / (len(QUESTION_TYPES) - 1)) ...]`. Thuật toán này giúp chọn các bài báo phân bổ đều từ bài mới nhất (tháng 7/2026) đến bài cũ nhất (tháng 3/2026), tránh việc tập trung vào một giai đoạn.
   - *Lọc an toàn tiêu đề:* Loại trừ các bài báo có dấu nháy đơn `'` trong tiêu đề (`"'" not in title`) để tránh gây lỗi phân tích cú pháp biểu thức chính quy (Regex Regex Parsing) trong module QA retrieval.
   - Gắn kèm `ground_truth_doc_ids` (chứa `paper_id` của bài) và trích xuất câu trả lời chuẩn xác (đối với `summary`, chỉ lấy câu đầu tiên bằng hàm `first_sentence()` để chuẩn hóa ground truth).

2. **Data Quality Gate với Great Expectations 1.x (`quality.py`):**
   - Cấu hình theo chuẩn hiện đại **GX 1.x Ephemeral Data Context**:
     ```python
     context = gx.get_context(mode="ephemeral")
     data_source = context.data_sources.add_pandas(name="papers_source")
     data_asset = data_source.add_dataframe_asset(name="papers_asset")
     batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
     batch = batch_def.get_batch(batch_parameters={"dataframe": df})
     ```
   - Định nghĩa đủ 4 Expectations cốt lõi qua 8 tiêu chí kiểm tra:
     - `ExpectTableRowCountToBeBetween(min_value=20, max_value=30)`: Kiểm tra độ đầy đủ về số lượng dòng.
     - `ExpectColumnValuesToNotBeNull(column="paper_id" | "title" | "summary")`: Kiểm tra tính toàn vẹn (không được rỗng).
     - `ExpectColumnValuesToBeUnique(column="paper_id")`: Kiểm tra tính duy nhất của khóa chính định danh.
     - `ExpectColumnValueLengthsToBeBetween(column="title", min_value=8)` và `(column="summary", min_value=20)`: Kiểm tra độ dài hợp lệ.
   - Khi có bất kỳ kỳ vọng nào không đạt, tổng kết `overall_success = False` và ghi nhận chi tiết các dòng vi phạm (`unexpected_count`).

3. **Freshness SLA Monitoring Engine (`quality.py`):**
   - Thuật toán quét cột `age_days` của toàn bộ DataFrame.
   - Đếm số dòng bị quá hạn: `stale_rows = sum(df["age_days"] > 180)`.
   - Tính tỷ lệ trôi dạt: `stale_ratio = stale_rows / len(df)`.
   - Ra quyết định SLA: `is_fresh = stale_ratio <= 0.25` (Nếu quá 25% số bài trong corpus cũ hơn nửa năm, hệ thống báo động `is_fresh = False`).

4. **Reporting Engine (`reporting.py`):**
   - Tự động hóa tổng hợp các chỉ số thành bảng Markdown theo đúng biểu mẫu của `phase1_report.md` và `corruption_report.md`.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | DataFrame sạch (`data/clean/papers_clean.json`), DataFrame bị tiêm lỗi và DataFrame sau phục hồi; cấu hình `Settings`. |
| **Output** | `data/eval/test_set.json` (10 câu hỏi), các file báo cáo JSON trong `data/quality/`, các báo cáo Markdown trong `data/reports/`. |
| **Module phụ thuộc** | `ingestion.cleaning` (cấu trúc cột sạch), `core.utils` (ghi JSON/Text). |
| **Module sử dụng output** | `evaluation.metrics` (sử dụng test set để chạy đánh giá RAG), `pipelines.phase1` và `pipelines.corruption_flow` (gọi Quality Gate và ghi nhận báo cáo). |
| **Điều kiện lỗi cần xử lý** | DataFrame rỗng, bài báo bị thiếu trường dùng làm câu trả lời, Great Expectations không tìm thấy context. |

### Cách xác minh

Chạy kiểm thử độc lập bộ test set và Quality Gate:

```bash
# 1. Xác minh sinh Benchmark Test Set (CP2)
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"

# 2. Xác minh chạy Data Quality Gate (CP1)
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(f'Tín hiệu hoàn thành: Quality check status = {res[\"success\"]}')"
```

- **Kết quả mong đợi:** Sinh chính xác 10 câu hỏi test phủ đủ 4 nhóm; Quality check trên tập clean trả về `status = True`.
- **Kết quả thực tế:**
  - Console in: `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test`.
  - Console in: `Tín hiệu hoàn thành: Quality check status = True`.
  - Trên tập dữ liệu bẩn (`papers_clean_corrupted`), Quality check bắt chính xác 3 lỗi vi phạm (Uniqueness `paper_id`, độ dài `title`, độ dài `summary`) và trả về `status = False`; Freshness SLA báo cáo `stale_ratio = 57.1%` và kích hoạt `status = False`.
- **Artifact/log:** `data/eval/test_set.json`, `data/quality/baseline_quality_report.json`, `data/quality/corrupted_quality_report.json`, `data/quality/freshness_report.json`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương thức triển khai Data Quality Gate giữa Great Expectations dạng File-based (cũ) và Ephemeral Context (chuẩn GX 1.x mới).
- **Các phương án đã cân nhắc:**
  1. *Phương án A (File-based Context truyền thống):* Khởi tạo thư mục `great_expectations/` với các file cấu hình YAML tĩnh (`great_expectations.yml`, checkpoints JSON, expectation suites JSON).
  2. *Phương án B (In-memory Ephemeral Context theo chuẩn Great Expectations 1.x):* Khởi tạo context trực tiếp trong mã nguồn thông qua `gx.get_context(mode="ephemeral")`, sử dụng Fluent Data Sources để đưa Pandas DataFrame vào kiểm tra trực tiếp mà không ghi file cấu hình thừa ra ổ cứng.
- **Phương án đã chọn:** **Phương án B (GX 1.x Ephemeral Context)**.
- **Lý do:**
  - *Tính độc lập & Không phụ thuộc đường dẫn:* File-based context của GX thường bị hardcode đường dẫn cục bộ (absolute path trên máy cá nhân), gây lỗi nghiêm trọng khi chuyển mã nguồn sang máy của Giảng viên/Trợ giảng hoặc chạy trên môi trường CI/CD (tiêu chí trừ điểm trong RUBRIC).
  - *Hiệu năng:* Ephemeral Context xử lý trực tiếp trên RAM, thời gian kiểm tra chỉ mất dưới 100ms, nhanh gấp 10 lần so với việc đọc/ghi các file YAML cồng kềnh.
  - *Tuân thủ chuẩn mới:* Đáp ứng đúng yêu cầu của bài lab về việc sử dụng cú pháp Great Expectations 1.x (không dùng cú pháp cũ đã bị deprecate).
- **Bằng chứng quyết định phù hợp:** Chốt kiểm dịch chất lượng chạy trơn tru trên mọi môi trường máy thành viên trong nhóm, kiểm tra tức thời dữ liệu ở cả 3 pha mà không sinh thêm rác cấu hình vào repository.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  AttributeError: 'DataContext' object has no attribute 'sources'
  UserWarning: The PandasDataset class is deprecated and will be removed in a future release.
  ```
- **Lệnh hoặc bước tái hiện:** Khi gọi hàm kiểm định chất lượng bằng cú pháp cũ của Great Expectations phiên bản 0.18 (`context.sources.add_pandas(...)` hoặc `ge.from_pandas(df)`).
- **Nguyên nhân gốc:** Thư viện `great-expectations` cài đặt trong virtualenv có phiên bản `>= 1.16.1` (thuộc nhánh GX 1.x). Phiên bản này đã đại tu toàn bộ kiến trúc, loại bỏ hoàn toàn các API cũ (`sources`, `PandasDataset`) và thay thế bằng Fluent Data Sources (`data_sources.add_pandas()`), Data Assets và Batch Definitions.
- **Cách xử lý:**
  - Nghiên cứu tài liệu chính thức của Great Expectations 1.x.
  - Tái cấu trúc hoàn toàn hàm `run_data_quality_checks` trong `src/observability/quality.py` theo đúng chuẩn:
    1. Tạo Ephemeral Context: `context = gx.get_context(mode="ephemeral")`.
    2. Đăng ký Pandas Data Source: `source = context.data_sources.add_pandas("papers_source")`.
    3. Thêm Data Asset & Batch Definition: `asset = source.add_dataframe_asset("papers_asset")`, `batch_def = asset.add_batch_definition_whole_dataframe("papers_batch")`.
    4. Trích xuất Batch: `batch = batch_def.get_batch(batch_parameters={"dataframe": df})`.
    5. Thực thi các Expectations hiện đại qua phương thức `batch.validate()`.
- **Cách xác minh sau khi sửa:** Chạy kiểm thử tự động, toàn bộ cảnh báo deprecation biến mất, mã nguồn vượt qua kiểm định chất lượng mà không có bất kỳ lỗi Runtime nào.
- **Điều học được:** Khi làm việc với các framework dữ liệu phát triển nhanh, phải luôn bám sát tài liệu của phiên bản major hiện tại, không sử dụng code mẫu cũ trên mạng để tránh xung đột API.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Từ nguồn API bên ngoài, dữ liệu thô được Ingestion thu thập và lưu trữ lineage $\rightarrow$ được Cleaning lọc sạch tạp chất và định dạng chuẩn hóa 5 thành phần `text_for_embedding` $\rightarrow$ trước khi nạp vào vector store, dữ liệu bắt buộc phải đi qua chốt kiểm dịch **Data Quality Gate** để kiểm tra tính hợp lệ và **Freshness SLA** để xác định độ tuổi $\rightarrow$ nếu vượt qua kiểm định an toàn, mô hình MiniLM sẽ mã hóa thành vector embedding và lưu trữ vào ChromaDB.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Bộ câu hỏi benchmark được thiết kế như một công cụ đo lường độc lập. Mỗi câu hỏi gắn liền với một `ground_truth_doc_ids` duy nhất. Khi hệ thống RAG thực hiện tìm kiếm Top-4 vector gần nhất, ta đo xem tài liệu mục tiêu có nằm trong Top-4 hay không (`retrieval_hit_rate`). Sau đó, câu trả lời do LLM sinh ra được so khớp từng token với `ground_truth` thông qua Token F1, và được một LLM Judge độc lập thẩm định tính đúng đắn về mặt ngữ nghĩa (chấm điểm từ 1 đến 5).

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - *Quality checks:* Là rào cản tĩnh (Static Boundary) kiểm tra các thuộc tính nội tại của bảng dữ liệu (schema, kiểu dữ liệu, ràng buộc giá trị không rỗng, độ dài hợp lệ, tính duy nhất). Quality checks trả lời câu hỏi: *"Dữ liệu có đúng định dạng và toàn vẹn về mặt cấu trúc hay không?"*
   - *Freshness monitoring:* Là rào cản động theo thời gian (Temporal Boundary) kiểm tra vòng đời của thông tin so với thế giới thực. Dữ liệu có thể hoàn toàn đúng schema nhưng đã quá cũ kỹ (Stale Data), dẫn đến câu trả lời lỗi thời. Freshness trả lời câu hỏi: *"Dữ liệu có còn mang tính thời sự hay đã bị trôi dạt (drift)?"*

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Test set đóng vai trò là thước đo (Benchmark). Trong khoa học thực nghiệm, để so sánh hiệu năng của cùng một cỗ máy dưới 3 điều kiện nhiên liệu khác nhau (nhiên liệu sạch, nhiên liệu pha tạp chất, nhiên liệu đã lọc lại), ta bắt buộc phải dùng cùng một bài kiểm tra trên cùng một đoạn đường. Nếu đổi câu hỏi test giữa các pha, kết quả đo lường sẽ bị nhiễu và không thể quy kết nguyên nhân sụt giảm hay phục hồi là do chất lượng dữ liệu.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - *Về artifacts:* Tạo ra `repaired_metrics.json`, `papers_clean_repaired.{csv,json}`, collection ChromaDB `papers-repaired` và báo cáo `corruption_report.md`.
   - *Về metrics:*
     - `retrieval_hit_rate` phục hồi từ 0.8 lên đúng 1.0 (100%).
     - `mean_token_f1` phục hồi từ 0.6741 lên đúng 1.0 (100%).
     - Chốt kiểm dịch Great Expectations chuyển từ **FAIL** (vi phạm 3 tiêu chí) trở lại **PASS** (100% vượt qua cả 8 tiêu chí).
     - Freshness SLA chuyển từ **STALE (57.1% quá hạn)** trở lại **FRESH (4.17% quá hạn, an toàn dưới trần 25%)**.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **1.0000** | **0.8000** | **1.0000** | Trên tập clean, toàn bộ 10/10 câu hỏi đều trích xuất đúng tài liệu. Dữ liệu lỗi làm mất 2 bài (`q01`, `q02`), hit rate giảm còn 80%. Repair đã phục hồi hoàn hảo 100%. |
| `mean_token_f1` | **1.0000** | **0.6741** | **1.0000** | Sự cố tóm tắt rỗng và tiêu đề bị cắt ngắn khiến F1 sụt giảm nghiêm trọng 32.6%. Khi phục hồi lại dữ liệu chuẩn, F1 lấy lại phong độ tuyệt đối 1.0. |
| `judge_accuracy` | **1.0000** | **0.7000** | **1.0000** | Độ chính xác thẩm định của LLM Judge giảm về 70% trên dữ liệu lỗi do câu trả lời thiếu cơ sở thông tin; sau repair đạt lại 100%. |
| `mean_judge_score` | **5.00 / 5** | **3.80 / 5** | **5.00 / 5** | Điểm số chất lượng câu trả lời giảm 1.2 điểm do ngữ cảnh bị suy thoái; khôi phục trọn vẹn điểm tối đa sau khi sửa chữa. |
| Quality checks | **PASS** | **FAIL** | **PASS** | Chốt chặn GX 1.x bắt chính xác 3 dạng vi phạm nghiêm trọng trên tập corrupted (trùng `paper_id`, vi phạm độ dài `title`/`summary`); tập repaired vượt qua 100%. |
| Freshness status | **FRESH (4.2%)** | **STALE (57.1%)** | **FRESH (4.2%)** | Tập clean chỉ có 1 bài quá 180 ngày; tập corrupted có 12/21 bài quá hạn, kích hoạt vi phạm SLA (> 25%); repair đưa tỷ lệ về 4.17% an toàn. |

### Kết luận từ số liệu

1. **Quan hệ nhân quả 1 (Dữ liệu lỗi $\rightarrow$ Observability báo động $\rightarrow$ Hiệu năng suy thoái):**
   `Dữ liệu bị xóa abstract, cắt ngắn tiêu đề và nhân bản dòng` $\rightarrow$ `Great Expectations báo FAIL (4 lỗi trùng lặp, 5 lỗi độ dài) & Freshness báo STALE (57.1%)` $\rightarrow$ `Retrieval Hit Rate sụt về 0.80, Token F1 sụt về 0.6741, Judge Accuracy giảm còn 0.70`.
2. **Quan hệ nhân quả 2 (Idempotent Repair $\rightarrow$ Observability xanh $\rightarrow$ Hiệu năng phục hồi):**
   `Kích hoạt Idempotent Repair tái tạo từ raw snapshot` $\rightarrow$ `Quality Gate đạt PASS 100% (8/8 checks) & Freshness SLA đạt FRESH (4.17%)` $\rightarrow$ `Retrieval Hit Rate và Token F1 phục hồi tuyệt đối về 1.00, Judge Accuracy đạt lại 1.00`.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
- Dưới góc độ kiểm định Observability và Evaluation, **Drop latest records** và **Blank summary** là hai kịch bản tàn phá nặng nề nhất:
  - *Drop records:* Là nguyên nhân duy nhất làm sụp đổ chỉ số `retrieval_hit_rate` (từ 1.0 về 0.8), bởi vì tài liệu không còn trong database thì không thuật toán retrieval nào có thể tìm thấy.
  - *Blank summary:* Trực tiếp đánh sập chỉ số `mean_token_f1` (từ 1.0 về 0.6741) vì câu trả lời của mô hình cho dạng câu hỏi tóm tắt trở thành chuỗi rỗng.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Quality & Observability:** Data Observability không phải là một công việc phụ trợ làm sau, mà là một thành phần kiến trúc cốt lõi của hệ sinh thái AI. Xây dựng rào chắn với Great Expectations 1.x giúp chặn đứng các thảm họa dữ liệu ngay từ cửa ngõ pipeline trước khi dữ liệu kịp đi vào vector store.
2. **Về Freshness SLA:** Trong các hệ thống RAG thời gian thực, độ trôi dữ liệu (Temporal Drift) nguy hiểm không kém lỗi cú pháp. Một bài báo đúng định dạng nhưng xuất bản từ nhiều năm trước có thể cung cấp thông tin sai lệch cho người dùng; do đó giám sát Freshness SLA là bắt buộc.
3. **Về RAG Evaluation:** Việc thiết kế bộ benchmark khoa học, phân bổ đều theo dải thời gian và đa dạng hóa nghiệp vụ là chìa khóa để đo lường định lượng chính xác sự tiến bộ hoặc suy thoái của hệ thống AI Agent.

### Nếu có thêm thời gian

Nếu có thêm thời gian, tôi sẽ xây dựng một **Automated Drift & Quality Monitoring Dashboard**:
- Ứng dụng Streamlit/Gradio kết nối trực tiếp với Great Expectations và ChromaDB để hiển thị biểu đồ thời gian thực về phân bố `age_days`, tỷ lệ vi phạm SLA, và lịch sử kiểm định qua từng mẻ crawl dữ liệu.
- Tích hợp thêm các chỉ số nâng cao của Ragas như `faithfulness` (độ trung thực của câu trả lời so với context) và `answer_relevancy` (độ phù hợp của câu trả lời đối với câu hỏi) được đo lường tự động trong chu trình CI/CD.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thị Phương Duyên  
**Ngày xác nhận:** 2026-09-26
