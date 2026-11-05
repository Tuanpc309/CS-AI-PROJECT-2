# CSC14003 · Đồ án 2 · Griductive Solver

Kế hoạch triển khai và checklist nghiệm thu cho nhóm 5 người. Nguồn yêu cầu là [đề Đồ án 2](<AI - Project 2.pdf>). Các ô dưới đây dùng để theo dõi công việc và chỉ được đánh dấu sau khi đã kiểm tra.

Nhóm sẽ xây dựng trò chơi Griductive có giao diện web và bộ giải tự động bằng Python. Quy tắc xuyên suốt là **chỉ lật thẻ khi trạng thái nhân vật suy ra được từ dữ kiện công khai ở bước hiện tại**. Game Engine quản lý đáp án ẩn. Logic Agent dùng manh mối đã mở và trạng thái đã biết để chứng minh phán quyết.

## 1. Thang điểm và người phụ trách

*TV: THÀNH VIÊN

| Mục trong đề | Điểm | Phụ trách | Minh chứng cần có |
| --- | ---: | --- | --- |
| §4.1 Trò chơi có GUI | 10 | TV5 giao diện, TV1 Game Engine, TV4 tích hợp suy luận | Chơi tay, lật thẻ theo luật, highlight, bốn nút điều khiển và ranh giới dữ liệu ẩn. |
| §4.2 Biểu diễn logic và mã hóa CNF | 10 | TV2 | Encoder tự sinh CNF, hỗ trợ sáu mẫu cơ bản và hai mở rộng, có bộ đánh giá trực tiếp và số liệu. |
| §4.3 Bộ giải DPLL | 10 | TV3 | Trả `SAT` kèm phép gán đầy đủ hoặc `UNSAT`, có bộ đếm và thời gian chạy. |
| §4.4 Logic Agent | 20 | TV4 | Auto Solve suy luận từng bước, nhật ký và phép kiểm tra tính duy nhất riêng. |
| §4.5 Thực nghiệm | 10 | TV3, TV1 chuẩn bị câu đố | Bảng số liệu cho nhiều câu đố 3×3 và 4×4, gồm các ca lỗi hoặc quá thời gian nếu có. |
| §4.6 Báo cáo PDF | 30 | TV1 tổng hợp, cả nhóm viết phần mình | Đủ phân công, mô hình hóa, dẫn xuất CNF, thuật toán, thực nghiệm, tham khảo và phụ lục. |
| §4.7 Video demo | 10 | TV5, TV1 và TV4 hỗ trợ trình diễn | Khoảng 5–10 phút, gồm GUI (5 điểm) và chức năng (5 điểm), có liên kết Google Drive xem được. |
| **Tổng** | **100** | | |

### Phân công 5 thành viên

| Thành viên | Công việc chính | Bàn giao và phần báo cáo |
| --- | --- | --- |
| **TV1 · [Họ tên / MSSV]** | Game Engine, định dạng dữ liệu, câu đố mẫu và điều phối tích hợp | Dữ liệu công khai cho TV4/TV5, bộ câu đố cho TV3. Viết mô hình bài toán và quy trình mở thẻ. Ghép PDF, cùng TV5 kiểm tra gói nộp. |
| **TV2 · [Họ tên / MSSV]** | Ánh xạ biến, vùng, encoder, bộ đánh giá trực tiếp và hai mở rộng | Giao CNF và thống kê cho TV3/TV4, bộ phân giải vùng cho TV5. Viết ngữ nghĩa và hai dẫn xuất CNF. |
| **TV3 · [Họ tên / MSSV]** | DPLL, bộ đếm, công cụ chạy thực nghiệm và tổng hợp số liệu | Giao giao diện gọi SAT cho TV4. Viết phần DPLL, phương pháp đo, bảng kết quả và phân tích. |
| **TV4 · [Họ tên / MSSV]** | Logic Agent, xử lý phán quyết, Hint, Auto Solve, nhật ký và kiểm tra nghiệm duy nhất | Giao luồng suy luận cho TV1/TV5 và nhật ký mẫu cho TV3. Viết phần chứng minh phán quyết, vòng lặp và kiểm tra tính duy nhất. |
| **TV5 · [Họ tên / MSSV]** | Web GUI, tích hợp nút điều khiển, demo và hướng dẫn chạy | Bàn chơi dùng được, video có quyền xem và hướng dẫn cài/chạy. Viết phần kiến trúc giao diện và hỗ trợ TV1 kiểm tra bản nộp. |

