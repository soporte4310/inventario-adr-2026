// Lógica compartida de los modales de Mantención: "Observación" (comentario
// + evidencia, en Revisión mensual) y "Mover de sala" (enroque, en las
// Listas de proyectores/impresoras). Cada página sólo trae los elementos
// que realmente usa, así que todo se busca de forma defensiva (puede no
// existir en la página actual).
document.addEventListener('DOMContentLoaded', function () {
  const modalNovedad = document.getElementById('mnt-modal-novedad');
  const formNovedad = document.getElementById('mnt-form-novedad');
  const modalEnroque = document.getElementById('mnt-modal-enroque');
  const formEnroque = document.getElementById('mnt-form-enroque');
  const modalFoto = document.getElementById('mnt-modal-foto');
  const fotoImagen = document.getElementById('mnt-foto-imagen');
  const fotoTitulo = document.getElementById('mnt-foto-titulo');
  const fotoComentario = document.getElementById('mnt-foto-comentario');
  const modalImpresoras = document.getElementById('mnt-modal-impresoras');
  const abrirImpresoras = document.getElementById('mnt-abrir-gestionar-impresoras');

  if (modalNovedad && formNovedad) {
    document.querySelectorAll('.mnt-abrir-novedad').forEach(function (btn) {
      btn.addEventListener('click', function () {
        // El botón trae la url con un '0' de relleno (generado con
        // {% url %} en la plantilla); acá lo reemplazamos por el id real.
        formNovedad.action = btn.dataset.urlTemplate.replace('/0/', '/' + btn.dataset.revision + '/');
        modalNovedad.classList.remove('hidden');
      });
    });
  }

  if (modalEnroque && formEnroque) {
    document.querySelectorAll('.mnt-abrir-enroque').forEach(function (btn) {
      btn.addEventListener('click', function () {
        formEnroque.action = btn.dataset.urlTemplate.replace('/0/', '/' + btn.dataset.equipo + '/');
        modalEnroque.classList.remove('hidden');
      });
    });
  }

  if (modalFoto && fotoImagen) {
    document.querySelectorAll('.mnt-ver-foto').forEach(function (btn) {
      btn.addEventListener('click', function () {
        fotoImagen.src = btn.dataset.foto;
        if (fotoTitulo) fotoTitulo.textContent = btn.dataset.equipo || 'Evidencia';
        if (fotoComentario) fotoComentario.textContent = btn.dataset.comentario || '';
        modalFoto.classList.remove('hidden');
      });
    });
  }

  if (modalImpresoras && abrirImpresoras) {
    abrirImpresoras.addEventListener('click', function () {
      modalImpresoras.classList.remove('hidden');
    });
  }

  document.querySelectorAll('.mnt-cerrar-modal').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (modalNovedad) modalNovedad.classList.add('hidden');
      if (modalEnroque) modalEnroque.classList.add('hidden');
      if (modalFoto) modalFoto.classList.add('hidden');
      if (modalImpresoras) modalImpresoras.classList.add('hidden');
    });
  });
});
