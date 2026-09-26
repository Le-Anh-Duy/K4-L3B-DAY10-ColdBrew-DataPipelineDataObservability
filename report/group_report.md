# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4                         |
| Tên nhóm         | ColdBrew                   |
| Repository         | https://github.com/Le-Anh-Duy/K4-L3B-DAY10-ColdBrew-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Lê Anh Duy | 2A202602723 | Data ingestion & cleaning owner | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`; raw/clean schema contract và artifacts trong `data/raw/`, `data/clean/` |
| 2 | Nguyễn Thị Phương Duyên | 2A202603001 | Evaluation & observability owner | `src/evaluation/testset.py`, `src/observability/quality.py`, `src/observability/reporting.py`; benchmark test set `data/eval/test_set.json`, GX 1.x quality suite và Freshness SLA |
| 3 | Lê Quang Thành | 2A202602647 | Corruption & integration owner | `src/ingestion/corruption.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`; điều phối 2 flow end-to-end, corruption log, metrics và comparison report |

---

## 2. Tóm tắt kết quả

Nhóm ColdBrew đã hoàn thành trọn vẹn chu trình Data Pipeline & Data Observability phục vụ hệ thống RAG Agent từ Checkpoint 0 đến Checkpoint 6. Nhóm đã thu thập 24 bản ghi nghiên cứu từ Crossref REST API (có cơ chế offline snapshot fallback), chuẩn hóa văn bản, tính toán `age_days` và cấu trúc trường `text_for_embedding` theo đúng Data Contract. 

Pipeline Baseline (Pha 1) được điều phối tự động, đánh chỉ mục 24 tài liệu sạch vào ChromaDB collection `papers-baseline` và đánh giá qua bộ benchmark 10 câu hỏi chuẩn hóa thuộc 4 nhóm nghiệp vụ. Kết quả baseline đạt hiệu năng tuyệt đối với `retrieval_hit_rate = 1.0` và `mean_token_f1 = 1.0`, đồng thời vượt qua 100% các chốt kiểm định Great Expectations 1.x và đạt chuẩn Freshness SLA (tỷ lệ quá hạn 4.2% <= 25%).

Khi kích hoạt Synthetic Data Corruption Suite với 6 kịch bản lỗi thực tế (drop latest records, blank summary, inject noise, truncate title, stale date, duplicate rows), hệ thống đã chứng minh rõ nét hiện tượng **Silent Failure**: `retrieval_hit_rate` giảm xuống `0.80`, `mean_token_f1` sụt giảm mạnh về `0.6741`, LLM Judge score giảm từ 5.0 xuống 3.8. Cùng lúc đó, Data Observability Gate đã lập tức báo động đỏ (Quality check vi phạm uniqueness và độ dài; Freshness SLA vi phạm với 57.1% bản ghi quá hạn).