Các mã TV1–TV5 là chỗ điền tên thật. Cuối đồ án, ghi lại nhiệm vụ thực tế và **tỷ lệ hoàn thành của từng người** dựa trên phần đã bàn giao và nghiệm thu.

## 2. Game Engine và giao diện web · 10 điểm

### Game Engine và bộ câu đố · TV1, phối hợp TV2 và TV4

- [ ] Biểu diễn bàn chơi vuông `N×N`. Đánh số hàng từ trên xuống, đánh chữ cột từ trái sang phải và sắp nhân vật theo tên hiển thị. Ví dụ, `C2` là cột C, hàng 2.
- [ ] Lưu tọa độ, tên, nghề, trạng thái ẩn và một manh mối có cấu trúc cho mỗi nhân vật. Đánh dấu các thẻ mở sẵn để công khai trạng thái và manh mối của chúng khi tải câu đố.
- [ ] Tách dữ liệu đầy đủ do Engine giữ khỏi dữ liệu công khai dùng khi chơi. Dữ liệu trả về trình duyệt và dữ liệu đưa vào Agent chỉ chứa thông tin được phép xem, gồm thông tin bàn chơi, trạng thái đã biết và manh mối đã mở. Kiểm tra cả nội dung phản hồi mạng nếu dùng API.
- [ ] Thực hiện `Load` để nạp câu đố và `Restart` để khôi phục đúng bộ thẻ mở sẵn, đồng thời bắt đầu lại tiến trình suy luận.
- [ ] Phối hợp TV4 để xử lý phán quyết thủ công theo bảng bên dưới. Khi chấp nhận, Engine công khai đúng thẻ được chọn cùng trạng thái và manh mối của nó.
- [ ] Chuẩn bị bộ câu đố 3×3 và 4×4 cho thực nghiệm, trong đó có câu đố giải được từng bước từ bộ thẻ mở sẵn. Đối chiếu đáp án ẩn với các manh mối và xác nhận câu đố hợp lệ có đúng một lời giải. Có dữ liệu mẫu để chạy thử cả hai mở rộng. Dùng các ca kẹt hoặc mâu thuẫn để kiểm tra cách hệ thống dừng.

| Tình huống khi chọn trạng thái | Kết quả nghiệm thu |
| --- | --- |
| Dữ kiện công khai chứng minh lựa chọn, trạng thái đúng | Chấp nhận, hiển thị trạng thái và mở đúng một thẻ. |
| Cả hai trạng thái vẫn khả dĩ, kể cả khi lựa chọn tình cờ trùng đáp án ẩn | `NOT_PROVABLE`. Bàn chơi giữ nguyên. |
| Dữ kiện công khai chứng minh trạng thái đối lập | `CONTRADICTED`. Bàn chơi giữ nguyên. |

### Giao diện web · TV5, phối hợp TV1 và TV4

- [ ] Hiển thị lưới, nhãn hàng/cột, tọa độ, tên, nghề, trạng thái đã biết, manh mối đã mở và thẻ đang úp.
- [ ] Cho chọn thẻ và gửi phán quyết `CRIMINAL` hoặc `INNOCENT`. Hiển thị hai lý do từ chối khác nhau như bảng trên.
- [ ] Khi người dùng chọn một manh mối đã mở, tô sáng toàn bộ ô được nhắc trực tiếp hoặc nằm trong vùng dùng để đếm. Dùng cùng cách phân giải vùng với encoder để hai phần hiểu manh mối giống nhau.
- [ ] Gắn đủ bốn điều khiển **Load**, **Restart**, **Hint** và **Auto Solve** vào chức năng thật. Hint chỉ ra một manh mối đã mở có liên quan, một nhân vật có thể chứng minh ngay, hoặc cả hai.
- [ ] Khi chạy Auto Solve, phản ánh các phán quyết được chấp nhận trên bàn chơi và hiển thị manh mối mới tương ứng. Khi giải xong, các trạng thái hiển thị trên bàn chính là kết quả để demo. Khi agent dừng vì thiếu dữ kiện, các thẻ chưa chứng minh vẫn úp.

Mã nguồn và thuật toán chính viết bằng **Python**. Nhóm được dùng thư viện hỗ trợ giao diện hoặc cấu trúc dữ liệu. Công nghệ web, tên module và cách tổ chức mã nguồn do nhóm chọn.

## 3. Biểu diễn logic và mã hóa CNF · 10 điểm · TV2

