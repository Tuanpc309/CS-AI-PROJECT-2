# GridLogic – Griductive Solver (CSC14003 · Đồ án 2)

Trò chơi suy luận lưới “không đoán” có giao diện web và Logic Agent dùng **logic mệnh đề → CNF → DPLL tự cài đặt**.
Agent chỉ lật một thẻ khi trạng thái của nhân vật là **hệ quả logic** của thông tin công khai hiện tại.

## Yêu cầu

- Python **3.10+** (đã kiểm thử với Python 3.12, Windows 11).
- Không cần thư viện ngoài: chương trình chỉ dùng thư viện chuẩn (`requirements.txt` để trống có chủ đích).
- Trình duyệt bất kỳ (Edge/Chrome/Firefox) để mở giao diện.

## Chạy nhanh

```bash
cd Source
python main.py                 # mở GUI tại http://127.0.0.1:8000 (tự mở trình duyệt)
```

Tùy chọn: `python main.py gui --port 8080 --no-browser` (đổi cổng, không tự mở trình duyệt), `--host 0.0.0.0` để truy cập từ máy khác.

### Cách chơi trên GUI

| Thao tác | Ý nghĩa |
| --- | --- |
| Bấm thẻ **úp** → **CRIMINAL** / **INNOCENT** (hoặc phím `C` / `I`) | Gửi phán quyết. Được chấp nhận nếu chứng minh được từ dữ kiện công khai; ngược lại báo `NOT_PROVABLE` (chưa suy ra được) hoặc `CONTRADICTED` (trạng thái đối lập đã được chứng minh) và bàn chơi giữ nguyên. |
| Bấm thẻ **đã mở** | Tô sáng các ô mà manh mối đếm (vàng) và người được nêu tên (viền tím); hiện cấu trúc JSON + số mệnh đề CNF. |
| **Load** / *Load puzzle from file…* | Nạp câu đố có sẵn hoặc tệp JSON của bạn. |
| **Restart** | Về bộ thẻ mở ban đầu. |
| **Hint** (`H`) | Chỉ ra manh mối liên quan và nhân vật chứng minh được; bấm lần nữa để xem phán quyết. Không đọc đáp án ẩn. |
| **Agent step** / **Auto Solve** | Logic Agent thực hiện một bước / chạy đến khi SOLVED, STUCK hoặc INCONSISTENT (có thể Stop). |
| **Check uniqueness** | Kiểm tra số nghiệm của toàn bộ manh mối (+ thẻ mở sẵn) và khả năng giải không cần đoán. |
| **Export trace** | Tải nhật ký suy luận (JSON). |
| *Solver settings* | Chế độ agent (step/wave), cách mã hóa đếm (auto/direct/seqcounter/totalizer), heuristic DPLL. |

## Dòng lệnh

```bash
python main.py solve puzzles/4x4/classic-4x4-a.json --verbose      # in nhật ký + mọi truy vấn SAT
python main.py solve puzzles/5x5/stress-5x5-a.json --mode wave --trace trace.json
python main.py check puzzles/special/special-stuck-3x3.json          # manh mối đúng? duy nhất? giải tuần tự được?
python main.py encode puzzles/tutorial/tutorial-3x3.json --all       # in CNF của từng manh mối
python main.py encode puzzles/tutorial/tutorial-3x3.json --dimacs kb.cnf
python main.py generate --size 4 --seed 7 --ext 0.3 --out my.json    # sinh câu đố mới
python main.py experiments                                           # chạy thực nghiệm -> results/
python -m unittest discover -s tests                                 # kiểm thử
python tools/build_puzzles.py                                        # sinh lại bộ câu đố (seed cố định)
```

Các tùy chọn bộ giải dùng chung: `--cardinality {auto,direct,seqcounter,totalizer}`, `--heuristic {first,occurrence}`,
`--pure-literal`; với `solve`: `--no-witnesses`, `--time-limit GIÂY`.

## Cấu trúc thư mục

