const telaLogin = document.getElementById('tela-login')
const telaEsqueciSenha = document.getElementById('tela-esqueci-senha')
const linkEsqueciSenha = document.getElementById('link-esqueci-senha')
const linkVoltarLogin = document.getElementById('link-voltar-login')

linkEsqueciSenha.addEventListener('click', function(e){
    e.preventDefault();
    telaLogin.style.display = 'none';
    telaEsqueciSenha.style.display = 'block';
});

linkVoltarLogin.addEventListener('click', function(e){
    e.preventDefault();
    telaEsqueciSenha.style.display = 'none';
    telaLogin.style.display = 'block';
});