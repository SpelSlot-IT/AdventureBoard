document.addEventListener('DOMContentLoaded', () => {
  const form          = document.getElementById('loginForm');
  const usernameInput = form.username;
  const passwordInput = form.password;
  const toggleBtn     = document.getElementById('togglePassword');
  const userErr       = document.getElementById('usernameError');
  const passErr       = document.getElementById('passwordError');

    // Toggle password visibility
  toggleBtn.addEventListener('click', () => {
    const isHidden = passwordInput.type === 'password';
    passwordInput.type = isHidden ? 'text' : 'password';
    toggleBtn.textContent = isHidden ? 'Hide' : 'Show';
  });

  // Handle login submit
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    userErr.textContent = '';
    passErr.textContent = '';

    try {
      const formData = new URLSearchParams(new FormData(form));
      const resp     = await fetch('login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
      });
      const data = await resp.json();

      if (!data.success) {
        // Display field errors or general errors
        if (data.errors?.username) userErr.textContent = data.errors.username;
        if (data.errors?.password) passErr.textContent = data.errors.password;
        if (data.errors?.database) showToast(data.errors.database);
        return;
      }

      // On successful login, receive JWT token
      const { token, message, redirect_url } = data;
      // Store token securely (consider HttpOnly cookie for production)
      localStorage.setItem('authToken', token);
      console.log(message);

      // Optionally set auth header for future fetch calls
      // Example: fetch('/protected', { headers: { 'Authorization': `Bearer ${token}` } })

      // Redirect user
      if (redirect_url) {
        window.location.href = redirect_url;
      } else {
        // Fallback to dashboard
        window.location.href = 'app';
      }
    } catch (err) {
      console.error('Login error:', err);
      alert('An unexpected error occurred. Please try again later.');
    }
  });
});
