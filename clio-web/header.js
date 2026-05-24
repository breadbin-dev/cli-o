export function header() {
    return {
        title: window.SITE_TITLE
    }
}

export function logout() {
    localStorage.setItem('token', '')
    window.location = "/login/login.html"
}

export default header;