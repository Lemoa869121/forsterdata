# ForsterData

Plateforme de consultation, de comparaison et de sélection des procès-verbaux (Feu, Anti-effraction, Pare-balles), des essais AEV et des essais acoustiques Forster.

Site 100 % statique : un fichier `index.html` et les données dans `data/data.json`. Pas de serveur ni de base de données, hébergement gratuit sur GitHub Pages.

## Fonctionnalités

- 5 catégories : Feu, Anti-effraction (RC), Pare-balles (FB), AEV, Acoustique
- Filtres par catégorie : n° de PV, degré / classe, durée, application, série, verrier, minimums A/E/V, Rw minimum…
- Recherche par dimensions (Feu) : cloison (dimensions du vitrage), bloc-porte 1 ou 2 vantaux
- Statut de validité des PV : valide, expire dans les 3 mois, expiré
- Fiche détaillée de chaque PV
- **Lien Feu ↔ Anti-effraction ↔ Pare-balles** : chaque fiche liste les PV des deux autres catégories qu'on peut cumuler avec elle. On peut aussi filtrer, par exemple « PV feu cumulables avec un RC3 ». Voir la règle ci-dessous.
- Comparaison côte à côte de 2 à 4 PV, avec option « uniquement les différences »
- Tri des colonnes, pagination, adresse directe par catégorie (`…/#feu`, `…/#rc`, `…/#aev`…)

## Règle de lien entre Feu, Anti-effraction et Pare-balles

Deux PV de catégories différentes sont liés quand ils ont :
1. la **même série** (presto, unico, fuego light…) ;
2. le **même type d'ouvrage** : porte (porte, porte anti-panique et portes tôlées sont regroupées), ouvrant de service, cloison, cloison bords-à-bords, mur rideau… ;
3. une **déclaration de cumul** dans la colonne « Cumul de perf » d'au moins un des deux PV. Par exemple, Feu « RC2 / RC3 » ↔ RC2, RC « E30, EI30 » ↔ E30, FB « RC3 » ↔ RC3.

Si les deux PV déclarent un cumul, c'est le plus spécifique qui fait foi (Pare-balles > Anti-effraction > Feu). Par exemple, un PV RC2 testé avec « EI60 » n'est pas lié aux portes EI30, même si celles-ci indiquent « RC2 ».

Pour que les liens soient justes, il suffit de bien remplir « Cumul de perf ». La règle est codée dans la fonction `buildLinks()` de `index.html`.

## Structure

```
index.html               l'application (HTML + CSS + JS, sans dépendance)
data/csv/                exports CSV des tables (source de vérité)
data/data.json           données nettoyées utilisées par l'app (générées)
scripts/build_data.py    conversion CSV -> data.json
.github/workflows/       publication automatique sur GitHub Pages
```

## Mettre à jour les données

Ce dépôt est **public** : les exports bruts, qui contiennent les notes internes, ne doivent jamais y être poussés.

1. Exporter les tables depuis la source (Glide / Google Sheet) et déposer les CSV dans `data/brut/`. Ce dossier est ignoré par git.
2. Lancer `python3 scripts/build_data.py`. Le script écrit dans `data/csv/` des copies sans colonnes internes (*Note interne*, *Propriétaire(s)*, *Date modification*, *A ajouter pour prochaine revision*), puis génère `data/data.json`.
3. Faire un commit et un push. L'action GitHub republie le site en 1 à 2 minutes.

Le script nettoie aussi les données : espaces, dates aux formats JJ/MM/AAAA et M/J/AA, dimensions à 0 traitées comme « non applicable ». Pour publier une colonne interne, la retirer de la liste `INTERNAL` dans `scripts/build_data.py`.

## Mise en ligne sur GitHub

1. Créer un dépôt public, puis y pousser le contenu de ce dossier.
2. Aller dans **Settings → Pages → Build and deployment → Source : GitHub Actions**.
3. Le site est publié à l'adresse `https://<compte>.github.io/<depot>/`. On peut ensuite lui associer un nom de domaine (par ex. `data.forstersystems.fr`) dans la même page.

## Tester en local

```
python3 scripts/build_data.py
python3 -m http.server 8000
# puis ouvrir http://localhost:8000
```
