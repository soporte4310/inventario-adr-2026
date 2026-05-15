const MenuUsuarioPerfil = document.getElementById("MenuUsuarioPerfil");
const MenuUsuarioDropdown = document.getElementById("MenuUsuarioDropdown");

// Cuando el usuario hace click en su nombre o avatar, se oculta o muestra un menú desplegable con más opciones
MenuUsuarioPerfil.addEventListener('click', () => {
    MenuUsuarioDropdown.classList.toggle('activo')
})

// Listener para detectar clicks fuera del menú desplegable con la finalidad de ocultarlo automáticamente
document.addEventListener('click', (event) => {
    const esClickDentroMenu = MenuUsuarioDropdown.contains(event.target);
    const esClickEnBoton = MenuUsuarioPerfil.contains(event.target);

    if (!esClickDentroMenu && !esClickEnBoton) {
        MenuUsuarioDropdown.classList.remove('activo');
    }
});
