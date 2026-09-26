# Data Contract — Raw & Clean Schema

> Owner: Thành viên 1 (Data ingestion & cleaning) · Code: `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`
> Mọi module phía sau (testset, quality, index, corruption, repair) dựa vào contract này. Muốn đổi tên cột/kiểu dữ liệu phải báo cả nhóm trước.

## 1. Luồng dữ liệu

```text
Crossref API /works  ──(REFRESH_SOURCE=1)──┐
                                           ├─> data/raw/crossref_response.json   (payload gốc, lineage)
snapshot local (mặc định / fallback) ──────┘            │ parse_crossref_payload()
                                                        v
                                        data/raw/crossref_records.json   (list[PaperRecord])
                                                        │ load_raw_records() + build_clean_dataframe(records, run_date)
                                                        v
                                        DataFrame sạch -> phase1 ghi data/clean/papers_clean.{csv,json}
```

| Hàm | Input | Output |
|---|---|---|
| `fetch_source_records(settings)` | settings (`source_query`, `source_filter`, `max_results`, `refresh_source`) | `list[PaperRecord]`; ghi 2 file raw |
| `parse_crossref_payload(payload)` | dict JSON Crossref | `list[PaperRecord]` |
| `load_raw_records(path)` | đường dẫn `crossref_records.json` | `list[PaperRecord]` |
| `build_clean_dataframe(records, run_date)` | records + thời điểm chạy (tz-aware hoặc naive = UTC) | `pd.DataFrame` theo clean schema |

**Chế độ lấy dữ liệu**
- Mặc định (`REFRESH_SOURCE` không set) dùng snapshot `data/raw/crossref_response.json`. Cách này chạy lại được và luôn ra 24 bài.
- `REFRESH_SOURCE=1` thì gọi `https://api.crossref.org/works`. Gặp lỗi 429/500/502/503/504 hoặc lỗi mạng thì retry tối đa 4 lần, chờ theo `Retry-After` hoặc backoff 2s, 4s, 8s.
- Gọi API thất bại thì fallback về snapshot. Snapshot chỉ bị ghi đè khi gọi API thành công.
- Lưu ý: Crossref là nguồn sống. Chạy lại với `REFRESH_SOURCE=1` có thể đổi corpus, nên cần tạo lại test set (`REFRESH_TEST_SET=1`).

## 2. Raw schema — `PaperRecord` (`crossref_records.json`)

| Trường | Kiểu | Nguồn Crossref | Quy tắc / trường thiếu |
|---|---|---|---|
| `paper_id` | str | `DOI` | Bỏ khoảng trắng đầu/cuối, chuyển chữ thường. Thiếu thì bỏ record |
| `title` | str | `title[0]` | Bỏ tag, decode entity, gom khoảng trắng. Rỗng thì bỏ record |
| `summary` | str | `abstract` | Bỏ tag JATS (kể cả `<jats:title>`), bỏ nhãn "Abstract" ở đầu, gom khoảng trắng. Rỗng thì bỏ record |
| `authors` | list[str] | `author[].given + family` hoặc `name` (tổ chức) | Bỏ tên rỗng, bỏ trùng. Thiếu thì `[]` |
| `categories` | list[str] | `subject` | Bỏ trùng (không phân biệt hoa thường), giữ thứ tự. Thiếu thì `[]` |
| `primary_category` | str | `subject[0]` | `""` nếu không có subject |
| `published` | str `YYYY-MM-DD` | `published` → `published-online` → `published-print` → `issued` → `created` | `date-parts` thiếu tháng/ngày thì điền 1. Không có ngày thì bỏ record |
| `updated` | str `YYYY-MM-DD` | `created` | Thiếu thì dùng `published` |
| `abs_url` | str | `URL` | Thiếu thì `https://doi.org/<paper_id>` |
| `pdf_url` | str | `link[]` có content-type pdf | Thiếu thì dùng `abs_url` |
| `comment` | str | — | `"Crossref record <paper_id>"` |

DOI trùng trong cùng payload thì giữ bản xuất hiện đầu tiên. `load_raw_records` chịu được JSON thiếu field (điền `""`/`[]`) và bỏ qua field thừa, để luồng repair không bị crash.

## 3. Clean schema — output `build_clean_dataframe`

