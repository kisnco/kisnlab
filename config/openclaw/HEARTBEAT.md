# HEARTBEAT — KisnLab

OpenClaw consulte ce fichier toutes les 30 minutes.
Il poste dans **#alertes** uniquement si une action est nécessaire. Sinon : silence.

---

## ✅ Check quotidienne (chaque jour)

- [ ] Y a-t-il des messages Discord sans réponse depuis plus de 4h ? → résumer et pinger dans #alertes
- [ ] Un workflow n8n a-t-il échoué dans les dernières 24h ? → notifier dans #alertes avec le détail

## 📅 Check hebdomadaire (lundi 9h)

- [ ] Générer le brief hebdomadaire des 5 projets actifs → poster dans #briefs
- [ ] Résumer les décisions stratégiques en attente → poster dans #strategie

## 💰 Check financière (chaque vendredi)

- [ ] Y a-t-il des factures non payées depuis plus de 7 jours ? → notifier dans #admin
- [ ] Résumé de la semaine : appels LLM + coûts Claude (via Langfuse) → poster dans #logs

## ⚠️ Alertes immédiates (dès que détecté)

- [ ] Erreur critique dans les logs → #alertes immédiatement
- [ ] Coût Claude > 5€ sur une seule tâche → #alertes avec détail
- [ ] Tentative d'accès non autorisé → #alertes immédiatement

---

## 📏 Règles de comportement

- **Pas de spam** : mieux vaut silence que notification inutile
- **Si tu hésites** : ne notifie pas
- **Urgences** : toujours immédiates, sans attendre le prochain cycle
- **Format** : messages courts, clairs, avec emoji de contexte
