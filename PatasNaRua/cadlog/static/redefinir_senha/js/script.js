const novaSenha = document.getElementById('nova_senha')
const confirmaSenha = document.getElementById('confirma_senha');
const feedback = document.getElementById('senha-feedback');
        
    function verificarSenhas() {
        if (confirmaSenha.value === '') {
            feedback.textContent = '';
            feedback.className = 'senha-match';
            return;
        }
            
        if (novaSenha.value === confirmaSenha.value) {
            feedback.textContent = '✓ As senhas coincidem';
            feedback.className = 'senha-match match';
        } else {
            feedback.textContent = '✗ As senhas não coincidem';
            feedback.className = 'senha-match no-match';
        }
    }
        
    novaSenha.addEventListener('input', verificarSenhas);
    confirmaSenha.addEventListener('input', verificarSenhas);