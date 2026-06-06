# Configuration Firebase — Groupe Prospective

## Étapes pour activer le cloud (environ 15 minutes)

---

### 1. Créer le projet Firebase

1. Aller sur **https://console.firebase.google.com**
2. Cliquer **Ajouter un projet**
3. Nom : `groupe-prospective` (ou ce que vous voulez)
4. Désactiver Google Analytics (pas nécessaire) → **Créer le projet**

---

### 2. Activer l'authentification par email

1. Dans le menu gauche → **Build → Authentication**
2. Cliquer **Commencer**
3. Onglet **Sign-in method** → activer **Email/Mot de passe**
4. Onglet **Users** → **Ajouter un utilisateur**
   - Entrer votre email et un mot de passe sécurisé
   - (Répéter pour chaque personne qui utilisera l'app)

---

### 3. Activer Firestore (base de données cloud)

1. Dans le menu gauche → **Build → Firestore Database**
2. Cliquer **Créer une base de données**
3. Choisir **Mode production** → **Suivant**
4. Choisir la région : **northamerica-northeast1 (Montréal)** → **Activer**
5. Aller dans l'onglet **Règles** et remplacer le contenu par :

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId}/{document=**} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
```

6. Cliquer **Publier**

---

### 4. Obtenir la configuration Firebase

1. Dans **Paramètres du projet** (icône ⚙️ en haut à gauche)
2. Section **Vos applications** → cliquer l'icône `</>`  (Web)
3. Nom de l'app : `gestion` → **Enregistrer l'application**
4. Vous verrez un bloc comme ceci — **copiez ces valeurs** :

```javascript
const firebaseConfig = {
  apiKey: "AIzaSy...",
  authDomain: "groupe-prospective-xxxxx.firebaseapp.com",
  projectId: "groupe-prospective-xxxxx",
  storageBucket: "groupe-prospective-xxxxx.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abcdef..."
};
```

---

### 5. Configurer le fichier index.html

Ouvrir `index.html` et chercher (vers la fin du fichier) :

```javascript
const GP_FIREBASE_CONFIG = {
  apiKey:            "VOTRE_API_KEY",
  authDomain:        "VOTRE_PROJECT_ID.firebaseapp.com",
  projectId:         "VOTRE_PROJECT_ID",
  storageBucket:     "VOTRE_PROJECT_ID.appspot.com",
  messagingSenderId: "VOTRE_MESSAGING_SENDER_ID",
  appId:             "VOTRE_APP_ID"
};
```

Remplacer chaque valeur `"VOTRE_..."` par les vraies valeurs copiées à l'étape 4.

---

### 6. Tester

1. Ouvrir `index.html` dans le navigateur
2. L'écran de connexion apparaît
3. Entrer le courriel et mot de passe créés à l'étape 2
4. L'application s'ouvre — les données se synchronisent automatiquement

---

## Comment ça fonctionne

- **Connexion requise** : L'app affiche un écran de login avant tout accès
- **Sync automatique** : Chaque modification est sauvegardée dans le cloud après 1,5 secondes
- **Hors ligne** : Si vous n'avez pas internet, tout fonctionne localement — le sync reprend dès que la connexion revient
- **Multi-appareil** : Connectez-vous depuis n'importe quel ordinateur pour retrouver vos données
- **Sécurité** : Chaque utilisateur voit uniquement ses propres données

## Indicateur de sync (en bas à droite)

| Couleur | Signification |
|---------|---------------|
| 🟡 Jaune | Sauvegarde en cours |
| 🟢 Vert | Sauvegardé avec succès |
| 🔴 Rouge | Erreur (données locales conservées) |

---

## Ajouter d'autres utilisateurs

1. Firebase Console → **Authentication → Users**
2. Cliquer **Ajouter un utilisateur**
3. Entrer leur courriel et mot de passe
4. Ils partagent le même compte Firebase (mêmes données)

> **Note :** Actuellement tous les utilisateurs partagent les mêmes données.
> Pour des comptes séparés (chaque utilisateur voit ses propres données),
> contactez votre développeur.