- [ ] Gán mỗi nhân vật đúng một biến Boolean chính `C_i`, với `True` là phạm tội và `False` là vô tội. Chốt một quy tắc ánh xạ xác định, chẳng hạn theo thứ tự hàng rồi cột. Nếu dùng biến phụ, cấp mã và thống kê riêng với biến chính.
- [ ] Phân giải đủ bốn kiểu vùng **hàng**, **cột**, **lân cận** và **danh sách ô**. Lân cận tính cả đường chéo, loại ô trung tâm và bỏ ô ngoài bàn. Danh sách chứa các ô phân biệt.
- [ ] Kiểm tra kiểu manh mối, số tham số, nhân vật/ô tồn tại, vùng hợp lệ và danh sách ô trùng. Với manh mối đếm, yêu cầu `k` là số nguyên và `0 ≤ k ≤ |R|`.
- [ ] Viết encoder tái sử dụng tự sinh CNF từ dữ liệu có cấu trúc cho sáu mẫu sau. Manh mối đã mở luôn đúng, bất kể chủ thẻ có trạng thái gì.

| Mẫu | Ý nghĩa |
| --- | --- |
| `FACT(i, status)` | Nhân vật `i` có trạng thái đã nêu. |
| `SAME(i, j)` | Hai nhân vật cùng trạng thái. |
| `DIFFERENT(i, j)` | Hai nhân vật khác trạng thái. |
| `EXACTLY(k, R)` | Đúng `k` người trong vùng `R` phạm tội. |
| `AT_LEAST(k, R)` | Ít nhất `k` người trong vùng `R` phạm tội. |
| `AT_MOST(k, R)` | Nhiều nhất `k` người trong vùng `R` phạm tội. |

- [ ] Làm **ít nhất hai mở rộng khác nhau**. Kế hoạch đề xuất `PARITY(EVEN|ODD, R)` để đếm chẵn/lẻ và `COMMON_NEIGHBORS(a, b)` để lấy giao hai tập hàng xóm rồi dùng làm vùng cho một mẫu đếm. Mỗi mở rộng có ví dụ, đường sinh CNF và ca kiểm tra riêng. Nhóm có thể đổi lựa chọn trước khi chốt định dạng dữ liệu.
- [ ] Xây `KB` ở mỗi bước từ manh mối đã mở và các mệnh đề đơn biểu diễn trạng thái đã biết. Chẳng hạn, với nhân vật đã được chứng minh vô tội, thêm `(¬C_i)`. CNF được sinh từ đầu vào ở thời điểm chạy.
- [ ] Viết bộ đánh giá trực tiếp cho mỗi mẫu bắt buộc. Với phép gán hoàn chỉnh, đánh giá ngữ nghĩa của manh mối độc lập với encoder. Ví dụ, đếm số người phạm tội trong vùng rồi so với `k`. Kế hoạch nhóm áp dụng cách kiểm tra trực tiếp này cho cả hai mở rộng.
- [ ] Cung cấp số **biến chính, biến phụ và mệnh đề CNF** cho từng câu đố. Cung cấp danh sách ô đã phân giải để GUI dùng khi tô sáng.
- [ ] Chuẩn bị hai dẫn xuất cho báo cáo. Ví dụ đề xuất gồm `SAME(A, B)` thành `(¬A ∨ B) ∧ (A ∨ ¬B)`, và “đúng một trong A, B, C” thành một mệnh đề buộc ít nhất một người phạm tội cùng ba mệnh đề cấm từng cặp cùng phạm tội.

## 4. Tự cài bộ giải DPLL · 10 điểm · TV3

- [ ] Cài **unit propagation** để gán literal bắt buộc khi một mệnh đề chỉ còn một literal có thể thỏa.
- [ ] Phát hiện xung đột khi một mệnh đề không thể thỏa dưới các phép gán hiện tại.
- [ ] Chọn biến chưa gán theo quy tắc xác định. Phân nhánh đệ quy và quay lui khi nhánh đang thử thất bại.
- [ ] Trả về `SAT` với **phép gán hoàn chỉnh** hoặc `UNSAT`. Khi trả `SAT`, điền cả những biến đã khai báo nhưng còn tự do.
- [ ] Ghi số quyết định phân nhánh, số lần lan truyền, số lần quay lui và thời gian cho mỗi lần gọi SAT. Thống nhất định nghĩa bộ đếm để cộng dồn được trong thực nghiệm.
- [ ] Hỗ trợ Logic Agent kiểm tra giả định tạm. Có thể nhận giả định qua tham số hoặc tạo CNF tạm với mệnh đề đơn, rồi dùng lại `KB` gốc cho truy vấn sau.

