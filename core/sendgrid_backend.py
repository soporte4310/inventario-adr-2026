"""
Backend de email personalizado para Django que usa la API HTTP de SendGrid.

Render bloquea conexiones SMTP salientes (puerto 587), por lo que el backend
SMTP estándar de Django no funciona en producción. Este backend reemplaza
el envío SMTP por llamadas HTTP a la API de SendGrid.

Se usa automáticamente cuando EMAIL_BACKEND apunta a este módulo.
"""
import logging
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class SendGridHTTPBackend(BaseEmailBackend):
    """
    Backend de email que envía correos usando la API HTTP de SendGrid
    en lugar de SMTP. Compatible con todas las funciones de Django
    que usan django.core.mail (incluyendo PasswordResetView).
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        from decouple import config
        self.api_key = config('SENDGRID_API_KEY', default='')

    def send_messages(self, email_messages):
        """Envía uno o más mensajes usando SendGrid HTTP API."""
        if not self.api_key:
            logger.error("SENDGRID_API_KEY no está configurada")
            if not self.fail_silently:
                raise Exception("SENDGRID_API_KEY no está configurada")
            return 0

        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, To

        sg = SendGridAPIClient(self.api_key)
        sent_count = 0

        for message in email_messages:
            try:
                from_email = message.from_email or getattr(
                    settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'
                )

                # Construir lista de destinatarios
                to_emails = [To(email) for email in message.to]

                html_content = None
                if message.alternatives:
                    for content, mimetype in message.alternatives:
                        if mimetype == 'text/html':
                            html_content = content

                # Crear el mensaje de SendGrid
                sg_mail = Mail(
                    from_email=from_email,
                    to_emails=to_emails,
                    subject=message.subject,
                    plain_text_content=message.body,
                    html_content=html_content,
                )

                # Enviar
                response = sg.send(sg_mail)

                if response.status_code in (200, 201, 202):
                    sent_count += 1
                    logger.info(
                        f"✅ Email enviado: '{message.subject}' -> {message.to}"
                    )
                else:
                    logger.error(
                        f"❌ SendGrid error {response.status_code}: {response.body}"
                    )
                    if not self.fail_silently:
                        raise Exception(
                            f"SendGrid error: {response.status_code}"
                        )

            except Exception as e:
                logger.error(f"❌ Error enviando email: {e}")
                if not self.fail_silently:
                    raise

        return sent_count
