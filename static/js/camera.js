window.onload = function () {
    startCamera();
};

let videoStream = null;
let isProcessing = false;

function startCamera() {
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(function (stream) {
            const video = document.getElementById("video");
            video.srcObject = stream;
            videoStream = stream;
        })
        .catch(function () {
            alert("Camera access denied or not available ❌");
        });
}

function captureImage() {

    if (isProcessing) return;   // prevent multiple clicks
    isProcessing = true;

    const video = document.getElementById("video");

    if (!video.videoWidth) {
        document.getElementById("result").innerText = "Camera not ready ❌";
        isProcessing = false;
        return;
    }

    const canvas = document.createElement("canvas");

    // 🔥 Resize image (faster recognition)
    const scale = 0.5;
    canvas.width = video.videoWidth * scale;
    canvas.height = video.videoHeight * scale;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const imageData = canvas.toDataURL("image/jpeg", 0.7); // compressed image

    document.getElementById("result").innerText = "Processing... ⏳";

    fetch("/recognize", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ image: imageData })
    })
        .then(response => response.json())
        .then(data => {
            document.getElementById("result").innerText = data.message;
            isProcessing = false;
        })
        .catch(() => {
            document.getElementById("result").innerText = "Error processing image ❌";
            isProcessing = false;
        });
}