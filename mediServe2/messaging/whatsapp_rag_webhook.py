# messaging/whatsapp_rag_webhook.py
# Webhook WhatsApp avec intégration RAG complète et logging amélioré

import os
import sys
import logging
import re
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from django.conf import settings
from django.utils import timezone
import json

def parse_rag_output(response_text: str):
    """
    Sépare la réponse principale des suggestions générées par l'IA.
    """
    main_answer = response_text
    suggestions = []
    
    if "---SUGGESTIONS---" in response_text:
        parts = response_text.split("---SUGGESTIONS---", 1)
        main_answer = parts[0].strip()
        
        # Regex pour trouver les suggestions numérotées (ex: 1. ..., 2. ...)
        suggestion_text = parts[1]
        suggestions = re.findall(r'^\d+\.\s*(.*)', suggestion_text, re.MULTILINE)
        
    return {
        "answer": main_answer,
        "suggestions": suggestions
    }

# Ajouter le chemin pour les scripts
sys.path.append(os.path.join(settings.BASE_DIR, 'scripts'))

from patients.models import Patient
from documents.models import DocumentUpload
from sessions.models import WhatsAppSession, ConversationLog
from messaging.utils import normalize_phone_number, phones_match

QUICK_REPLY_MAP = {
    "1": "Quels sont mes prochains rendez-vous ?",
    "2": "Donne moi des conseils santé au vu de mes antécédents médicaux ?",
    "3": "Quels médicaments dois-je prendre aujourd'hui ?",
}

