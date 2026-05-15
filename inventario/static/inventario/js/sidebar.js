const btnToggle = document.getElementById('btn-toggle'); // botón del header
const btnClose = document.getElementById('btn-close-sidebar'); // Botón X para cerrar sidebar
const container = document.querySelector('#customRoot');

// Función principal de toggle
btnToggle.addEventListener('click', () => {
    if (window.innerWidth <= 768) {
        // En móvil usamos la clase de overlay
        container.classList.toggle('sidebar-open');
    } else {
        // En escritorio usamos tu clase original de colapsar
        container.classList.toggle('collapsed');
    }
});

// Evento para el botón X (solo cierra el overlay)
if (btnClose) {
    btnClose.addEventListener('click', () => {
        container.classList.remove('sidebar-open');
    });
}