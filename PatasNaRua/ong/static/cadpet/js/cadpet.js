document.addEventListener("DOMContentLoaded", () => {
    const inputFile = document.querySelector("#fotoInput");
    const pictureImage = document.querySelector(".fotoImg");
    const pictureImageTxt = "Choose an image";
    const form = document.querySelector("form.dados");
    const PLACEHOLDER_URL = window.PLACEHOLDER_URL || "#";

    pictureImage.innerHTML = pictureImageTxt;

    inputFile.addEventListener("change", function (e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.addEventListener("load", function (e) {
                const img = document.createElement("img");
                img.src = e.target.result;
                img.classList.add("picture__img");

                const label = document.querySelector("label.foto");
                label.innerHTML = "";
                label.appendChild(img);
            });

            reader.readAsDataURL(file);
        } else {
            pictureImage.innerHTML = pictureImageTxt;
        }
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const formData = new FormData(form);
        const file = inputFile.files[0];
        if (file) {
            formData.append("foto", file);
        }

        try {
            const response = await fetch("/api/cadpet/", {
                method: "POST",
                body: formData
            });
            const data = await response.json();
            if (response.ok) {
                alert("Pet cadastrado com sucesso!");
                form.reset();

                const label = document.querySelector("label.foto");
                label.innerHTML = `<span class="fotoImg">${pictureImageTxt}</span>`;
                inputFile.value = "";
            } else {
                alert("Erro: " + (data.erro || "Erro desconhecido."));
            }
        } catch (error) {
            console.error("Erro de rede:", error);
            alert("Falha de comunicação com o servidor.");
        }
    });
});