Cột theo đúng thứ tự:

| Cột | Kiểu | Mô tả |
|---|---|---|
| `paper_id` | str | Document ID ổn định (DOI chữ thường), **unique** |
| `title` | str | Tiêu đề đã chuẩn hóa |
| `summary` | str | Abstract đã chuẩn hóa |
| `authors` | list[str] | |
| `categories` | list[str] | |
| `primary_category` | str | Rỗng thì lấy `categories[0]` |
| `published` | str `YYYY-MM-DD` | **Là chuỗi**, vì Chroma metadata chỉ nhận scalar và câu hỏi `date` so khớp chuỗi này |
| `updated` | str `YYYY-MM-DD` | |
| `age_days` | int | `(run_date − published).days` tính theo ngày UTC, nhỏ nhất là 0 (bài ghi ngày tương lai) |
| `authors_joined` | str | `", ".join(authors)` |
| `categories_joined` | str | `", ".join(categories)` |
| `summary_chars` | int | `len(summary)` |
| `abs_url`, `pdf_url`, `comment` | str | |
| `text_for_embedding` | str | 5 phần, xem bên dưới |

```text
Title: <title>
Authors: <authors_joined>
Categories: <categories_joined>
Published: <published>
Summary: <summary>
```

## 4. Cleaning rules

1. **Chuẩn hóa text:** bỏ JATS/HTML tag, `html.unescape`, gom mọi khoảng trắng/xuống dòng thành 1 space. Áp dụng lại ở bước clean, dù raw đã chuẩn hóa, vì records có thể đến từ file bị sửa tay hoặc bị corrupt.
2. **Chuẩn hóa `paper_id`:** strip và chuyển chữ thường (DOI không phân biệt hoa thường).
3. **List fields:** bỏ phần tử rỗng, bỏ trùng không phân biệt hoa thường, giữ thứ tự.
4. **Ngày:** parse `published`/`updated`. Dòng có `published` không parse được thì bị loại. `updated` lỗi thì lấy `published`.
5. **Lọc dòng xấu:** loại dòng có `paper_id`, `title` hoặc `summary` rỗng.
6. **Deduplicate theo `paper_id`:** giữ bản có `updated` mới nhất; bằng nhau thì giữ bản đứng trước.
7. **Sắp xếp cố định:** `published` giảm dần, sau đó `paper_id` tăng dần; `reset_index`.

Cleaning **không** lọc theo độ dài summary hay độ tuổi bài. Hai điều này do Quality Gate (`quality.py`) và Freshness SLA báo cáo, để lỗi được phát hiện thay vì bị giấu đi.

## 5. Kết quả trên snapshot hiện tại

Chạy với `run_date` = 2026-09-26:

| Chỉ số | Giá trị |
|---|---|
| Items trong response | 24 |
| Raw records | 24 (khớp 100% với `crossref_records.json` gốc) |
| Clean rows | 24, `paper_id` unique |
| Lỗi đã sửa | 1 abstract có khoảng trắng kép (`10.1145/3637528.3671820`); 24/24 abstract có tag `<jats:p>` đã bị bỏ |
| Khoảng `published` | 2026-03-28 → 2026-07-22 |
| `age_days > 180` | 1/24 (4.2%), dưới ngưỡng 25%, nên fresh |

Đã thử gọi Crossref API thật: 24 items, parse 24 bài, clean 24 dòng. Dữ liệu thật có nhiều abstract bắt đầu bằng chữ "Abstract", đã được rule 1 xử lý. Snapshot không bị ghi đè.

## 6. Repair contract

Repair **luôn** chạy lại `load_raw_records(settings.paths.raw_records_json)` + `build_clean_dataframe(...)` từ raw, không sửa trên dữ liệu đã bị corrupt. Hai hàm này là hàm thuần (cùng input thì cùng output, trừ `age_days` phụ thuộc `run_date`), nên repair idempotent. Để so sánh baseline và repaired được khớp, dùng cùng `run_date` trong một lần chạy.

## 7. Lệnh xác minh

```bash
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
```

Trên Windows nên đặt `PYTHONIOENCODING=utf-8`, nếu không in tiếng Việt ra console sẽ lỗi `UnicodeEncodeError`.
