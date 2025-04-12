// Initialize Firebase with configuration from the page
function initializeFirebase() {
    try {
        const configElement = document.getElementById('firebase-config');
        if (!configElement) {
            console.error('Firebase configuration not found');
            return false;
        }

        const firebaseConfig = JSON.parse(configElement.textContent);
        if (!firebase.apps.length) {
            firebase.initializeApp(firebaseConfig);
        }
        return true;
    } catch (error) {
        console.error('Error initializing Firebase:', error);
        showError('Failed to initialize authentication system');
        return false;
    }
}

// Login user with Firebase
async function loginUser(email, password) {
    if (!initializeFirebase()) return;

    try {
        const userCredential = await firebase.auth().signInWithEmailAndPassword(email, password);
        const user = userCredential.user;

        // Get ID token and user ID
        const idToken = await user.getIdToken();
        const userId = user.uid;

        // Set user cookie
        document.cookie = `user_id=${userId}; path=/; max-age=3600`;

        // Redirect to boards page
        window.location.href = '/boards';
    } catch (error) {
        console.error('Login error:', error);
        handleAuthError(error);
        throw error;
    }
}

// Register user with Firebase
async function registerUser(email, password, displayName) {
    if (!initializeFirebase()) return;

    try {
        // Create user with email and password
        const userCredential = await firebase.auth().createUserWithEmailAndPassword(email, password);
        const user = userCredential.user;

        // Update display name if provided
        if (displayName) {
            await user.updateProfile({
                displayName: displayName
            });
        }

        // Send user data to backend
        const response = await fetch('/api/create-user', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                uid: user.uid,
                email: user.email,
                displayName: displayName || email.split('@')[0]
            }),
        });

        if (!response.ok) {
            throw new Error('Failed to create user profile');
        }

        // Set user cookie
        document.cookie = `user_id=${user.uid}; path=/; max-age=3600`;

        // Redirect to boards page
        window.location.href = '/boards';
    } catch (error) {
        console.error('Registration error:', error);
        handleAuthError(error);
        throw error;
    }
}

// Logout user
async function logoutUser() {
    if (!initializeFirebase()) return;

    try {
        await firebase.auth().signOut();
        
        // Clear user cookie
        document.cookie = 'user_id=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
        
        // Redirect to login page
        window.location.href = '/';
    } catch (error) {
        console.error('Logout error:', error);
        showError('Failed to log out. Please try again.');
    }
}

// Handle authentication state changes
function setupAuthStateListener() {
    if (!initializeFirebase()) return;

    firebase.auth().onAuthStateChanged((user) => {
        const currentPath = window.location.pathname;
        
        if (user) {
            // User is signed in
            if (currentPath === '/' || currentPath === '/register') {
                window.location.href = '/boards';
            }
        } else {
            // User is signed out
            if (currentPath !== '/' && currentPath !== '/register') {
                window.location.href = '/';
            }
        }
    });
}

// Handle authentication errors
function handleAuthError(error) {
    let errorMessage = 'An error occurred. Please try again.';

    switch (error.code) {
        case 'auth/email-already-in-use':
            errorMessage = 'This email is already registered. Please login instead.';
            break;
        case 'auth/invalid-email':
            errorMessage = 'Invalid email address.';
            break;
        case 'auth/operation-not-allowed':
            errorMessage = 'Email/password accounts are not enabled. Please contact support.';
            break;
        case 'auth/weak-password':
            errorMessage = 'Password should be at least 6 characters long.';
            break;
        case 'auth/user-disabled':
            errorMessage = 'This account has been disabled. Please contact support.';
            break;
        case 'auth/user-not-found':
            errorMessage = 'No account found with this email.';
            break;
        case 'auth/wrong-password':
            errorMessage = 'Invalid password.';
            break;
        case 'auth/too-many-requests':
            errorMessage = 'Too many failed attempts. Please try again later.';
            break;
    }

    showError(errorMessage);
}

// Show error message
function showError(message) {
    const errorElement = document.getElementById('login-error') || 
                        document.getElementById('register-error') ||
                        document.createElement('div');
    
    if (!errorElement.id) {
        errorElement.className = 'alert alert-danger mt-3';
        errorElement.role = 'alert';
        document.querySelector('form').appendChild(errorElement);
    }

    errorElement.textContent = message;
    errorElement.style.display = 'block';

    // Auto-hide error after 5 seconds
    setTimeout(() => {
        errorElement.style.display = 'none';
    }, 5000);
}

// Cookie management utilities
const Cookies = {
    set: function(name, value, days) {
        let expires = '';
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = '; expires=' + date.toUTCString();
        }
        document.cookie = name + '=' + value + expires + '; path=/';
    },

    get: function(name) {
        const nameEQ = name + '=';
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
        }
        return null;
    },

    delete: function(name) {
        document.cookie = name + '=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    }
};

// Session management
const SessionManager = {
    checkSession: function() {
        const userId = Cookies.get('user_id');
        if (!userId && window.location.pathname !== '/' && window.location.pathname !== '/register') {
            window.location.href = '/';
        }
    },

    refreshSession: function() {
        const userId = Cookies.get('user_id');
        if (userId) {
            Cookies.set('user_id', userId, 1); // Refresh for 1 day
        }
    }
};

// Initialize authentication state listener when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    setupAuthStateListener();
    SessionManager.checkSession();

    // Refresh session when user interacts with the page
    document.addEventListener('click', () => {
        SessionManager.refreshSession();
    });
});

// Export functions for use in other scripts
window.loginUser = loginUser;
window.registerUser = registerUser;
window.logoutUser = logoutUser;