Loại bỏ literal thuần và heuristic phân nhánh nâng cao là phần tùy chọn. Dùng bộ DPLL do nhóm tự cài cho các truy vấn của trò chơi.

## 5. Logic Agent · 20 điểm · TV4

### Phân loại và mở thẻ

- [ ] Kiểm tra `KB` hiện tại trước. Nếu `KB` là `UNSAT`, trả `INCONSISTENT` và dừng, vì dữ kiện công khai đang mâu thuẫn.
- [ ] Với `KB` nhất quán, phân loại **mọi nhân vật chưa mở** bằng các giả định tạm trong bảng sau.

| Truy vấn trên nhân vật `i` | Phân loại |
| --- | --- |
| `KB ∧ ¬C_i` là `UNSAT` | `CRIMINAL` vì giả định vô tội dẫn đến mâu thuẫn. |
| `KB ∧ C_i` là `UNSAT` | `INNOCENT` vì giả định phạm tội dẫn đến mâu thuẫn. |
| Cả hai đều `SAT` | `UNKNOWN` vì hai trạng thái đều còn khả dĩ. |

- [ ] Khi có nhiều thẻ suy ra được, chọn theo thứ tự xác định. Gửi một phán quyết đã chứng minh cho Engine, nhận manh mối sau khi được chấp nhận, cập nhật `KB` rồi lặp lại.
- [ ] Dừng đúng khi đã giải hết, khi còn thẻ úp nhưng mọi thẻ đó đều `UNKNOWN`, hoặc khi phát hiện `INCONSISTENT`. Các truy vấn SAT chỉ làm việc trên tri thức công khai ở bước hiện tại.
- [ ] Cho chức năng chơi tay dùng cùng phép phân loại. Trả `NOT_PROVABLE` khi người dùng chọn thẻ `UNKNOWN` và `CONTRADICTED` khi trạng thái đối lập đã được chứng minh.
- [ ] Sinh Hint từ manh mối công khai có liên quan hoặc từ danh sách thẻ có phán quyết bắt buộc. Hint chỉ cung cấp gợi ý và để người dùng tiếp tục thao tác.
- [ ] Sinh **nhật ký suy luận** gồm số bước, mã các manh mối đang dùng, các truy vấn SAT và kết quả, phán quyết, mã/nội dung manh mối vừa mở. Kế hoạch nhóm xuất log hoặc tệp để kiểm tra. Bảng nhật ký trên web là tùy chọn.

### Kiểm tra tính duy nhất

- [ ] Cài một phép kiểm tra riêng dùng **toàn bộ tập manh mối của câu đố**. Tách luồng này khỏi Hint và Auto Solve trong ván đang chơi.
- [ ] Tìm một nghiệm. Nếu `UNSAT`, câu đố không có nghiệm. Nếu có nghiệm, thêm mệnh đề loại đúng phép gán trạng thái đó trên **các biến chính** rồi gọi SAT lần nữa. Lần hai `UNSAT` nghĩa là duy nhất, còn `SAT` nghĩa là có nhiều nghiệm trạng thái. Cách này cho phép các biến phụ có cách gán khác nhau.
- [ ] Kiểm tra các ca không có nghiệm, đúng một nghiệm và nhiều nghiệm. Xác minh riêng khả năng mở thẻ tuần tự, vì một lời giải duy nhất trên toàn bộ manh mối vẫn có thể chưa suy ra được từ các thẻ hiện đang mở.

## 6. Thực nghiệm · 10 điểm · TV3 và TV1

- [ ] Chạy toàn hệ thống trên nhiều câu đố **3×3 và 4×4**. Mốc nội bộ đề xuất là **3 câu mỗi kích thước**. Có thể thêm **5×5** làm ca thử tải. Đề không ấn định số ca cụ thể.
- [ ] Với mỗi ca, ghi số biến chính/phụ, số mệnh đề CNF, số lần gọi SAT, số quyết định, số lan truyền, số quay lui, số bước suy luận hoặc đợt mở thẻ, và thời gian chạy.
- [ ] Ghi điều kiện đo trong báo cáo. Kế hoạch đề xuất lấy số biến và mệnh đề tại **trạng thái công khai cuối của lần chạy**, cộng dồn bộ đếm qua các truy vấn SAT trong Auto Solve, và đo riêng phép kiểm tra tính duy nhất nếu đưa số liệu đó vào báo cáo.
- [ ] Dùng cùng bộ câu đố cho mọi phép so sánh. Ghi đơn vị thời gian và ngưỡng dừng nếu dùng timeout. Giữ lại các ca lỗi, bị kẹt hoặc quá thời gian, kèm trạng thái và số liệu thu được.
- [ ] Viết nhận xét dựa trên kết quả thật, nêu ca bất thường và giới hạn của hệ thống.

