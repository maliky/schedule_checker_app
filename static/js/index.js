document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("uploadForm");
    const spinnerContainer = document.getElementById("spinner-container");
    const messageArea = document.getElementById("message-area");

    form.addEventListener("submit", function (event) {
        event.preventDefault();

        const formData = new FormData(form);
        spinnerContainer.style.display = "block"; // show spinner
        messageArea.innerHTML = ""; // clear messages

        fetch("/upload", {
            method: "POST",
            body: formData,
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Network response was not ok");
                }
                return response.text();
            })
            .then((data) => {
                spinnerContainer.style.display = "none"; // hide spinner
                messageArea.innerHTML = `
    <div class="alert alert-success">
      File processed successfully!<br />
      <a href="/view_instructor_chart">View instructor_chart</a> &nbsp;|&nbsp;
      <a href="/view_room_chart">View room_chart</a>
      <a href="/download_processed">Download standardized schedule file</a>
    </div>
  `;
            })
            .catch((error) => {
                spinnerContainer.style.display = "none";
                messageArea.innerHTML = `
          <div class="alert alert-danger">
            There was an error uploading the file: ${error}
          </div>
        `;
            });
    });
});
