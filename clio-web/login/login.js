import Alpine from 'alpinejs'
import header from '../header.js'
import {errMsg} from "../utils";

window.Alpine = Alpine

function loginForm() {
    return {
        username: '',
        password: '',
        error: '',
        async login() {
            this.error = '';
            this.loading = true;
            try {
                const response = await fetch(window.API_HOST + '/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({username: this.username, password: this.password})
                });
                if (!response.ok) {
                    throw new Error(errMsg(response));
                }
                const token = await response.text();
                if (token) {
                    localStorage.setItem('token',token);
                    window.location = "/"
                } else {
                    throw new Error('No token returned');
                }
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
            }
        }
    }
}

Alpine.data('header', header)
Alpine.data('loginForm', loginForm)

Alpine.start()