### Mẫu bảng kết quả

| Mã câu đố | Kích thước | Biến chính | Biến phụ | Mệnh đề | Lần gọi SAT | Quyết định | Lan truyền | Quay lui | Bước mở | Thời gian (ms) | Kết quả / ghi chú |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| | | | | | | | | | | | |

## 7. Báo cáo PDF · 30 điểm · Cả nhóm

- [ ] **Kế hoạch và phân công** · TV1 tổng hợp. Ghi họ tên/MSSV, trách nhiệm, nhiệm vụ được giao và tỷ lệ hoàn thành của từng người. Đề minh họa điểm cá nhân bằng `9,0 × 90% = 8,1`.
- [ ] **Mô hình hóa** · TV1 và TV2. Mô tả biến, ngữ nghĩa manh mối, `KB`, thông tin công khai và quy trình lật thẻ.
- [ ] **Mã hóa CNF** · TV2. Dẫn xuất từng bước cho ít nhất một manh mối giữa hai nhân vật và một manh mối đếm. Ghi cách mã hóa và hai mở rộng mà nhóm thực sự đã triển khai.
- [ ] **Thuật toán** · TV3 và TV4. Trình bày DPLL, kiểm tra hệ quả logic, vòng lặp suy luận và phép kiểm tra tính duy nhất. Minh họa bằng một ví dụ từ nhật ký của chương trình.
- [ ] **Thực nghiệm** · TV3, TV1 đối chiếu dữ liệu. Đưa bảng hoặc biểu đồ, nhận xét, ca thất bại và giới hạn. Đối chiếu với số liệu chạy thực tế.
- [ ] **Tài liệu tham khảo và phụ lục** · Cả nhóm. Liệt kê tất cả nguồn đã sử dụng. Nếu dùng AI tạo sinh, ghi cách nhóm sử dụng và các prompt có liên quan trong phụ lục.
- [ ] **Hoàn thiện PDF** · TV1 và TV5. Rà soát bố cục, hình/bảng, đối chiếu tên tính năng với phiên bản nộp, và kiểm tra liên kết video trong `Report.pdf`.

## 8. Video demo · 10 điểm · TV5, TV1 và TV4

- [ ] Quay video khoảng **5–10 phút**, có **thuyết minh hoặc phụ đề tiếng Việt hay tiếng Anh**.
- [ ] **GUI (5 điểm)**. Giới thiệu bàn chơi, tọa độ, thẻ úp/mở, trạng thái và các điều khiển. Quay thao tác chọn manh mối để thấy các ô liên quan được tô sáng.
- [ ] **Chức năng (5 điểm)**. Trình diễn cả **chơi thủ công** và **chạy bộ giải**. Kịch bản đề xuất gồm nạp câu đố, thử phán quyết chưa chứng minh được, mở một thẻ hợp lệ, dùng Hint, Restart rồi chạy Auto Solve để hiện kết quả trên bàn.
- [ ] Tải video lên **Google Drive**, đặt quyền **bất kỳ ai có liên kết đều có thể xem**, kiểm tra bằng cửa sổ riêng tư/ẩn danh và chèn liên kết Drive vào báo cáo. Đề không nhận liên kết YouTube.

## 9. Kiểm tra chéo trước khi quay và nộp

Các ca dưới đây là cách nhóm kiểm chứng yêu cầu, có thể chạy tự động hoặc kiểm tra thủ công tùy phần.

