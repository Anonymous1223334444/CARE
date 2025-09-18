# messaging/services.py - Version Production

import requests
from django.conf import settings
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)

class SMSService:
    """Service pour envoyer des SMS via Twilio"""
    
    def __init__(self):
        self.client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        self.from_number = settings.TWILIO_SMS_NUMBER
    
    def send_activation_sms(self, patient):
        """Envoie un SMS d'activation au patient"""
        try:
            activation_url = f"{settings.SITE_PUBLIC_URL}/api/patients/activate/{patient.activation_token}/"
            
            if settings.WHATSAPP_MODE == 'production':
                # En production : message simple avec lien
                message = f"""Bonjour {patient.first_name},{activation_url}\n{settings.HEALTH_STRUCTURE_NAME}"""
            else:
                # En sandbox : message avec instructions
                message = f"""Bonjour {patient.first_name},{activation_url}\n{settings.HEALTH_STRUCTURE_NAME}"""
            
            sms = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=patient.phone
            )
            
            logger.info(f"SMS envoyé à {patient.phone}: {sms.sid}")
            return True, sms.sid
            
        except Exception as e:
            logger.error(f"Erreur envoi SMS à {patient.phone}: {e}")
            return False, str(e)

class WhatsAppService:
    """Service pour envoyer des messages WhatsApp via Twilio"""
    
    def __init__(self):
        self.client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        self.whatsapp_number = settings.TWILIO_WHATSAPP_NUMBER
        self.is_production = settings.WHATSAPP_MODE == 'production'
    
    def send_message(self, to_number: str, message: str, template: str = None) -> bool:
        """
        Envoyer un message WhatsApp
        En production, utilise les templates approuvés pour les messages initiés par l'entreprise
        """
        if not to_number.startswith('+'):
            to_number = f"+{to_number}"
        
        try:
            if self.is_production and template:
                # Utiliser un template approuvé
                message_data = self.client.messages.create(
                    from_=f'whatsapp:{self.whatsapp_number}',
                    to=f'whatsapp:{to_number}',
                    messaging_service_sid=settings.TWILIO_MESSAGING_SERVICE_SID,  # Si configuré
                    template=template
                )
            else:
                # Message libre (sandbox ou conversation active)
                message_data = self.client.messages.create(
                    from_=f'whatsapp:{self.whatsapp_number}',
                    to=f'whatsapp:{to_number}',
                    body=message
                )
            
            logger.info(f"Message WhatsApp envoyé à {to_number}: {message_data.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi WhatsApp à {to_number}: {e}")
            return False
    
    def send_template_message(self, to_number: str, template_name: str, parameters: list) -> bool:
        """
        Envoie un message basé sur un template approuvé (production uniquement)
        """
        if not self.is_production:
            logger.warning("Templates non disponibles en mode sandbox")
            return False
        
        template_sid = settings.WHATSAPP_TEMPLATES.get(template_name)
        if not template_sid:
            logger.error(f"Template '{template_name}' non configuré")
            return False
        
        try:
            message = self.client.messages.create(
                from_=f'whatsapp:{self.whatsapp_number}',
                to=f'whatsapp:{to_number}',
                template={
                    'sid': template_sid,
                    'parameters': parameters
                }
            )
            
            logger.info(f"Template '{template_name}' envoyé à {to_number}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi template: {e}")
            return False
    
    def send_activation_message(self, patient):
        """Envoie le message d'activation WhatsApp"""
        if self.is_production:
            # Utiliser le template approuvé
            return self.send_template_message(
                patient.phone,
                'activation',
                [patient.first_name, f"{settings.SITE_PUBLIC_URL}/api/patients/activate/{patient.activation_token}/"]
            )
        else:
            # En sandbox, envoyer après que l'utilisateur ait rejoint
            message = f"""✅ Bienvenue {patient.first_name} !

Pour activer votre espace santé, envoyez:
ACTIVER {patient.activation_token}

{settings.HEALTH_STRUCTURE_NAME}"""
            return self.send_message(patient.phone, message)
    
    def send_document_ready_notification(self, patient, document_name):
        """Notifie quand un document est prêt"""
        if self.is_production:
            return self.send_template_message(
                patient.phone,
                'document_ready',
                [patient.first_name, document_name]
            )
        else:
            message = f"""📄 {patient.first_name}, votre document "{document_name}" a été indexé avec succès.

Vous pouvez maintenant poser des questions sur vos documents."""
            return self.send_message(patient.phone, message)