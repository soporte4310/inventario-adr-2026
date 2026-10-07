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
  const modalDeBaja = document.getElementById('mnt-modal-de-baja');
  const abrirDeBaja = document.getElementById('mnt-abrir-de-baja');

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

  if (modalDeBaja && abrirDeBaja) {
    abrirDeBaja.addEventListener('click', function () {
      modalDeBaja.classList.remove('hidden');
    });
  }

  // Botón "Tomar fotografía" (en realidad una <label> que dispara el input
  // de archivo oculto): como el input real ya no se ve, mostramos acá el
  // nombre del archivo elegido y una vista previa, para que quede claro qué
  // se seleccionó y se pueda volver a tomar otra si no convence (el input
  // solo guarda un archivo a la vez, así que la nueva selección reemplaza
  // sola a la anterior).
  const inputArchivo = document.getElementById('id_archivo');
  const nombreArchivo = document.querySelector('.mnt-archivo-nombre');
  const previewArchivo = document.querySelector('.mnt-archivo-preview');
  if (inputArchivo && nombreArchivo) {
    inputArchivo.addEventListener('change', function () {
      const archivo = inputArchivo.files[0];
      nombreArchivo.textContent = archivo ? archivo.name : '';
      if (previewArchivo) {
        if (archivo) {
          previewArchivo.src = URL.createObjectURL(archivo);
          previewArchivo.classList.remove('hidden');
        } else {
          previewArchivo.classList.add('hidden');
        }
      }
    });
  }

  // Evita que un doble clic/doble tap en "Guardar novedad" mande el
  // formulario dos veces (y suba la misma evidencia duplicada): se
  // deshabilita apenas se envía, la propia recarga de la página al volver
  // (éxito o error) deja el botón fresco de nuevo.
  if (formNovedad) {
    formNovedad.addEventListener('submit', function () {
      const boton = formNovedad.querySelector('.mnt-submit-novedad');
      if (boton) {
        boton.disabled = true;
        boton.textContent = 'Guardando...';
      }
    });
  }

  // Botón "Info" en Lista de proyectores/impresoras: un modal propio por
  // equipo (ver lista_equipos.html), identificado por su id en data-modal.
  document.querySelectorAll('.mnt-abrir-info').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const modal = document.getElementById(btn.dataset.modal);
      if (modal) modal.classList.remove('hidden');
    });
  });

  // "Automático (DHCP)" en el modal de agregar impresora: deshabilita el
  // campo IP mientras esté marcado (el valor igual se limpia en el server,
  // esto es sólo para que no se vea editable si ya no aplica).
  const checkDhcp = document.querySelector('.mnt-check-dhcp');
  const inputIp = document.getElementById('id_ip');
  if (checkDhcp && inputIp) {
    const sincronizarIp = function () {
      inputIp.disabled = checkDhcp.checked;
      if (checkDhcp.checked) inputIp.value = '';
    };
    checkDhcp.addEventListener('change', sincronizarIp);
    sincronizarIp();
  }

  document.querySelectorAll('.mnt-cerrar-modal').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (modalNovedad) modalNovedad.classList.add('hidden');
      if (modalEnroque) modalEnroque.classList.add('hidden');
      if (modalFoto) modalFoto.classList.add('hidden');
      if (modalImpresoras) modalImpresoras.classList.add('hidden');
      if (modalDeBaja) modalDeBaja.classList.add('hidden');
      document.querySelectorAll('.mnt-modal-info').forEach(function (modal) {
        modal.classList.add('hidden');
      });
    });
  });
});