logger = logging.getLogger(__name__)
@csrf_exempt
@require_POST
def whatsapp_rag_webhook(request):
    """Webhook WhatsApp avec RAG intégré"""
    import time
    start_time = time.time()
    # Logger toutes les données reçues pour debug
    logger.info("="*50)
    logger.info("📱 WEBHOOK TWILIO APPELÉ")
    logger.info(f"Method: {request.method}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"POST data: {dict(request.POST)}")
    logger.info(f"Body: {request.body.decode('utf-8', errors='ignore')[:500]}")  # Premiers 500 chars
    logger.info("="*50)
    
    # Créer la réponse TwiML vide dès le début (pour acknowledgment)
    resp = MessagingResponse()
    
    try:
        # 1. Extraire les données du message - Twilio envoie en POST form-encoded
        # IMPORTANT: Garder le format WhatsApp complet pour les réponses
        from_number = request.POST.get('From', '')  # Garde "whatsapp:+1234567890"
        to_number = request.POST.get('To', '')      # Garde "whatsapp:+1415238886"
        message_body = request.POST.get('Body', '').strip()
        logger.info(f"📱 Raw Body from Twilio: '{message_body}'")
        message_sid = request.POST.get('MessageSid', '')

        final_query = QUICK_REPLY_MAP.get(message_body, message_body)
        if final_query != message_body:
            logger.info(f"🔄 Quick reply detected. Translated '{message_body}' to '{final_query}'")
        
        # Pour les recherches dans la DB, on nettoie le numéro
        clean_from_number = from_number.replace('whatsapp:', '').replace(' ', '')
        
        logger.info(f"📱 From: {from_number} (clean: {clean_from_number})")
        logger.info(f"📱 To: {to_number}")
        logger.info(f"📱 Body: {message_body}")
        logger.info(f"📱 MessageSid: {message_sid}")
        
        # Initialize Twilio client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # 3. Traiter le message d'activation
        if message_body.upper().startswith('ACTIVER '):
            logger.info("🔑 Message d'activation détecté")
            response_text = handle_activation(clean_from_number, message_body)
            cleaned_response = response_text.strip()[:1024]
            
            # Send activation response with Quick Reply
            logger.info("🛠️ Sending activation response with Quick Reply")
            try:
                client.messages.create(
                    from_=to_number,  # Utilise le "To" reçu (format WhatsApp complet)
                    to=from_number,   # Utilise le "From" reçu (format WhatsApp complet)
                    content_sid='HX14ddb3d223d516023b8432428f9ff88c',  # Your Quick Reply Content SID
                    content_variables=json.dumps({
                        'message': response_text,
                        # Ajoute d'autres variables si ton template en a besoin
                    })
                )
                logger.info("✅ Réponse d'activation avec Quick Reply envoyée")
            except Exception as e:
                logger.error(f"❌ Erreur Quick Reply activation, fallback vers message simple: {e}")
                # Fallback vers message simple si Quick Reply échoue
                client.messages.create(
                    from_=to_number,
                    to=from_number,
                    body=response_text
                )
                logger.info("✅ Réponse d'activation simple envoyée")
            
            return HttpResponse(str(resp), content_type='text/xml')
        
        # 4. Vérifier que le patient existe et est actif
        try:
            # Normaliser le numéro d'abord
            normalized_from = normalize_phone_number(clean_from_number)
            logger.info(f"🔍 Recherche du patient avec numéro normalisé: {normalized_from}")
            
            # Recherche flexible du patient
            patient = None
            
            # 1. Recherche exacte
            try:
                patient = Patient.objects.get(phone=normalized_from)
                logger.info(f"✅ Patient trouvé par recherche exacte")
            except Patient.DoesNotExist:
                # 2. Recherche avec comparaison flexible
                all_patients = Patient.objects.all()
                for p in all_patients:
                    if phones_match(p.phone, clean_from_number):
                        patient = p
                        logger.info(f"✅ Patient trouvé par comparaison flexible: {p.phone} ≈ {clean_from_number}")
                        break
            
            if not patient:
                raise Patient.DoesNotExist()
            
            logger.info(f"👤 Patient trouvé: {patient.full_name()} (ID: {patient.id})")
            
            if not patient.is_active:
                logger.warning(f"⚠️ Patient non actif: {patient.id}")
                # Send inactive message with Quick Reply
                try:
                    client.messages.create(
                        from_=to_number,
                        to=from_number,
                        content_sid='HX14ddb3d223d516023b8432428f9ff88c',
                        content_variables=json.dumps({
                            'message': f"❌ Veuillez d'abord activer votre compte.\n\nEnvoyez : ACTIVER {patient.activation_token}"
                        })
                    )
                    logger.info("✅ Message d'inactivité avec Quick Reply envoyé")
                except Exception as e:
                    logger.error(f"❌ Erreur Quick Reply inactivité, fallback: {e}")
                    client.messages.create(
                        from_=to_number,
                        to=from_number,
                        body=f"❌ Veuillez d'abord activer votre compte.\n\nEnvoyez : ACTIVER {patient.activation_token}"
                    )
                    logger.info("✅ Message d'inactivité simple envoyé")
                
                return HttpResponse(str(resp), content_type='text/xml')
            
        except Patient.DoesNotExist:
            logger.error(f"❌ Patient non trouvé pour le numéro: {clean_from_number} (normalisé: {normalized_from})")
            
            # Logger tous les numéros de patients pour debug
            logger.debug("📱 Numéros de patients dans la DB:")
            for p in Patient.objects.all()[:10]:  # Limiter à 10 pour les logs
                logger.debug(f"  - {p.phone} ({p.full_name()})")
            
            # Send not recognized message with Quick Reply
            try:
                client.messages.create(
                    from_=to_number,
                    to=from_number,
                    content_sid='HX14ddb3d223d516023b8432428f9ff88c',
                    content_variables=json.dumps({
                        'message': "❌ Numéro non reconnu. Veuillez contacter votre médecin pour vous inscrire."
                    })
                )
                logger.info("✅ Message 'non reconnu' avec Quick Reply envoyé")
            except Exception as e:
                logger.error(f"❌ Erreur Quick Reply 'non reconnu', fallback: {e}")
                client.messages.create(
                    from_=to_number,
                    to=from_number,
                    body="❌ Numéro non reconnu. Veuillez contacter votre médecin pour vous inscrire."
                )
                logger.info("✅ Message 'non reconnu' simple envoyé")
            
            return HttpResponse(str(resp), content_type='text/xml')
        
        # 5. Créer ou récupérer la session WhatsApp
        session, created = WhatsAppSession.objects.get_or_create(
            patient=patient,
            phone_number=clean_from_number,  # Utilise le numéro nettoyé pour la DB
            defaults={
                'session_id': f'wa_{patient.id}_{message_sid[:8]}',
                'status': 'active'
            }
        )
        
        # Mettre à jour la dernière activité
        session.last_activity = timezone.now()
        session.save()
        
        logger.info(f"💬 Session {'créée' if created else 'récupérée'}: {session.session_id}")
        
        # 6. Utiliser le RAG pour générer la réponse
        try:
            rag_result = process_with_rag(patient, final_query, session)
        
            main_answer = rag_result.get('answer', "Désolé, je n'ai pas de réponse pour le moment.")
            suggestions = rag_result.get('suggestions', [])

            response_text = main_answer

            if suggestions:
                suggestion_lines = "\n".join([f"➡️ {s.strip()}" for s in suggestions])
                response_text += f"\n\nVous pourriez aussi demander :\n{suggestion_lines}"
                
            # 7. Enregistrer la conversation
            response_time_ms = (time.time() - start_time) * 1000
            ConversationLog.objects.create(
                session=session,
                user_message=message_body,
                ai_response=response_text,
                response_time_ms=int(response_time_ms),
                message_length=len(message_body),
                response_length=len(response_text)
            )
            
            logger.info(f"✅ Réponse générée en {response_time_ms:.0f}ms")
            
        except Exception as e:
            logger.error(f"❌ Erreur RAG pour patient {patient.id}: {e}", exc_info=True)
            response_text = (
                "😔 Désolé, je n'ai pas pu traiter votre demande pour le moment.\n\n"
                "Vous pouvez:\n"
                "• Reformuler votre question\n"
                "• Contacter votre médecin directement\n"
                "• Réessayer dans quelques instants"
            )
        
        # 8. Envoyer la réponse avec debugging complet
        try:
            logger.info("🛠️ Sending RAG response with Quick Reply")
            
            # Log detailed info for debugging
            logger.info(f"📤 Message details:")
            logger.info(f"   From: {to_number}")
            logger.info(f"   To: {from_number}")
            logger.info(f"   Content SID: HX14ddb3d223d516023b8432428f9ff88c")
            logger.info(f"   Response length: {len(response_text)} chars")
            
            # Try Quick Reply first
            message = client.messages.create(
                from_=to_number,
                to=from_number,
                content_sid='HX14ddb3d223d516023b8432428f9ff88c',
                content_variables=json.dumps({
                    'message': response_text[:1000]  # Limit to 1000 chars for templates
                })
            )
            
            # LOG THE MESSAGE SID AND STATUS
            logger.info(f"✅ Message created - SID: {message.sid}")
            logger.info(f"✅ Message status: {message.status}")
            logger.info(f"✅ Message direction: {message.direction}")
            
            # Check message status after a moment
            import time
            time.sleep(2)  # Wait 2 seconds
            
            # Fetch updated message status
            try:
                updated_message = client.messages(message.sid).fetch()
                logger.info(f"📊 Updated message status: {updated_message.status}")
                logger.info(f"📊 Error code: {updated_message.error_code}")
                logger.info(f"📊 Error message: {updated_message.error_message}")
            except Exception as status_error:
                logger.error(f"❌ Couldn't fetch message status: {status_error}")
            
            logger.info("✅ Réponse RAG avec Quick Reply envoyée")
            
        except Exception as e:
            logger.error(f"❌ Erreur Quick Reply RAG: {e}")
            logger.error(f"❌ Error details: {str(e)}")
            
            # Fallback vers message simple avec contenu nettoyé
            try:
                logger.info("🔄 Trying simple message fallback")
                
                # Use the same cleaned content for simple message
                fallback_message = client.messages.create(
                    from_=to_number,
                    to=from_number,
                    body=cleaned_response
                )
                
                logger.info(f"✅ Fallback message - SID: {fallback_message.sid}")
                logger.info(f"✅ Fallback status: {fallback_message.status}")
                
                # Check fallback status too
                time.sleep(2)
                try:
                    updated_fallback = client.messages(fallback_message.sid).fetch()
                    logger.info(f"📊 Fallback updated status: {updated_fallback.status}")
                    logger.info(f"📊 Fallback error code: {updated_fallback.error_code}")
                except Exception as fallback_status_error:
                    logger.error(f"❌ Couldn't fetch fallback status: {fallback_status_error}")
                
                logger.info("✅ Réponse RAG simple envoyée")
                
            except Exception as e2:
                logger.error(f"❌ Erreur également avec message simple: {e2}")
                logger.error(f"❌ Simple message error details: {str(e2)}")
                
                # Last fallback - use TwiML response
                resp.message("⚠️ Erreur technique, veuillez réessayer.")
                logger.info("⚠️ Using TwiML fallback response")
        
        return HttpResponse(str(resp), content_type='text/xml')
        
    except Exception as e:
        logger.error(f"❌ Erreur webhook: {e}", exc_info=True)
        resp.message("⚠️ Une erreur technique s'est produite. Veuillez réessayer.")
        return HttpResponse(str(resp), content_type='text/xml')
    
def handle_activation(from_number, message_body):
    """Gère l'activation du patient"""
    try:
        logger.info(f"🔑 Traitement activation pour {from_number}")
        
        # Extraire le token - plus flexible
        # Le token peut être après "ACTIVER " ou juste le UUID
        parts = message_body.split()
        token = None
        
        # Chercher un UUID dans le message
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        matches = re.findall(uuid_pattern, message_body, re.IGNORECASE)
        
        if matches:
            token = matches[0]
            logger.info(f"🔑 Token extrait: {token}")
        else:
            logger.error("❌ Aucun token UUID trouvé dans le message")
            return "❌ Format invalide. Copiez le message complet depuis votre SMS."
        
        # Rechercher le patient par token
        patient = Patient.objects.get(activation_token=token)
        logger.info(f"👤 Patient trouvé par token: {patient.full_name()}")
        
        # Vérifier que le numéro correspond
        if not phones_match(patient.phone, from_number):
            logger.error(f"❌ Numéro non correspondant. Patient: {patient.phone}, From: {from_number}")
            return "❌ Ce lien d'activation ne correspond pas à votre numéro."
        
        if patient.is_active:
            logger.info("✅ Patient déjà actif")
            return f"✅ {patient.first_name}, votre compte est déjà activé ! Comment puis-je vous aider ?"
        
        # Activer le patient
        patient.is_active = True
        patient.activated_at = timezone.now()
        patient.save()
        logger.info(f"✅ Patient activé: {patient.id}")
        
        # Vérifier les documents
        doc_count = DocumentUpload.objects.filter(
            patient=patient, 
            upload_status='indexed'
        ).count()
        
        return f"""✅ Bienvenue {patient.first_name} !

Votre espace santé {settings.HEALTH_STRUCTURE_NAME} est maintenant actif.

{'📄 ' + str(doc_count) + ' document(s) médical(aux) disponible(s)' if doc_count > 0 else '📭 Aucun document pour le moment'}

Je suis votre assistant médical personnel. Je peux vous aider avec :
• 📋 Vos documents médicaux
• 💊 Vos traitements et posologies
• 🔬 Vos résultats d'examens
• ❓ Toute question sur votre santé

Comment puis-je vous aider aujourd'hui ?"""
        
    except Patient.DoesNotExist:
        logger.error(f"❌ Patient non trouvé pour token: {token}")
        return "❌ Token d'activation invalide. Veuillez vérifier votre SMS."
    except Exception as e:
        logger.error(f"❌ Erreur activation: {e}", exc_info=True)
        return "❌ Erreur lors de l'activation. Veuillez contacter le support."


def process_with_rag(patient, query, session):
    """Traite la question avec le système RAG en incluant l'historique de conversation."""
    try:
        logger.info(f"🤖 Traitement RAG pour patient {patient.id} - {patient.full_name()}")
        logger.info(f"📝 Question: {query}")

        # --- Ajout de la mémoire de conversation ---
        history_logs = ConversationLog.objects.filter(session=session).order_by('-timestamp')[:20]
        
        conversation_history = ""
        if history_logs:
            history_list = []
            # Inverser pour avoir l'ordre chronologique
            for log in reversed(history_logs):
                history_list.append(f"Patient: {log.user_message}")
                history_list.append(f"Assistant: {log.ai_response}")
            conversation_history = "\n".join(history_list)
            logger.info(f"🧠 Historique de conversation injecté:\n{conversation_history}")

        # Détecter si c'est le début de la conversation pour la salutation
        is_new_conversation = not history_logs.exists()
        greeting = f"👋 Bonjour {patient.first_name} ! " if is_new_conversation else ""
        # --- Fin de l'ajout de la mémoire ---

        # Vérifier d'abord les documents indexés
        indexed_docs = DocumentUpload.objects.filter(
            patient=patient,
            upload_status='indexed'
        )
        logger.info(f"📚 Documents indexés pour ce patient: {indexed_docs.count()}")
        
        # Importer les modules RAG
        from rag.your_rag_module import (
            VectorStoreHDF5, EmbeddingGenerator, 
            HybridRetriever, GeminiLLM, RAG
        )
        
        # Chemins des fichiers pour ce patient
        vector_dir = os.path.join(settings.MEDIA_ROOT, 'vectors', f'patient_{patient.id}')
        hdf5_path = os.path.join(vector_dir, 'vector_store.h5')
        bm25_dir = os.path.join(settings.MEDIA_ROOT, 'indexes', f'patient_{patient.id}_bm25')
        
        if not os.path.exists(hdf5_path):
            logger.warning(f"⚠️ Pas de vector store pour patient {patient.id}")
            if indexed_docs.count() > 0:
                return "⚠️ Vos documents sont en cours de traitement. Veuillez réessayer dans quelques instants."
            return fallback_response(patient, query)
        
        # Initialisation des composants RAG
        vector_store = VectorStoreHDF5(hdf5_path)
        vector_store.load_store()
        embedder = EmbeddingGenerator(settings.RAG_SETTINGS.get('EMBEDDING_MODEL', 'all-mpnet-base-v2'))
        
        if os.path.exists(bm25_dir) and settings.RAG_SETTINGS.get('USE_BM25', True):
            retriever = HybridRetriever(vector_store, embedder, bm25_dir)
            if settings.RAG_SETTINGS.get('USE_RERANKING', False):
                reranker_model = settings.RAG_SETTINGS.get('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
                retriever.enable_reranking(reranker_model)
        else:
            retriever = HybridRetriever(vector_store, embedder)
            
        llm = GeminiLLM(model_name=settings.RAG_SETTINGS.get('LLM_MODEL', 'gemini-1.5-flash-latest'))
        rag = RAG(retriever, llm)
        
        # Personnaliser le prompt pour WhatsApp avec mémoire
        enhanced_query = f"""
            # CONTEXTE (informations provenant du dossier médical du patient)
            - Nom: {patient.first_name} {patient.last_name}
            - Sexe: {patient.gender or 'Non spécifié'}
            - Antécédents: {patient.medical_history or 'Aucun'}
            - Allergies: {patient.allergies or 'Aucune'}
            - Médicaments: {patient.current_medications or 'Aucun'}

            # HISTORIQUE DE LA CONVERSATION
            {conversation_history}

            # NOUVELLE QUESTION DU PATIENT
            Patient: {query}

            # DIRECTIVES STRICTES POUR L'ASSISTANT MÉDICAL

            ## 1. Persona et Source des Données (Point 4)
            - Tu es un assistant médical IA travaillant pour le médecin du patient.
            - Toutes les informations du CONTEXTE proviennent du dossier médical du patient.
            - Adresse-toi au patient en utilisant des expressions comme "Dans votre dossier, je vois que..." ou "D'après les informations fournies par votre médecin...".
            - Ne révèle ta nature d'IA ou la source des documents que si on te le demande explicitement.
            - Tu doits te comporter comme un assistant médical, pas comme un chatbot généraliste.
            - Réponds en francais, en utilisant un langage simple et accessible.
            - **Rôle sur les maladies chroniques** : Pour les conditions mentionnées dans le dossier (asthme, diabète, etc.), ton rôle est de :
                1. Fournir des informations générales et des conseils de vie (ex: alimentation, exercice) validés.
                2. Expliquer les informations déjà présentes dans le dossier (ex: "Votre dossier mentionne que vous suivez un traitement pour l'hypertension.").
                3. NE JAMAIS poser un nouveau diagnostic, suggérer un changement de traitement ou modifier une posologie. Renvoie TOUJOURS ces questions vers le médecin traitant.

            ## 2. Ton, Style et Longueur (Point 3)
            - **Ton** : Adopte un ton direct, concis et informel ("casual"). Sois rassurant et efficace.
            - **Humour** : N'utilise l'humour que s'il est très pertinent et léger. Dans le doute, abstiens-toi.
            - **Longueur** : Tes réponses doivent être brèves et aller droit au but. Limite-toi à 3-4 phrases maximum, sauf si une liste à puces est nécessaire pour la clarté.
            - **Emojis** : Utilise des emojis avec parcimonie pour appuyer le message (ex: 💊, ✅, 📅), sans surcharger.

            ## 3. Logique de Conversation (Point 1)
            - La salutation initiale est "{greeting}". N'ajoute pas d'autre salutation.
            - Plonge directement dans le vif du sujet pour répondre à la "NOUVELLE QUESTION DU PATIENT".
            - Utilise l'historique pour comprendre le contexte et ne jamais poser une question à laquelle la réponse a déjà été donnée.

            ## 4. Capacités Proactives (Point 5)
            - **Conseils** : Si pertinent, donne des conseils de santé basés sur le dossier médical. (Ex: si le patient parle de fatigue et a des antécédents de carence en fer, suggère d'en discuter avec son médecin).
            - **Comportements** : Suggère des habitudes saines en lien avec la question. (Ex: s'il parle de maux de tête, tu peux suggérer de penser à bien s'hydrater).
            - **Rappels** : Si la conversation mentionne une prise de médicament ou un rendez-vous, propose CLAIREMENT de créer un rappel. (Ex: "Voulez-vous que je configure un rappel pour votre prise de [médicament] ?").

            ## 5. Avertissement de Sécurité
            - Termine TOUJOURS tes réponses par un avertissement concis si un conseil est donné, comme : "N'oubliez pas que ceci est un conseil et ne remplace pas une consultation médicale." ou "Pour toute décision importante, parlez-en à votre médecin.". Adapte la phrase au contexte pour qu'elle soit naturelle.

            ## 6. Génération de Suggestions Proactives
            - Après avoir fourni ta réponse principale, saute une ligne et ajoute le marqueur "---SUGGESTIONS---".
            - Sous ce marqueur, génère TROIS questions de suivi courtes et pertinentes que le patient pourrait logiquement poser ensuite.
            - Chaque suggestion doit commencer par un numéro suivi d'un point (ex: "1. ...", "2. ...", "3. ...").
            - Ces suggestions doivent être des questions complètes et concises.

            Assistant: {greeting}"""
        
        logger.info(f"💭 Génération de la réponse RAG avec mémoire")
        response = rag.answer(enhanced_query, top_k=3)

        structured_response = parse_rag_output(response)

        structured_response['answer'] = post_process_response(structured_response['answer'], patient)
        
        # response = post_process_response(response, patient)
        
        logger.info("✅ Réponse RAG structurée générée avec succès")
        return structured_response
        
    except Exception as e:
        logger.error(f"❌ Erreur RAG: {e}", exc_info=True)
        return fallback_response(patient, query)


def fallback_response(patient, query):
    """Réponse de secours quand le RAG échoue"""
    query_lower = query.lower()
    
    # Réponses basées sur des mots-clés
    if any(word in query_lower for word in ['bonjour', 'salut', 'hello', 'bonsoir']):
        return f"👋 Bonjour {patient.first_name} ! Comment allez-vous aujourd'hui ?"
    
    elif any(word in query_lower for word in ['document', 'fichier', 'dossier']):
        docs = DocumentUpload.objects.filter(patient=patient, upload_status='indexed')
        if docs.exists():
            doc_list = '\n'.join([f"• {doc.original_filename}" for doc in docs[:5]])
            return f"📄 Vos documents disponibles :\n{doc_list}\n\nQue souhaitez-vous savoir ?"
        else:
            return "📭 Aucun document trouvé dans votre dossier. Contactez votre médecin pour les ajouter."
    
    elif any(word in query_lower for word in ['aide', 'help', 'comment', 'quoi']):
        return f"""🤝 Je peux vous aider avec :
        
• 📋 Consulter vos documents médicaux
• 💊 Informations sur vos médicaments
• 🔬 Comprendre vos résultats d'examens
• 📅 Rappels de rendez-vous
• ❓ Répondre à vos questions de santé

Posez-moi votre question !"""
    
    else:
        return f"""🤔 Je n'ai pas trouvé d'information spécifique sur : \"{query}\"\n
Essayez de reformuler ou demandez par exemple :
• \"Quels sont mes derniers résultats ?\"
• \"Quelle est ma posologie actuelle ?\"
• \"Résume mon dernier rapport médical\"

Pour une assistance urgente, contactez votre médecin."""


def post_process_response(response, patient):
    """Post-traite la réponse du RAG pour WhatsApp"""
    # Limiter la longueur
    if len(response) > 1000:
        response = response[:997] + "..."
    
    # S'assurer que la réponse n'est pas vide
    if not response or response.strip() == "":
        response = "Je n'ai pas pu générer une réponse. Veuillez reformuler votre question."
    
    # Nettoyer toute mention de "Réponse générée pour..."
    response = re.sub(r'_💡 Réponse générée pour.*_', '', response, flags=re.IGNORECASE).strip()
    
    return response