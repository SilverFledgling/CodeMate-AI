// --- FILE: frontend/script.js ---

const recordButton = document.getElementById('recordButton');
const stopButton = document.getElementById('stopButton');
const processButton = document.getElementById('processButton');
const audioInput = document.getElementById('audioInput');
const statusDiv = document.getElementById('status');
const transcriptSpan = document.getElementById('transcript');
const responseSpan = document.getElementById('response');
const fileNameSpan = document.getElementById('file-name');

let mediaRecorder;
let audioChunks = [];
let audioSource = null; // Biến toàn cục để lưu trữ nguồn audio (File hoặc Blob)

// --- Logic quản lý file tải lên ---
audioInput.addEventListener('change', () => {
    if (audioInput.files.length > 0) {
        const file = audioInput.files[0];
        fileNameSpan.textContent = `File đã chọn: ${file.name}`;
        audioSource = file; // Lưu file vào biến
        updateStatus('Sẵn sàng xử lý file.', false, 3000);
    } else {
        fileNameSpan.textContent = 'Chưa có file nào được chọn';
        audioSource = null;
    }
});

// --- Logic Ghi Âm ---
recordButton.addEventListener('click', async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstart = () => {
            recordButton.disabled = true;
            stopButton.disabled = false;
            processButton.disabled = true; // Vô hiệu hóa nút Xử lý khi đang ghi
            audioInput.disabled = true;
            updateStatus('Đang ghi âm... 🔴');
            fileNameSpan.textContent = 'Chế độ ghi âm...';
            audioSource = null; // Xóa nguồn cũ
        };

        mediaRecorder.onstop = () => {
            recordButton.disabled = false;
            stopButton.disabled = true;
            processButton.disabled = false; // Kích hoạt lại nút Xử lý
            audioInput.disabled = false;

            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            audioChunks = []; // Reset lại
            
            // Lưu bản ghi âm vào biến toàn cục
            audioSource = new File([audioBlob], "recording.wav", { type: "audio/wav" });
            fileNameSpan.textContent = 'Bản ghi âm đã sẵn sàng.';
            updateStatus('Ghi âm hoàn tất. Sẵn sàng để xử lý.', false, 3000);
        };

        mediaRecorder.start();

    } catch (error) {
        console.error('Lỗi khi truy cập microphone:', error);
        updateStatus('Lỗi: Không thể truy cập microphone.', true);
    }
});

stopButton.addEventListener('click', () => {
    if (mediaRecorder) {
        mediaRecorder.stop();
    }
});

// --- Logic Xử Lý chung ---
processButton.addEventListener('click', () => {
    if (!audioSource) {
        alert("Vui lòng chọn một file hoặc ghi âm trước khi xử lý!");
        return;
    }
    sendAudioToServer(audioSource);
});


// --- Hàm Gửi Dữ Liệu Lên Server ---
async function sendAudioToServer(audioFile) {
    const formData = new FormData();
    formData.append("audio", audioFile);

    updateStatus('Đang xử lý, vui lòng chờ...');
    transcriptSpan.textContent = "...";
    responseSpan.textContent = "...";

    try {
        const response = await fetch("http://localhost:5000/api/process", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Lỗi từ server: ${response.statusText}`);
        }

        const result = await response.json();
        transcriptSpan.textContent = result.transcript || "[Lỗi]";
        responseSpan.textContent = result.response || "[Lỗi]";
        updateStatus('Xử lý hoàn tất!', false, 3000);

    } catch (error) {
        console.error('Lỗi khi gửi file:', error);
        updateStatus('Đã có lỗi xảy ra. Vui lòng thử lại.', true);
    } finally {
        // Reset sau khi xử lý xong
        audioSource = null;
        audioInput.value = ''; // Xóa file đã chọn khỏi input
        fileNameSpan.textContent = 'Chưa có file nào được chọn';
    }
}

// --- Hàm Tiện Ích ---
function updateStatus(message, isError = false, hideAfter = 0) {
    statusDiv.textContent = message;
    statusDiv.className = isError ? 'status-visible status-error' : 'status-visible';
    if (hideAfter > 0) {
        setTimeout(() => {
            statusDiv.className = 'status-hidden';
        }, hideAfter);
    }
}