Nhóm đã kích hoạt thành công cơ chế **Idempotent Repair** từ nguồn lưu trữ thô bất biến `data/raw/crossref_records.json`. Quá trình khôi phục sạch hoàn toàn phục hồi hiệu năng RAG về mức ban đầu (`retrieval_hit_rate = 1.0`, `mean_token_f1 = 1.0`), đưa Quality Gate và Freshness SLA trở lại trạng thái PASS. Vấn đề import path khi tích hợp module đã được khắc phục triệt để bằng cấu hình editable install `pip install -e .` và `sys.path`.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Nguồn Crossref API (hoặc Snapshot Local fallback)
    │
    ├──> Ingestion (`crossref.py`) ──> data/raw/crossref_response.json & crossref_records.json
    │
    ├──> Cleaning (`cleaning.py`) ──> data/clean/papers_clean.{csv,json} (16 cột chuẩn, 5 phần text_for_embedding)
    │
    ├──> Indexing (`retrieval/index.py`) ──> ChromaDB collection 'papers-baseline' (all-MiniLM-L6-v2)
    │
    ├──> Evaluation (`testset.py`, `metrics.py`) ──> Benchmark 10 câu hỏi -> baseline_metrics.json (Hit Rate: 1.0, F1: 1.0)
    │
    ├──> Observability (`quality.py`, `reporting.py`) ──> GX 1.x Ephemeral Context (PASS) & Freshness SLA (FRESH: 4.2%)
    │
    ├──> Corruption Suite (`corruption.py`) ──> 6 kịch bản lỗi -> papers_clean_corrupted & corruption_log.json
    │                                          └──> Re-index 'papers-corrupted' -> Hit Rate: 0.80, F1: 0.6741, Quality: FAIL, Freshness: STALE
    │
    ├──> Idempotent Repair (`corruption_flow.py`) ──> Re-ingest từ crossref_records.json -> papers_clean_repaired
    │                                                └──> Re-index 'papers-repaired' -> Hit Rate: 1.0, F1: 1.0, Quality: PASS, Freshness: FRESH
    │
    └──> Comparison Report (`corruption_report.md`) ──> Đối chiếu định lượng 3 trạng thái: Baseline vs Corrupted vs Repaired
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | Crossref REST API / Snapshot local | Fetch API có retry backoff, parse payload thành `PaperRecord`, bảo toàn raw lineage | `data/raw/crossref_response.json`<br>`data/raw/crossref_records.json` | Lê Anh Duy |
| **Cleaning** | `list[PaperRecord]` từ raw records | Loại bỏ JATS XML tag, decode entity, gom khoảng trắng, tính `age_days`, khử trùng theo `paper_id`, tạo `text_for_embedding` | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` | Lê Anh Duy |
| **Embedding/Index** | DataFrame sạch/corrupted/repaired | Sinh vector embedding với MiniLM, quản lý 3 collection ChromaDB tách biệt (`papers-baseline`, `papers-corrupted`, `papers-repaired`) | `data/chroma/`<br>`data/embeddings/*.json` | Lê Quang Thành |
| **Evaluation** | Clean DataFrame, Vector Index | Xây dựng bộ benchmark 10 câu hỏi qua 4 nhóm nghiệp vụ, đánh giá `retrieval_hit_rate`, `mean_token_f1`, LLM Judge | `data/eval/test_set.json`<br>`data/results/*_metrics.json`<br>`data/results/*_answers.json` | Nguyễn Thị Phương Duyên |
| **Observability** | DataFrame qua từng pha, `Settings` | Cấu hình GX 1.x ephemeral context kiểm định 4 expectations thiết yếu, tính tỷ lệ `age_days > 180` theo Freshness SLA | `data/quality/*_quality_report.json`<br>`data/quality/*_freshness_report.json` | Nguyễn Thị Phương Duyên |
| **Corruption/Repair**| Clean DataFrame, Raw records bất biến | Tiêm 6 kịch bản lỗi thực tế (drop, blank, noise, truncate, stale, duplicate); thực thi Idempotent Repair tái tạo từ raw source | `data/results/corruption_log.json`<br>`data/clean/*_corrupted.*`<br>`data/clean/*_repaired.*` | Lê Quang Thành |
| **Orchestration** | Toàn bộ các module thành phần | Điều phối chu trình thực thi end-to-end `run_phase1.py` và `run_corruption_flow.py`, tổng hợp báo cáo đối chiếu | `data/reports/phase1_report.md`<br>`data/reports/corruption_report.md` | Lê Quang Thành |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER` | `gemini` |
| `LLM_MODEL` | `gemini-2.5-flash` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | `24` |
| Retrieval `top_k` | `4` |
| Freshness threshold | `180` ngày (ngưỡng cảnh báo: tỷ lệ bài quá hạn > 25%) |
| Random seed / Thứ tự | Cố định qua deterministic indexing (`sort_values(["published", "paper_id"])`) |

*(Lưu ý: Mọi API Key được cấu hình riêng trong file `.env` local, tuyệt đối không commit lên Git repository).*

### Lệnh cài đặt

Nhóm sử dụng môi trường virtualenv chuẩn với `pip`:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

### Lệnh chạy

1. **Chạy Baseline Phase 1 (Ingestion, Cleaning, Indexing, Baseline Evaluation, Quality Gate):**

   ```bash
   python script/run_phase1.py
   ```

2. **Chạy Corruption Flow (Tiêm lỗi -> Đo lường suy thoái -> Idempotent Repair -> Báo cáo đối chiếu):**

   ```bash
   python script/run_corruption_flow.py
   ```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | :---: | :---: | :--- |
| `run_phase1.py` | **Thành công** | 2026-09-26 11:05 (UTC+7) | Sinh đầy đủ 7 artifacts, console in `PHASE 1 COMPLETED SUCCESSFULLY!`, Hit Rate = 1.0, Token F1 = 1.0, Quality = PASS |
| `run_corruption_flow.py` | **Thành công** | 2026-09-26 11:06 (UTC+7) | Bảng đối chiếu 3 trạng thái in ra console, báo cáo `data/reports/corruption_report.md` ghi nhận sự phục hồi từ 0.8 lên 1.0 |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --------------------------- | ------------------------------------- |
| Source | Crossref REST API (`https://api.crossref.org/works`) / Offline Fallback Snapshot |
| Query/filter | `query=agentic retrieval augmented generation large language model`<br>`filter=from-pub-date:2026-03-30,has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-09-26T04:00:00Z |
| Số record nhận được | `24` bài báo khoa học có đầy đủ abstract và metadata ngày tháng |
| Cơ chế retry/backoff | Tối đa 4 lần retry khi gặp mã lỗi 429/500/502/503/504, áp dụng exponential backoff (2s, 4s, 8s) hoặc theo header `Retry-After`. Tự động fallback về `data/raw/crossref_response.json` khi mạng mất kết nối. |

### Raw và clean schema

Theo thỏa thuận chung trong [data_contract.md](data_contract.md):

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --------------- | --------------- | :---: | ----------- | ---------------------- |
| `paper_id` | `str` | Có | Định danh DOI chuẩn hóa chữ thường, unique | Loại bỏ khoảng trắng đầu/cuối, chuyển lowercase; nếu rỗng thì bỏ bản ghi |
| `title` | `str` | Có | Tiêu đề bài báo khoa học | Bỏ JATS/HTML tag, decode HTML entities, gom khoảng trắng thừa; nếu rỗng thì bỏ |
| `summary` | `str` | Có | Tóm tắt (abstract) | Bỏ tag JATS (kể cả `<jats:title>`), bỏ nhãn "Abstract" ở đầu; nếu rỗng thì bỏ |
| `authors` | `list[str]` | Không | Danh sách tác giả | Chuẩn hóa họ tên, loại bỏ phần tử rỗng và trùng lặp; mặc định `[]` |
| `categories` | `list[str]` | Không | Chủ đề / Lĩnh vực khoa học | Chuẩn hóa, bỏ trùng giữ nguyên thứ tự xuất hiện; mặc định `[]` |
| `primary_category` | `str` | Không | Lĩnh vực chính | Lấy phần tử đầu tiên của `categories`; nếu không có thì để chuỗi rỗng `""` |
| `published` | `str (YYYY-MM-DD)` | Có | Ngày xuất bản | Phân tích từ chuỗi date-parts của Crossref; điền mặc định ngày 1 nếu thiếu tháng/ngày; loại bản ghi nếu không parse được |
| `updated` | `str (YYYY-MM-DD)` | Không | Ngày cập nhật | Điền bằng `published` nếu trường này bị thiếu |
| `age_days` | `int` | Có | Số ngày tính từ ngày xuất bản đến `run_date` | `(run_date - published).days` theo chuẩn UTC; nhỏ nhất là 0 nếu bài ghi ngày tương lai |
| `authors_joined` | `str` | Không | Chuỗi tác giả nối bằng dấu phẩy | `", ".join(authors)` |
| `categories_joined`| `str` | Không | Chuỗi chuyên mục nối bằng phẩy | `", ".join(categories)` |
| `summary_chars` | `int` | Không | Độ dài ký tự của abstract | `len(summary)` |
| `text_for_embedding`| `str` | Có | Văn bản hợp nhất phục vụ embedding | Cấu trúc 5 phần: Title, Authors, Categories, Published, Summary |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Bỏ tag JATS XML (`<jats:p>`, `<jats:title>`), unescape entity | Validity / Cleanliness | 24 / 24 | So sánh text trước và sau clean; kiểm tra `papers_clean.json` không còn tag XML |
| Bỏ nhãn "Abstract" ở đầu summary | Consistency / Accuracy | 6 / 24 | Kiểm tra biểu thức chính quy `_ABSTRACT_LABEL_RE` trên các trường abstract |
| Khử khoảng trắng kép và ngắt dòng dư thừa | Validity | 1 / 24 (`...3671820`) | Abstract được chuẩn hóa thành một đoạn văn duy nhất, liền mạch |
| Parse ngày chuẩn ISO YYYY-MM-DD | Uniformity / Validity | 24 / 24 | Cột `published` và `updated` đồng nhất định dạng, không còn kiểu date-parts |
| Deduplicate theo `paper_id` | Uniqueness | 0 (tập thô không trùng) | Giữ bản ghi có `updated` mới nhất; kiểm tra `df["paper_id"].nunique() == len(df)` |
| Sắp xếp cố định (Newest First) | Determinism | 24 / 24 | Sắp xếp theo `published` giảm dần, `paper_id` tăng dần; bảo đảm tính tái lập |

**Giải thích cách tạo `text_for_embedding`, document ID và `age_days`:**
- **Document ID (`paper_id`):** Sử dụng trực tiếp mã DOI do Crossref cấp, được strip khoảng trắng và chuyển toàn bộ sang chữ thường (ví dụ: `10.1145/3637528.3671812`). Định danh này có tính toàn cầu, không thay đổi qua các lần crawl và đóng vai trò làm khóa chính.
- **`age_days`:** Được tính bằng hiệu số giữa ngày thực thi pipeline (`run_date` chuẩn UTC) và ngày xuất bản (`published` chuẩn UTC). Nếu bài báo có ngày xuất bản trong tương lai do lỗi metadata từ nhà xuất bản, `age_days` được chặn dưới bằng 0 (`clip(lower=0)`).
- **`text_for_embedding`:** Được cấu trúc chặt chẽ thành 5 dòng rõ ràng:
  ```text
  Title: <title>
  Authors: <authors_joined>
  Categories: <categories_joined>
  Published: <published>
  Summary: <summary>
  ```
  Cách tổ chức này cung cấp đầy đủ thông tin ngữ nghĩa (semantic context) để mô hình MiniLM nhúng chính xác các khía cạnh về nội dung nghiên cứu, tác giả và thời gian.

---

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi | `10` câu hỏi benchmark |
| Các `question_type` | `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu) |
| Ground-truth document ID | Trích xuất trực tiếp từ trường `paper_id` của bài báo được chọn làm nguồn sinh câu hỏi |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) |
| Vector store/collection | ChromaDB Persistent Client (`data/chroma/`), không gian khoảng cách cosine (`hnsw:space = cosine`) |
| Retrieval `top_k` | `4` tài liệu ngữ cảnh |
| LLM provider/model | `gemini` / `gemini-2.5-flash` (kèm fallback heuristic Token F1 khi bị rate limit) |
| Test set dùng chung cho ba trạng thái | Lưu trữ cố định tại file `data/eval/test_set.json` |

**Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:**
Trong phương pháp luận thực nghiệm khoa học, nguyên tắc cơ bản là **cô lập biến số (Isolation of Variables)**. Ở đây, biến số độc lập duy nhất đang được khảo sát là **chất lượng dữ liệu (Data Quality)**. Toàn bộ các tham số còn lại (bộ câu hỏi kiểm thử, ground truth, tiêu chí chấm điểm, tham số retrieval Top-K, mô hình vector hóa) bắt buộc phải giữ cố định 100%. Nếu thay đổi test set giữa các trạng thái, sự thay đổi của các chỉ số đo lường sẽ không còn phản ánh trung thực tác động của dữ liệu bẩn và năng lực phục hồi của hệ thống.

---

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| ------------------------ | -------------------------------------- | :---: | ---------- |
| Raw response/records | `data/raw/crossref_response.json`<br>`data/raw/crossref_records.json` | **Có** | Lưu trữ đầy đủ 24 bài thô phục vụ data lineage |
| Cleaned dataset | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` | **Có** | 24 dòng sạch, 16 cột chuẩn theo Data Contract |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`<br>`data/chroma/` | **Có** | Collection `papers-baseline` index đủ 24 docs |
| Evaluation set | `data/eval/test_set.json` | **Có** | 10 câu hỏi bao quát đủ 4 dạng nghiệp vụ |
| Baseline metrics | `data/results/baseline_metrics.json` | **Có** | Ghi nhận Hit Rate = 1.0, Token F1 = 1.0 |
| Quality/freshness | `data/quality/baseline_quality_report.json`<br>`data/quality/freshness_report.json` | **Có** | GX 1.x PASS, Freshness SLA FRESH |
| Baseline report | `data/reports/phase1_report.md` | **Có** | Báo cáo Markdown tổng kết Pha 1 hoàn chỉnh |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | **1.0000** | 10/10 câu hỏi đều truy xuất chính xác tài liệu chứa câu trả lời trong Top-4 kết quả. |
| `mean_token_f1` | **1.0000** | Câu trả lời của hệ thống khớp hoàn hảo 100% với ground truth tham chiếu. |
| `judge_accuracy` | **1.0000** | 10/10 câu trả lời được LLM Judge thẩm định là hoàn toàn chính xác về mặt nội dung. |
| `mean_judge_score` | **5.00 / 5** | Điểm số chất lượng tối đa theo thang điểm chuẩn của hệ thống đánh giá. |
| Ragas, nếu có | `Skipped` | Bỏ qua để tối ưu thời gian chạy (chỉ kích hoạt khi bật cờ `RUN_RAGAS=1`). |

---

## 8. Data quality và freshness

### Quality checks

Cấu hình Ephemeral Data Context theo chuẩn Great Expectations 1.x:

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `ExpectTableRowCountToBeBetween` | Completeness | [20, 30] dòng | **PASS** (quan sát: 24 dòng) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`paper_id`) | Completeness | 0 giá trị null | **PASS** (0/24 unexpected) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` (`paper_id`) | Uniqueness | 100% unique | **PASS** (0/24 trùng lặp) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` (`paper_id`) | Validity | Độ dài [5, 100] ký tự | **PASS** (0/24 vi phạm) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`title`) | Completeness | 0 giá trị null | **PASS** (0/24 unexpected) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` (`title`) | Validity | Tối thiểu 8 ký tự | **PASS** (0/24 vi phạm) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`summary`) | Completeness | 0 giá trị null | **PASS** (0/24 unexpected) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` (`summary`) | Validity | Tối thiểu 20 ký tự | **PASS** (0/24 vi phạm) | `baseline_quality_report.json` |

### Freshness

| Thuộc tính | Giá trị |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Tập dữ liệu sạch `data/clean/papers_clean.json` |
| Timestamp mới nhất | `2026-07-22` (bài báo `10.1145/3637528.3671812`) |
| Timestamp cũ nhất | `2026-03-28` (bài báo `10.1145/3637528.3671805`) |
| Ngưỡng freshness | Cảnh báo vi phạm nếu tỷ lệ bài có `age_days > 180` vượt quá **25%** |
| Trạng thái baseline | **FRESH** |
| Lý do | Chỉ có duy nhất 1 bài quá hạn 180 ngày (`10.1145/3637528.3671805`, xuất bản ngày 2026-03-28, `age_days = 182`), chiếm tỷ lệ **4.17%** (nhỏ hơn rất nhiều so với ngưỡng trần 25%). |

---

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| **Drop latest records** | Cắt bỏ 5 bài báo mới nhất (~20.8% dữ liệu) | 5 bài (`...812`, `...808`, `...804`, `...807`, `...802`) | Cảnh báo giảm số lượng dòng (vi phạm nếu vượt ngưỡng) | Mất hoàn toàn ngữ cảnh câu `q01`, `q02`; `retrieval_hit_rate` rơi thẳng từ 1.0 về 0.80 | Tải lại toàn bộ bản ghi gốc từ `crossref_records.json` |
| **Blank summary** | Xóa rỗng chuỗi tóm tắt (`summary = ""`) | 2 bài (`...822`, `...820`) | Vi phạm GX `ExpectColumnValueLengthsToBeBetween` trên cột `summary` | QA Agent không trích xuất được tóm tắt cho câu `q05`, Token F1 rơi về 0 | Làm sạch lại từ raw records, tái tạo trường summary chuẩn |
| **Inject noise** | Chèn chuỗi byte rác `[CORRUPTED_STREAM_#$!@%*&_0xDEADBEEF]` | 2 bài (`...821`, `...818`) | Tăng đột biến độ dài ký tự bất thường | Phá vỡ vector embedding, gây sai lệch điểm tương đồng cosine | Lọc bỏ và tái nạp abstract sạch từ raw records |
| **Truncate title** | Cắt ngắn tiêu đề xuống < 8 ký tự (ví dụ: `"Advan"`) | 2 bài (`...823`, `...819`) | Vi phạm GX `ExpectColumnValueLengthsToBeBetween` trên cột `title` (3 lỗi) | Phá vỡ cơ chế exact title lookup của Agent, giảm độ chính xác truy xuất | Khôi phục tiêu đề gốc đầy đủ từ raw snapshot |
| **Stale date** | Lùi ngày xuất bản về quá khứ 500 ngày (`published - 500d`) | 9 bài báo | Vi phạm Freshness SLA (tỷ lệ bài `age_days > 180` tăng vọt lên 57.1%) | Trạng thái Freshness chuyển sang STALE; câu hỏi về thời gian (`q03`) trả về mốc sai | Tính toán lại ngày chuẩn từ trường `published` trong raw records |
| **Duplicate rows** | Nhân bản 2 dòng dữ liệu và gắn vào cuối bảng | 2 bài báo | Vi phạm GX `ExpectColumnValuesToBeUnique` trên cột `paper_id` (4 lỗi) | Gây ô nhiễm vector store, xuất hiện bản ghi trùng lặp trong Top-k retrieval | Chạy thuật toán deduplicate theo `paper_id` trong hàm clean thuần |

**Corruption log:**
- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: **Có đầy đủ**
- Nhận xét: Log ghi nhận tường minh cả 6 dạng lỗi, chi tiết danh sách `paper_id` của từng bài bị tác động, các tham số tiêm lỗi và tổng kết số lượng dòng trước/sau khi làm bẩn.

**Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:**
Cơ chế Repair của nhóm tuân thủ nguyên tắc **Idempotent Self-Healing**: Tuyệt đối không thực hiện sửa chữa chắp vá (in-place patching) trên tập dữ liệu đã bị biến dạng. Lý do là vì in-place patching không thể khôi phục lại các bản ghi đã bị xóa mất (`drop_latest_records`), đồng thời dễ bỏ sót các lỗi tiềm ẩn. Thay vào đó, pipeline phục hồi luôn kích hoạt việc đọc lại từ bản lưu trữ thô nguyên bản (`data/raw/crossref_records.json`) — đây là bản snapshot bất biến (immutable data lineage). Sau đó, pipeline áp dụng lại hàm làm sạch thuần túy `build_clean_dataframe()` với thời điểm chạy hiện tại. Nhờ tính chất hàm thuần (cùng đầu vào cho ra cùng đầu ra), dữ liệu sạch được khôi phục 100% một cách khách quan, minh bạch và có thể tái lập ở bất kỳ thời điểm nào.

---

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi (Repair) | Nhận xét |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate` | **1.0000** | **0.8000** | **1.0000** | `-0.2000` | `+0.2000` | Giảm 20% do 5 bài mới bị drop mất; phục hồi hoàn hảo 100% sau repair |
| `mean_token_f1` | **1.0000** | **0.6741** | **1.0000** | `-0.3259` | `+0.3259` | Sụt giảm nghiêm trọng 32.6% do tóm tắt bị rỗng và nhiễu; lấy lại phong độ tối đa |
| `judge_accuracy` | **1.0000** | **0.7000** | **1.0000** | `-0.3000` | `+0.3000` | Tỷ lệ thẩm định đúng của LLM Judge giảm về 70% và phục hồi lại 100% |
| `mean_judge_score` | **5.00** | **3.80** | **5.00** | `-1.20` | `+1.20` | Điểm chất lượng câu trả lời giảm 1.2 điểm trên thang 5; phục hồi trọn vẹn 5.0 |
| Data Quality Gate | **PASS** | **FAIL** | **PASS** | `FAIL (vi phạm 3 checks)` | `Khôi phục PASS 100%` | GX 1.x bắt chính xác lỗi trùng `paper_id` và vi phạm độ dài `title`/`summary` |
| Freshness SLA | **FRESH (4.2%)**| **STALE (57.1%)**| **FRESH (4.2%)**| `Vi phạm SLA (> 25%)` | `Khôi phục FRESH` | Tỷ lệ bài quá hạn vọt lên 57.1% gây báo động đỏ; repair đưa về 4.17% an toàn |

**Hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:**

1. **Chuỗi suy thoái (Corruption $\rightarrow$ Observability Signal $\rightarrow$ Performance Drop):**
   Việc tiêm 6 kịch bản lỗi vào DataFrame dẫn đến việc Data Quality Gate lập tức chuyển sang trạng thái **FAIL** (phát hiện 4 bản ghi trùng `paper_id`, 3 tiêu đề và 2 tóm tắt vi phạm độ dài trong `corrupted_quality_report.json`), đồng thời Freshness SLA chuyển sang **STALE** (12/21 bài quá hạn trong `corrupted_freshness_report.json`). Dữ liệu lỗi này khi đi vào vector store đã trực tiếp làm sụp đổ hiệu năng của RAG Agent: `retrieval_hit_rate` rơi xuống `0.8000` và `mean_token_f1` rơi xuống `0.6741` (được chứng thực trong `corrupted_metrics.json` và `corrupted_answers.json`).
2. **Chuỗi phục hồi (Idempotent Repair $\rightarrow$ Observability Recovery $\rightarrow$ Performance Restoration):**
   Hành động kích hoạt Idempotent Repair tái tạo dữ liệu từ bản raw snapshot bất biến `crossref_records.json` đã loại bỏ hoàn toàn các bản ghi rác và phục hồi đầy đủ 24 bài báo sạch. Điều này khiến Data Quality Gate trở lại **PASS** (100% vượt qua cả 8 tiêu chí kiểm định trong `repaired_quality_report.json`) và Freshness SLA trở lại **FRESH** (chỉ còn 4.17% bài quá hạn). Kết quả là hiệu năng của AI Agent được khôi phục tuyệt đối: `retrieval_hit_rate` đạt lại `1.0000` và `mean_token_f1` đạt lại `1.0000` (chứng thực trong `repaired_metrics.json`).

---

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy script kiểm thử entrypoint `python script/run_phase1.py` hoặc chạy trực tiếp `python .\src\pipelines\phase1.py`, chương trình dừng đột ngột và báo lỗi:
  ```text
  ModuleNotFoundError: No module named 'core'
  ModuleNotFoundError: No module named 'pipelines'
  ```
- **Nguyên nhân:** Python runtime khi thực thi script sẽ mặc định gán `sys.path[0]` là thư mục chứa chính file script đó (`script\` hoặc `src\pipelines\`). Do dự án được cấu trúc theo chuẩn `src layout` (`src/core`, `src/ingestion`, `src/retrieval`, v.v.), Python không thể tự động tìm thấy các package đồng cấp trong `src/` nếu gói phần mềm chưa được cài đặt vào môi trường ảo `.venv` ở chế độ editable.
- **Cách xử lý:**
  1. Thực hiện cài đặt dự án ở chế độ editable: `python -m pip install -e .` để liên kết thư mục `src/` vào site-packages của `.venv` theo đúng khai báo trong `pyproject.toml`.
  2. Bổ sung đoạn mã phòng vệ tự động cấu hình `sys.path` ngay tại phần đầu của các file pipeline (`phase1.py` và `corruption_flow.py`):
     ```python
     import sys
     from pathlib import Path

     _SRC_DIR = str(Path(__file__).resolve().parents[1])
     if _SRC_DIR not in sys.path:
         sys.path.insert(0, _SRC_DIR)
     ```
- **Cách xác minh:** Chạy lại cả hai script `python script/run_phase1.py` và `python script/run_corruption_flow.py`, toàn bộ các lệnh import module `core`, `ingestion`, `retrieval`, `observability`, `evaluation` đều hoạt động trơn tru 100%.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Cơ chế Repair hiện tại vẫn cần kích hoạt qua pipeline flow | Khi phát hiện dữ liệu bẩn, hệ thống vẫn phải chờ lệnh điều phối chạy quy trình phục hồi | Triển khai **Automated Circuit Breaker**: Tự động ngắt kết nối nạp dữ liệu vào ChromaDB chính và tự kích hoạt luồng Repair ngầm khi GX trả về `success = False`. Đo lường bằng thời gian phục hồi MTTR < 5s. |
| Báo cáo Observability hiện xuất dưới dạng file JSON và Markdown tĩnh | Người vận hành hệ thống phải mở file thủ công để theo dõi tình trạng dữ liệu | Xây dựng **Interactive Real-Time Observability Dashboard** bằng Streamlit/Gradio hiển thị trực quan biểu đồ phân bố `age_days`, tỷ lệ vi phạm SLA và lịch sử cảnh báo chất lượng dữ liệu. |
| Bộ benchmark kiểm thử hiện cố định ở 10 câu hỏi tĩnh | Chưa đánh giá hết được các trường hợp góc (edge cases) khi kho tài liệu tăng lên hàng nghìn bài | Ứng dụng thư viện Ragas và Synthetic Data Generation để tự động sinh hàng trăm câu hỏi đa dạng theo ngữ cảnh mới sau mỗi lần crawl dữ liệu. |

---

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác (`ColdBrew`, repository nhánh `main`).
- [x] Phân công khớp với module, artifact và kết quả thực tế của 3 thành viên.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp (`python script/run_phase1.py` & `python script/run_corruption_flow.py`).
- [x] Baseline, corrupted và repaired dùng chung 100% cùng một evaluation set (`data/eval/test_set.json`).
- [x] Bảng metrics khớp chính xác tuyệt đối với các file trong `data/results/` (`baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`).
- [x] Quality/freshness conclusions khớp hoàn toàn với các báo cáo trong `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact có thể truy cập được trong cấu trúc thư mục của repository.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng trong `report/` theo mẫu quy ước.
- [x] Tuyệt đối không có `.env`, API key, token hoặc secret trong source code, báo cáo hay log.
