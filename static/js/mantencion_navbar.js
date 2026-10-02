// Controla el navbar retráctil del módulo de Mantención.
// A diferencia del sidebar del sitio principal (static/js/sidebar.js, que
// se abre con el mouse), este usa un botón que se toca/hace click, porque
// en el celular no existe el hover: es el uso principal que pide el brief.
document.addEventListener('DOMContentLoaded', function () {
  const navbar = document.getElementById('mnt-navbar');
  const toggle = document.getElementById('mnt-navbar-toggle');
  const cerrar = document.getElementById('mnt-navbar-close');
  const overlay = document.getElementById('mnt-overlay');

  function abrirNavbar() {
    navbar.classList.remove('-translate-x-full');
    overlay.classList.remove('hidden');
    // El botón hamburguesa queda tapado por el navbar abierto (mismo
    // z-index, el navbar va después en el HTML): lo ocultamos mientras
    // esté abierto para no dejar un botón "fantasma" ahí. Para cerrar
    // queda la X de adentro del menú o tocar fuera de él.
    if (toggle) toggle.classList.add('hidden');
  }

  function cerrarNavbar() {
    navbar.classList.add('-translate-x-full');
    overlay.classList.add('hidden');
    if (toggle) toggle.classList.remove('hidden');
  }

  if (toggle) toggle.addEventListener('click', abrirNavbar);
  if (cerrar) cerrar.addEventListener('click', cerrarNavbar);
  if (overlay) overlay.addEventListener('click', cerrarNavbar);

  // En el celular, tocar un link del menú debería cerrarlo de inmediato
  // (en escritorio esto no se nota: md:translate-x-0 mantiene el navbar
  // fijo y visible pase lo que pase con esta clase).
  navbar.querySelectorAll('a.mnt-nav-link').forEach(function (link) {
    link.addEventListener('click', cerrarNavbar);
  });

  // Submenú de "Revisión mensual": se abre solo si ya estamos en una de
  // esas dos páginas, para que el usuario no tenga que buscarlo.
  const submenuToggle = document.getElementById('mnt-submenu-toggle');
  const submenu = document.getElementById('mnt-submenu');
  const submenuIcon = document.getElementById('mnt-submenu-icon');

  if (submenuToggle && submenu) {
    if (window.location.pathname.indexOf('/mantencion/revision/') !== -1) {
      submenu.classList.add('mnt-submenu-open');
      submenuIcon.classList.add('rotate-180');
    }
    submenuToggle.addEventListener('click', function () {
      submenu.classList.toggle('mnt-submenu-open');
      submenuIcon.classList.toggle('rotate-180');
    });
  }

  // Modo oscuro del módulo: solo se activa si la persona lo pide con este
  // botón (nunca solo porque Windows/el navegador esté en oscuro; ver el
  // script inline en base_mantencion.html que evita el parpadeo). Se guarda
  // en localStorage, por navegador, igual patrón que usa el Debug Toolbar.
  const themeToggle = document.getElementById('mnt-theme-toggle');
  const themeIcon = document.getElementById('mnt-theme-icon');

  if (themeToggle && themeIcon) {
    function actualizarIconoTema() {
      const esOscuro = document.documentElement.classList.contains('dark');
      themeIcon.className = esOscuro ? 'fas fa-sun' : 'fas fa-moon';
      themeToggle.setAttribute('aria-label', esOscuro ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
    }

    actualizarIconoTema();

    themeToggle.addEventListener('click', function () {
      document.documentElement.classList.toggle('dark');
      const nuevoTema = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
      localStorage.setItem('mantencion-theme', nuevoTema);
      actualizarIconoTema();
    });
  }
});
