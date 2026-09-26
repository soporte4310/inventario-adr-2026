// Mensajes del sistema (django.contrib.messages) como "toast" flotantes:
// se cierran solos a los 8 segundos, o antes con la X de cada uno.
document.addEventListener('DOMContentLoaded', function () {
  const DURACION_MS = 8000;

  document.querySelectorAll('.mnt-toast').forEach(function (toast) {
    let cerrado = false;

    function cerrar() {
      if (cerrado) return;
      cerrado = true;
      toast.remove();
    }

    const boton = toast.querySelector('.mnt-cerrar-toast');
    if (boton) boton.addEventListener('click', cerrar);

    setTimeout(cerrar, DURACION_MS);
  });
});
