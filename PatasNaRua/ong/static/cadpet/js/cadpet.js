document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("form.dados");
    const imgInput = document.getElementById("seletorDeImagem");
    const imgPreview = document.getElementById("imagemVisualizada");

    imgInput.addEventListener("change", () => {
        const file = imgInput.files[0];
        if(file) {
            imgPreview.src = URL.createObjectURL(file);
        } else {
            imgPreview.src = "#";
        }
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const formData = new FormData(form);
        try {
            const response = await fetch("/api/cadpet/", {
                method: "POST",
                body: formData
            });
            const data = await response.json();
            if(response.ok){
                alert("Pet cadastrado com sucesso!");
                form.reset();
                imgPreview.src = "#"
            } else {
                alert("Erro: " + (data.erro || "Erro desconhecido."));
            }
        } catch (error) {
            console.error("Erro de rede: ", error);
            alert("Falha de comunicação com o servidor.");
        }
    })
})