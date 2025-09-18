#!/usr/bin/env python3
"""
Script pour préparer la migration de WhatsApp Sandbox vers Production
Usage: python migrate_to_production.py
"""
import os
import sys
import django

script_dir = os.path.dirname(os.path.abspath(__file__))
# Aller deux niveaux plus haut pour atteindre le répertoire racine du projet Django
# (Exemple: si script est dans /project_root/scripts/, cela renvoie /project_root/)
project_root = os.path.join(script_dir, '..', '') # Ajout d'un '/' final pour s'assurer que c'est un chemin de répertoire
sys.path.insert(0, os.path.abspath(project_root))
# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mediServe.settings')
django.setup()

from django.conf import settings
from patients.models import Patient
from termcolor import colored

def check_production_readiness():
    """Vérifie si le système est prêt pour la production"""
    print(colored("=== VÉRIFICATION PRODUCTION READINESS ===\n", 'cyan', attrs=['bold']))
    
    checks = []
    
    # 1. Vérifier la configuration
    print(colored("1. Configuration", 'yellow'))
    
    # Mode actuel
    current_mode = getattr(settings, 'WHATSAPP_MODE', 'sandbox')
    checks.append({
        'name': 'Mode WhatsApp',
        'status': current_mode,
        'ok': True,
        'note': f"Actuellement en mode: {current_mode}"
    })
    
    # Numéro WhatsApp Production
    prod_number = os.getenv('TWILIO_WHATSAPP_NUMBER_PROD', '')
    checks.append({
        'name': 'Numéro WhatsApp Production',
        'status': 'Configuré' if prod_number else 'Non configuré',
        'ok': bool(prod_number),
        'note': prod_number if prod_number else 'TWILIO_WHATSAPP_NUMBER_PROD manquant dans .env'
    })
    
    # Templates
    print(colored("\n2. Templates WhatsApp", 'yellow'))
    templates = getattr(settings, 'WHATSAPP_TEMPLATES', {})
    for template_name, template_sid in templates.items():
        checks.append({
            'name': f'Template {template_name}',
            'status': 'Configuré' if template_sid else 'Manquant',
            'ok': bool(template_sid) and template_sid != f'{template_name}_template',
            'note': template_sid if template_sid else 'Template SID requis'
        })
    
    # 3. Patients
    print(colored("\n3. Données patients", 'yellow'))
    total_patients = Patient.objects.count()
    active_patients = Patient.objects.filter(is_active=True).count()
    
    checks.append({
        'name': 'Patients totaux',
        'status': str(total_patients),
        'ok': True,
        'note': f"{active_patients} actifs"
    })
    
    # 4. Vérifier les numéros de téléphone
    print(colored("\n4. Format des numéros", 'yellow'))
    invalid_phones = []
    for patient in Patient.objects.all():
        if not patient.phone.startswith('+'):
            invalid_phones.append(patient)
    
    checks.append({
        'name': 'Numéros au format E.164',
        'status': 'OK' if not invalid_phones else f'{len(invalid_phones)} invalides',
        'ok': not bool(invalid_phones),
        'note': 'Tous les numéros doivent commencer par +'
    })
    
    # 5. SSL/HTTPS
    print(colored("\n5. Sécurité", 'yellow'))
    site_url = getattr(settings, 'SITE_PUBLIC_URL', '')
    checks.append({
        'name': 'URL HTTPS',
        'status': 'OK' if site_url.startswith('https://') else 'Non sécurisé',
        'ok': site_url.startswith('https://'),
        'note': site_url
    })
    
    # Afficher les résultats
    print(colored("\n=== RÉSUMÉ ===", 'cyan', attrs=['bold']))
    all_ok = True
    
    for check in checks:
        if check['ok']:
            status = colored('✅', 'green')
        else:
            status = colored('❌', 'red')
            all_ok = False
        
        print(f"{status} {check['name']}: {check['status']}")
        if check['note'] and not check['ok']:
            print(f"   → {colored(check['note'], 'yellow')}")
    
    # Recommandations
    if all_ok:
        print(colored("\n✅ Système prêt pour la production!", 'green', attrs=['bold']))
    else:
        print(colored("\n⚠️ Des corrections sont nécessaires avant la production", 'yellow', attrs=['bold']))
    
    return all_ok

