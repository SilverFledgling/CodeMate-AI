async function processAudio() {
    const audioInput = document.getElementById("audioInput").files[0];
    if (!audioInput) {
        alert("Vui lòng chọn file âm thanh!");
        return;
    }

    const formData = new FormData();
    formData.append("audio", audioInput);

    const response = await fetch("http://localhost:5000/api/process", {
        method: "POST",
        body: formData
    });

    const result = await response.json();
    document.getElementById("transcript").innerText = "Nhận diện: " + result.transcript;
    document.getElementById("response").innerText = "Phản hồi: " + result.response;
}