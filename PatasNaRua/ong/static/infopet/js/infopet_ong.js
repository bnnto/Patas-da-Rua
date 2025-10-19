document.addEventListener('DOMContentLoaded', function () {
    const botaoRemover = document.querySelector('.botao-remover');
    if(botaoRemover) {
        botaoRemover.addEventListener('submit', function(event) {
            event.preventDefault();
            const petNome = this.getAttribute('data-pet-nome') || 'este pet';
            const confirmar = confirm('Tem certeza que deseja remover permanentemente o pet: ${petNome}? Esta ação não pode ser desfeita.');
            if(confirmar) {
                window.location.href = this.href;
            }
        })
    }
})