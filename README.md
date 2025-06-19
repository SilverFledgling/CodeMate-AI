🎯 Dự án Nhận dạng Giọng nói và Phân loại Ý định Tiếng Việt

Đây là dự án xây dựng một ứng dụng web hoàn chỉnh có khả năng nhận diện giọng nói tiếng Việt từ file âm thanh, sau đó phân loại ý định của câu nói đó và đưa ra phản hồi tương ứng. Dự án này là một phần của học phần Thực tập cơ sở (TTCS).

Ứng dụng sử dụng mô hình Whisper đã được tinh chỉnh (fine-tuned) trên dữ liệu tiếng Việt để đạt độ chính xác cao và mô hình PhoBERT để hiểu ngữ nghĩa của văn bản.

✨ Tính năng chính

  * Nhận dạng giọng nói (Speech-to-Text): Chuyển đổi file âm thanh (`.m4a`, `.mp3`, `.wav`...) sang văn bản tiếng Việt.
  * Phân loại ý định (Intent Classification): Phân loại văn bản đã nhận dạng thành các ý định cơ bản như "chào hỏi", "hỏi", "yêu cầu".
  * Phản hồi thông minh: Đưa ra câu trả lời dựa trên ý định đã được phân loại.
  * Giao diện Web: Giao diện người dùng đơn giản, dễ sử dụng để tải file lên và xem kết quả.
  * Backend Flask: Server backend được xây dựng bằng Flask, nhẹ và hiệu quả.

 🛠️ Công nghệ sử dụng

  * Backend:
      * Ngôn ngữ: Python
      * Web Framework: Flask
      * AI/ML: PyTorch, Transformers, Datasets, Accelerate, PEFT
      * Xử lý âm thanh: Librosa, SoundFile
      * Cơ sở dữ liệu: MySQL (dùng để lưu trữ lịch sử - đang trong quá trình tích hợp)
  * Frontend:
      * HTML5
      * CSS3
      * JavaScript (dùng `fetch` API để gọi backend)

 📁 Cấu trúc dự án

```
TTCS/
├── backend/
│   ├── whisper-finetuned-vi/   # Thư mục chứa model fine-tuned (hiện tại tải từ Hub)
│   ├── uploads/                # Thư mục tạm để lưu file audio upload
│   ├── fine_tune_on_colab.py   # Script dùng để fine-tune model trên Colab
│   ├── nlp_phobert.py          # File server Flask chính, xử lý API
│   ├── requirements.txt        # Danh sách các thư viện Python cần thiết
│   └── database.sql            # Script khởi tạo cơ sở dữ liệu
│
└── frontend/
    ├── index.html              # Giao diện chính của ứng dụng
    ├── script.js               # Logic xử lý sự kiện phía client
    └── style.css               # Định dạng giao diện
```

 🚀 Hướng dẫn cài đặt và khởi chạy

Thực hiện các bước sau để chạy dự án trên máy local.

 1\. Yêu cầu tiên quyết

  * Đã cài đặt Python 3.9+
  * Đã cài đặt Git.
  * Đã cài đặt và khởi động MySQL Server.
  * Đã cài đặt FFmpeg và thêm nó vào biến môi trường PATH (để xử lý file như`.m4a`).

 2\. Cài đặt

1. Clone repository từ GitHub:

    ```bash
    git clone https://github.com/ElfiDeeper/TTCS.git
    cd TTCS
    ```

2.  Tạo cơ sở dữ liệu:

      * Kết nối vào MySQL Server của bạn (dùng MySQL Workbench hoặc dòng lệnh).
      * Chạy toàn bộ các lệnh trong file `backend/database.sql` để tạo database `speech_recognition` và bảng `history`.

3.  Cài đặt các thư viện Python:

      * Mở terminal (CMD hoặc Git Bash) trong thư mục `TTCS`, sau đó di chuyển vào `backend`.
      * Tạo một môi trường ảo (khuyến khích):
        ```bash
        cd backend
        python -m venv venv
        # Trên Windows
        venv\Scripts\activate
        # Trên macOS/Linux
        # source venv/bin/activate
        ```
      * Cài đặt tất cả các gói cần thiết:
        ```bash
        pip install -r requirements.txt
        ```

 3\. Khởi chạy ứng dụng

1.  Hãy đảm bảo bạn đang ở trong thư mục `backend` và môi trường ảo đã được kích hoạt.
2.  Chạy server Flask:
    ```bash
    python nlp_phobert.py
    ```
3.  Nếu không có lỗi, server sẽ chạy và lắng nghe ở địa chỉ `http://127.0.0.1:5000`.

 4\. Sử dụng

1.  Mở trình duyệt web của bạn và truy cập: `http://127.0.0.1:5000`.
2.  Nhấn nút "Choose File" để chọn một file âm thanh từ máy tính.
3.  Nhấn nút "Xử lý".
4.  Chờ trong giây lát để server xử lý, kết quả phiên âm và phản hồi sẽ hiện ra trên trang.

 🧠 Thông tin về mô hình AI

  * Mô hình nhận dạng giọng nói:

      * Sử dụng `openai/whisper-base` đã được fine-tune trên tập dữ liệu tiếng Việt để tăng độ chính xác.
      * Mô hình này được lưu trữ và tải về tự động từ Hugging Face Hub tại địa chỉ: [Duke03/Whisper-base-finetuned-vietnamese](https://huggingface.co/Duke03/Whisper-base-finetuned-vietnamese/tree/main).
  * Mô hình phân loại ý định:

      * Sử dụng `vinai/phobert-base`, một mô hình ngôn ngữ mạnh mẽ cho tiếng Việt.
      * Mô hình được tải trực tiếp từ Hugging Face Hub.

 🔮 Hướng phát triển trong tương lai

  * Hoàn thiện và tích hợp lại tính năng lưu lịch sử xử lý vào database MySQL.
  * Fine-tune mô hình PhoBERT trên một tập dữ liệu phân loại ý định cụ thể để tăng độ chính xác.
  * Cải thiện giao diện người dùng, thêm tính năng ghi âm trực tiếp trên trình duyệt.
  * Đóng gói dự án bằng Docker để dễ dàng triển khai.

-----
