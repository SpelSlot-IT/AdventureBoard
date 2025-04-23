document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const togglePassword = document.getElementById('togglePassword');
    const passwordInput = document.getElementById('password');
    const usernameError = document.getElementById('usernameError');
    const passwordError = document.getElementById('passwordError');

    togglePassword.addEventListener('click', () => {
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);
        togglePassword.textContent = type === 'password' ? 'Show' : 'Hide';
    });

    loginForm.addEventListener('submit', (e) => {
        let valid = true;

        usernameError.textContent = '';
        passwordError.textContent = '';

        if (!loginForm.username.value.trim()) {
            usernameError.textContent = 'Username is required';
            valid = false;
        }

        if (!loginForm.password.value) {
            passwordError.textContent = 'Password is required';
            valid = false;
        }

        if (!valid) {
            e.preventDefault();
        }
    });
});