| Ca kiểm tra | Kết quả mong đợi | Thực hiện |
| --- | --- | --- |
| Thử đủ ba tình huống chơi tay ở mục 2 | Đúng nhãn phản hồi, mở đúng thẻ hoặc giữ nguyên trạng thái tùy tình huống. | TV1 + TV5 |
| Chọn manh mối rồi kiểm tra tô sáng và nội dung phản hồi web | Tô đúng vùng. Dữ liệu gửi về trình duyệt chỉ chứa thông tin công khai. | TV2 + TV5 |
| Kiểm tra vùng lân cận ở giữa, cạnh, góc và tham số biên | Trên 3×3, tương ứng 8, 5, 3 ô. Nhận `k=0` và `k` bằng kích thước vùng, từ chối tham số/vùng sai. | TV1 + TV2 |
| So sánh bộ đánh giá trực tiếp với CNF trên các phép gán nhỏ | Với cùng phép gán các biến chính, CNF có nghiệm khi và chỉ khi bộ đánh giá trả đúng. Thử cả sáu mẫu và hai mở rộng. | TV2 + TV3 |
| Chạy DPLL với công thức SAT, xung đột và ca buộc quay lui | Trả đúng kết quả, đủ phép gán khi SAT, bộ đếm phản ánh việc lan truyền và quay lui. | TV3 + TV4 |
| Chạy Agent trên ca giải xong, ca kẹt và ca mâu thuẫn | Dừng đúng lý do. Nhật ký cho thấy mỗi lần mở thẻ dựa trên dữ kiện có sẵn trước bước đó. | TV1 + TV4 |
| Thử kiểm tra duy nhất trên ca có 0, 1 và nhiều nghiệm | Phân biệt đúng số nghiệm theo trạng thái nhân vật. | TV2 + TV4 |
| Giải nén bản nộp ở thư mục mới rồi chạy theo README | Cài được phụ thuộc, mở được web, tải được câu đố và dùng được các điều khiển. | TV1 + TV5 |

## 10. Kế hoạch khoảng 3 tuần

| Mốc nội bộ | Việc cần chốt | Điều kiện bàn giao |
| --- | --- | --- |
| **Tuần 1 · Chốt dữ liệu và nối luồng cơ bản** | TV1/TV2 chốt định dạng câu đố và hai mở rộng. TV2/TV3 thống nhất đầu vào CNF và danh sách biến. TV3/TV4 chốt giả định, kết quả SAT và chỉ số. TV1/TV4/TV5 chốt dữ liệu công khai, phán quyết, mở thẻ và định dạng nhật ký. | Một câu đố mẫu, một phán quyết hợp lệ chạy xuyên từ logic tới bàn chơi. TV5 có thể dùng dữ liệu công khai mẫu trong lúc các phần khác đang làm. |
| **Tuần 2 · Tích hợp đủ chức năng** | Hoàn tất sáu mẫu, hai mở rộng, DPLL, Logic Agent, kiểm tra tính duy nhất và bốn điều khiển web. Chạy các ca kiểm tra chéo và chuẩn bị bộ câu đố thực nghiệm. | Chơi tay, Hint, Auto Solve và Restart dùng được. Có ca giải được, ca kẹt và ca mâu thuẫn với kết quả kiểm tra tương ứng. |
| **Tuần 3 · Đo, viết, quay và đóng gói** | TV3 đo và phân tích. Cả nhóm hoàn thiện các phần báo cáo. TV5 quay video. TV1 và TV5 kiểm tra liên kết, bản PDF và bản nộp. | Bản nén chạy được khi giải nén ở thư mục mới, báo cáo đủ mục, video mở được trong cửa sổ ẩn danh. |

## 11. Đóng gói và nộp bài

- [ ] Điền ngày giờ nộp theo thông báo của lớp. PDF chỉ nêu thời lượng khoảng **3 tuần**.
- [ ] Hoàn thiện hướng dẫn cài/chạy theo môi trường thật, gồm phiên bản Python, cài phụ thuộc, lệnh khởi động web, địa chỉ truy cập và cách tải câu đố mẫu. Bổ sung vào `Source/README.md` trong gói nộp theo mẫu của đề. README hiện tại là kế hoạch công việc.
- [ ] Nén mã nguồn và `Report.pdf` thành `.zip` hoặc `.rar`, đặt tên `StudentID1_StudentID2_StudentID3_StudentID4_StudentID5` theo MSSV thật.
- [ ] Kiểm tra gói nộp có mã nguồn, câu đố dùng để chạy, hướng dẫn và danh sách phụ thuộc. Mẫu trong đề có thư mục `Source/` với `main.py`, `README.md`, `requirements.txt`, cùng `Report.pdf` chứa liên kết video ở cấp ngoài.
- [ ] Nếu tệp nén **lớn hơn 20 MB**, tải lên Google Drive và nộp qua liên kết chia sẻ. Kiểm tra quyền truy cập của cả tệp nén và video khi dùng liên kết Drive.
- [ ] Chốt bản nộp trước hạn và giữ nguyên sau hạn. Mỗi thành viên nắm phần mình thực hiện để có thể giải thích nếu được chọn vấn đáp. Tuân thủ quy định về liêm chính học thuật trong đề.