```
Source/
├── main.py                 điểm vào (GUI + CLI)
├── gridlogic/              thuật toán (không phụ thuộc thư viện ngoài)
│   ├── board.py            tọa độ ô, Status, láng giềng
│   ├── regions.py          vùng: row, col, neighbors, cells + mở rộng
│   ├── clues.py            manh mối: kiểm tra, bộ đánh giá trực tiếp, công thức, câu chữ, tô sáng
│   ├── logic.py            cây công thức mệnh đề
│   ├── cnf.py              kho biến (chính/phụ), CNF, DIMACS
│   ├── encoder.py          công thức -> CNF (tổ hợp, sequential counter, totalizer, XOR chain, Tseitin)
│   ├── dpll.py             DPLL: lan truyền 2 literal canh, quay lui, bộ đếm, giả định, deadline
│   ├── knowledge.py        KB_t, truy vấn hệ quả, giải thích cho Hint
│   ├── state.py            PublicState – dữ liệu duy nhất agent được thấy
│   ├── puzzle.py           câu đố đầy đủ (có đáp án) + JSON
│   ├── engine.py           Game Engine (trọng tài, lật thẻ)
│   ├── agent.py            Logic Agent (vòng lặp suy luận, nhật ký, Hint)
│   ├── uniqueness.py       kiểm tra duy nhất, kiểm định câu đố
│   ├── generator.py        sinh câu đố không cần đoán
│   └── experiments.py      thực nghiệm
├── webapp/                 server HTTP (thư viện chuẩn) + static/ (HTML/CSS/JS)
├── puzzles/                tutorial/, 3x3/, 4x4/, 5x5/, special/ (ca kẹt, nhiều nghiệm, mâu thuẫn)
├── results/                experiments.csv / .json / .md (số liệu dùng trong báo cáo)
├── tests/                  unittest
└── tools/build_puzzles.py  dựng lại bộ câu đố
```

## Ngôn ngữ manh mối

Sáu mẫu bắt buộc: `FACT`, `SAME`, `DIFFERENT`, `EXACTLY`, `AT_LEAST`, `AT_MOST` (`NO` = `EXACTLY 0`), trên vùng
`row` / `col` / `neighbors` / `cells`. Manh mối đếm có thể đếm người vô tội bằng `"status": "INNOCENT"`.

Mở rộng: `PARITY` (chẵn/lẻ), `COMPARE` (so sánh số đếm hai vùng), `CONNECTED` (liền nhau trên một đoạn thẳng),
manh mối kép `ALL` / `ANY` / `NOT` / `IMPLIES`, và vùng nâng cao `common_neighbors`, `intersection`, `union`, `edge`,
`corners`, `all`, `direction` (left/right/above/below), `between`.

Ví dụ một nhân vật trong tệp câu đố:

```json
{"cell": "A1", "name": "Alice", "profession": "Baker", "status": "INNOCENT",
 "clue": {"type": "EXACTLY", "k": 2, "region": {"kind": "neighbors", "of": "Alice"}}}
```

Xem `puzzles/tutorial/tutorial-3x3.json` để có ví dụ đầy đủ (gồm `PARITY`, `COMPARE`, `CONNECTED`, `IMPLIES`).

## Kiến trúc tóm tắt

- **Game Engine** (`engine.py`) giữ đáp án ẩn và manh mối của thẻ úp; khi nhận phán quyết nó dựng `KB_t` **chỉ từ trạng thái
  công khai**, hỏi DPLL, rồi chấp nhận / từ chối (`NOT_PROVABLE`, `CONTRADICTED`).
- **Logic Agent** (`agent.py`) chỉ nhận `PublicState`: dựng `KB_t = CNF(manh mối đã mở) ∧ trạng thái đã biết`, kiểm tra
  `KB_t ∧ ¬C_i` / `KB_t ∧ C_i` cho mọi ô chưa biết, nộp phán quyết bị ép đầu tiên theo thứ tự hàng-rồi-cột và lặp lại.
- Web server chỉ gửi dữ liệu công khai về trình duyệt (được kiểm tra trong `tests/test_server.py`).