def generate_migration_checklist():
    """Génère une checklist de migration"""
    print(colored("\n=== CHECKLIST DE MIGRATION ===", 'cyan', attrs=['bold']))
    
    checklist = """
    □ 1. Compte Twilio
        □ Compte vérifié avec facturation activée
        □ Solde suffisant pour les messages
        
    □ 2. WhatsApp Business
        □ Profil Facebook Business Manager créé
        □ Demande WhatsApp Business soumise à Twilio
        □ Profil d'entreprise approuvé par Meta
        
    □ 3. Numéro de téléphone
        □ Numéro dédié pour WhatsApp (différent du SMS)
        □ Numéro vérifié et approuvé par Meta
        
    □ 4. Templates de messages
        □ Template d'activation créé et approuvé
        □ Template de notification document créé
        □ Templates additionnels si nécessaire
        
    □ 5. Configuration technique
        □ Fichier .env mis à jour avec WHATSAPP_MODE=production
        □ Numéro de production configuré
        □ Templates SIDs ajoutés
        □ SSL/HTTPS configuré
        
    □ 6. Tests
        □ Test d'envoi de template
        □ Test de réception de message
        □ Test du webhook en production
        
    □ 7. Migration des données
        □ Backup de la base de données
        □ Nettoyage des sessions sandbox
        □ Information des patients actifs
    """
    
    print(checklist)
    
    # Générer un fichier
    with open('migration_checklist.txt', 'w') as f:
        f.write(checklist)
    print(colored("\n📄 Checklist sauvegardée dans: migration_checklist.txt", 'green'))

def simulate_production():
    """Simule l'envoi de messages en mode production"""
    print(colored("\n=== SIMULATION MODE PRODUCTION ===", 'cyan', attrs=['bold']))
    
    # Prendre un patient de test
    test_patient = Patient.objects.filter(is_active=True).first()
    if not test_patient:
        print(colored("❌ Aucun patient actif pour le test", 'red'))
        return
    
    print(f"\n📱 Patient test: {test_patient.full_name()} ({test_patient.phone})")
    
    # Simuler l'envoi de templates
    from messaging.services import WhatsAppService
    
    # Temporairement forcer le mode production
    original_mode = settings.WHATSAPP_MODE
    settings.WHATSAPP_MODE = 'production'
    
    try:
        service = WhatsAppService()
        
        print("\n1. Test template activation:")
        print(f"   → Template: activation")
        print(f"   → Paramètres: ['{test_patient.first_name}', 'https://example.com/activate/xxx']")
        print(colored("   ✅ [SIMULATION] Template envoyé", 'green'))
        
        print("\n2. Test template document:")
        print(f"   → Template: document_ready")
        print(f"   → Paramètres: ['{test_patient.first_name}', 'Rapport médical.pdf']")
        print(colored("   ✅ [SIMULATION] Template envoyé", 'green'))
        
    finally:
        settings.WHATSAPP_MODE = original_mode
    
    print(colored("\n✅ Simulation terminée", 'green'))

def main():
    """Menu principal"""
    while True:
        print(colored("\n=== MIGRATION WHATSAPP SANDBOX → PRODUCTION ===", 'cyan', attrs=['bold']))
        print("\n1. Vérifier la production readiness")
        print("2. Générer la checklist de migration")
        print("3. Simuler l'envoi en production")
        print("4. Guide d'activation WhatsApp Business")
        print("5. Quitter")
        
        choice = input("\nVotre choix (1-5): ")
        
        if choice == '1':
            check_production_readiness()
        elif choice == '2':
            generate_migration_checklist()
        elif choice == '3':
            simulate_production()
        elif choice == '4':
            print(colored("\n📖 Guide complet:", 'yellow'))
            print("https://www.twilio.com/docs/whatsapp/tutorial/connect-number-business-profile")
            print("\n📞 Support Twilio WhatsApp:")
            print("https://support.twilio.com/hc/en-us/sections/360000538594-WhatsApp-on-Twilio")
        elif choice == '5':
            print(colored("\n👋 Au revoir!", 'green'))
            break
        else:
            print(colored("\n❌ Choix invalide", 'red'))
        
        input("\nAppuyez sur Entrée pour continuer...")

if __name__ == "__main__":
    # Installer termcolor si nécessaire
    try:
        from termcolor import colored
    except ImportError:
        print("Installation de termcolor...")
        os.system(f"{sys.executable} -m pip install termcolor")
        from termcolor import colored
    
    main()