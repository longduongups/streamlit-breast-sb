# 📊 Streamlit Breast Measurement App

Visualisez les mesures de poitrine issues de Blender, directement via une app web déployée sur AWS EC2.

## 🧪 Contenu

- `app_supabase.py` : App Streamlit connectée à Supabase
- `requirements.txt` : Dépendances
- `streamlit-deploy.yaml` : Déploiement automatique avec AWS CloudFormation

## 🚀 Déploiement EC2

1. Aller sur AWS CloudFormation
2. Créer une pile avec `streamlit-deploy.yaml`
3. Lancer → votre app est dispo via IP publique EC2 !

## 🔐 Variables secrètes

Créez un fichier `.streamlit/secrets.toml` **localement** avec :

```toml
[supabase]
url = "https://xxx.supabase.co"
key = "xxxxx"
